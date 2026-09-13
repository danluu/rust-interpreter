//! Exact Darwin foreign signatures; arbitrary fcntl operations stay unsupported.
use super::*;

impl<'tcx> Lower<'_, 'tcx> {
    pub(super) fn descriptor_function(&mut self, instance: Instance<'tcx>,
        args: &[rustc_span::Spanned<Operand<'tcx>>], destination: Place<'tcx>) -> Result<bool> {
        let tcx = self.tcx();
        let symbol = tcx.symbol_name(instance).name;
        if !matches!(symbol, "open" | "write" | "close" | "fcntl") { return Ok(false); }
        if tcx.sess.target.os.desc() != "macos" || tcx.sess.target.arch.desc() != "aarch64" {
            return Err("descriptor I/O requires the AArch64 Darwin target".into());
        }
        let sig = tcx.fn_sig(instance.def_id()).instantiate(tcx, instance.args);
        let sig = tcx.normalize_erasing_regions(env(), sig);
        let sig = tcx.instantiate_bound_regions_with_erased(sig);
        let inputs = sig.inputs();
        let const_pointer = |ty: Ty<'tcx>| matches!(ty.kind(), ty::RawPtr(_, rustc_hir::Mutability::Not))
            && self.layout(ty).is_ok_and(|layout| layout.size.bytes() == 8);
        let valid = match symbol {
            "open" => sig.c_variadic() && inputs.len() == 2 && const_pointer(inputs[0])
                && matches!(inputs[0].kind(), ty::RawPtr(pointee, _) if *pointee == tcx.types.i8 || *pointee == tcx.types.u8)
                && inputs[1] == tcx.types.i32 && sig.output() == tcx.types.i32
                && (args.len() == 2 || args.len() == 3
                    && matches!(self.operand_ty(&args[2].node), ty if ty == tcx.types.i32 || ty == tcx.types.u32)),
            "write" => !sig.c_variadic() && inputs.len() == 3 && inputs[0] == tcx.types.i32
                && const_pointer(inputs[1]) && inputs[2] == tcx.types.usize
                && sig.output() == tcx.types.isize && args.len() == 3,
            "close" => !sig.c_variadic() && inputs == [tcx.types.i32]
                && sig.output() == tcx.types.i32 && args.len() == 1,
            "fcntl" => sig.c_variadic() && inputs == [tcx.types.i32, tcx.types.i32]
                && sig.output() == tcx.types.i32 && args.len() == 2,
            _ => unreachable!(),
        };
        if !valid || sig.abi() != (ExternAbi::C { unwind: false }) {
            return Err(format!("invalid {symbol} signature for guest descriptor I/O"));
        }
        if symbol == "fcntl" {
            // F_GETFD is the only admitted command. Prove it during export,
            // rather than trapping after a program has already written a file.
            let command = match &args[1].node {
                Operand::Constant(c) => match self.mono(c.const_).eval(tcx, env(), c.span) {
                    Ok(ConstValue::Scalar(Scalar::Int(value))) => Some(value.to_bits(value.size())),
                    _ => None,
                },
                _ => None,
            };
            if command != Some(1) { return Err("guest fcntl requires a constant F_GETFD command".into()); }
        }
        let values = args.iter().map(|arg| self.scalar(&arg.node)).collect::<Result<Vec<_>>>()?;
        let address = self.exporter.errno_address()?;
        let errno = self.imm_pointer(address as u128, 0, PointerKind::Errno, || "guest errno".into())?;
        let dst = self.reg();
        self.code.push(match symbol {
            "open" => Op::DescriptorOpen { dst, path: values[0], flags: values[1], mode: values.get(2).copied(), errno },
            "write" => Op::DescriptorWrite { dst, descriptor: values[0], address: values[1], size: values[2], errno },
            "close" => Op::DescriptorClose { dst, descriptor: values[0], errno },
            "fcntl" => Op::DescriptorGetFd { dst, descriptor: values[0], errno },
            _ => unreachable!(),
        });
        let destination = self.place(destination)?;
        self.store(destination.address, dst, if symbol == "write" { 8 } else { 4 })?;
        Ok(true)
    }
}
