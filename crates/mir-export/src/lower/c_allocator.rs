//! Foreign allocator signatures lower to checked guest operations, never host pointers.
use super::*;

impl Exporter<'_> {
    fn errno_address(&mut self) -> Result<usize> {
        if let Some(address) = self.runtime_errno { return Ok(address); }
        let offset = self.statics.len().max(16).checked_add(3)
            .ok_or("guest errno offset overflow")? & !3;
        let end = offset.checked_add(4).ok_or("guest errno extent overflow")?;
        if end >= rust_interp_bytecode::HEAP_POINTER_TAG as usize {
            return Err("guest errno exceeds static address space".into());
        }
        self.statics.resize(end, 0);
        self.thread_locals.push(Slot { offset, size: 4 });
        let address = rust_interp_bytecode::HEAP_POINTER_TAG as usize + offset;
        self.runtime_errno = Some(address);
        Ok(address)
    }
}

impl<'tcx> Lower<'_, 'tcx> {
    pub(super) fn c_allocator_function(&mut self, instance: Instance<'tcx>,
        args: &[rustc_span::Spanned<Operand<'tcx>>], destination: Place<'tcx>) -> Result<bool> {
        let tcx = self.tcx();
        let symbol = tcx.symbol_name(instance).name;
        if !matches!(symbol, "malloc" | "calloc" | "free" | "realloc" | "posix_memalign" | "__error") {
            return Ok(false);
        }
        if tcx.sess.target.os.desc() != "macos" || tcx.sess.target.arch.desc() != "aarch64" {
            return Err("C allocator operations require the AArch64 Darwin target".into());
        }
        let sig = tcx.fn_sig(instance.def_id()).instantiate(tcx, instance.args);
        let sig = tcx.normalize_erasing_regions(env(), sig);
        let sig = tcx.instantiate_bound_regions_with_erased(sig);
        let pointer = |ty: Ty<'tcx>| matches!(ty.kind(), ty::RawPtr(_, rustc_hir::Mutability::Mut))
            && self.layout(ty).is_ok_and(|layout| layout.size.bytes() == 8);
        let inputs = sig.inputs();
        let valid = match symbol {
            "malloc" => inputs == [tcx.types.usize] && pointer(sig.output()),
            "calloc" => inputs == [tcx.types.usize, tcx.types.usize] && pointer(sig.output()),
            "free" => inputs.len() == 1 && pointer(inputs[0]) && sig.output().is_unit(),
            "realloc" => inputs.len() == 2 && pointer(inputs[0])
                && inputs[1] == tcx.types.usize && pointer(sig.output()),
            "posix_memalign" => inputs.len() == 3 && pointer(inputs[0])
                && matches!(inputs[0].kind(), ty::RawPtr(pointee, _) if pointer(*pointee))
                && inputs[1..] == [tcx.types.usize, tcx.types.usize] && sig.output() == tcx.types.i32,
            "__error" => inputs.is_empty() && pointer(sig.output())
                && matches!(sig.output().kind(), ty::RawPtr(pointee, _) if *pointee == tcx.types.i32),
            _ => unreachable!(),
        };
        if !valid || args.len() != inputs.len() || sig.c_variadic()
            || sig.abi() != (ExternAbi::C { unwind: false }) {
            return Err(format!("invalid {symbol} signature for guest C allocator"));
        }
        // Materialize arguments in their original order before creating hidden
        // TLS operands. All frontend type/borrow checks have already run.
        let values = args.iter().map(|arg| self.scalar(&arg.node)).collect::<Result<Vec<_>>>()?;
        if symbol == "free" {
            self.code.push(Op::CDeallocate { pointer: values[0] });
            return Ok(true);
        }
        let dst = self.reg();
        if symbol == "posix_memalign" {
            self.code.push(Op::CAlignedAllocate { dst, output: values[0], align: values[1], size: values[2] });
        } else {
            let address = self.exporter.errno_address()?;
            let errno = self.imm(address as u128);
            match symbol {
                "__error" => self.code.push(Op::Imm { dst, value: address as u128 }),
                "malloc" | "calloc" => {
                    let (count, size) = if symbol == "malloc" { (self.imm(1), values[0]) }
                        else { (values[0], values[1]) };
                    self.code.push(Op::CAllocate { dst, count, size, errno, zeroed: symbol == "calloc" });
                }
                "realloc" => self.code.push(Op::CReallocate { dst, pointer: values[0], size: values[1], errno }),
                _ => unreachable!(),
            }
        }
        let destination = self.place(destination)?;
        self.store(destination.address, dst, if symbol == "posix_memalign" { 4 } else { 8 })?;
        Ok(true)
    }
}
