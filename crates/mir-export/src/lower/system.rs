//! Narrow operating-system primitives, with checked guest memory in the VM.
use super::*;

impl<'tcx> Lower<'_, 'tcx> {
    pub(super) fn system_function(&mut self, instance: Instance<'tcx>, args: &[rustc_span::Spanned<Operand<'tcx>>], destination: Place<'tcx>) -> Result<bool> {
        let tcx = self.tcx();
        if !tcx.is_foreign_item(instance.def_id()) { return Ok(false); }
        if self.c_allocator_function(instance, args, destination)? { return Ok(true); }
        if self.descriptor_function(instance, args, destination)? { return Ok(true); }
        if self.getcwd_function(instance, args, destination)? { return Ok(true); }
        if self.tls_registration(instance, args)? { return Ok(true); }
        let symbol = tcx.symbol_name(instance).name;
        if !matches!(symbol, "abort" | "CCRandomGenerateBytes" | "sysctlbyname" | "getenv" | "strlen") { return Ok(false); }
        let sig = tcx.fn_sig(instance.def_id()).instantiate(tcx, instance.args);
        let sig = tcx.normalize_erasing_regions(env(), sig);
        let sig = tcx.instantiate_bound_regions_with_erased(sig);
        if symbol == "strlen" {
            let inputs = sig.inputs();
            if sig.abi() != (ExternAbi::C { unwind: false }) || sig.c_variadic()
                || inputs.len() != 1 || args.len() != 1 || sig.output() != tcx.types.usize
                || !matches!(inputs[0].kind(), ty::RawPtr(pointee, rustc_hir::Mutability::Not)
                    if *pointee == tcx.types.i8 || *pointee == tcx.types.u8)
                || self.layout(inputs[0])?.size.bytes() != 8 {
                return Err("invalid strlen signature".into());
            }
            // Scan with ordinary checked guest loads and charged bytecode
            // instructions. No host strlen sees a guest address; a missing
            // terminator reaches the normal memory or instruction limit.
            let address = self.scalar(&args[0].node)?;
            let zero = self.imm(0);
            let one = self.imm(1);
            let cursor = self.bin(Binary::Add, address, zero, 64, false).0;
            let length = self.imm(0);
            let start = self.code.len();
            let byte = self.load(cursor, 1)?;
            let branch = self.code.len();
            self.code.push(Op::Switch { value: byte, cases: vec![(0, 0)], otherwise: branch + 1 });
            let overflow = self.reg();
            self.code.push(Op::Binary { dst: cursor, overflow, op: Binary::Add, a: cursor, b: one, bits: 64, signed: false });
            self.code.push(Op::Binary { dst: length, overflow, op: Binary::Add, a: length, b: one, bits: 64, signed: false });
            self.code.push(Op::Jump { target: start });
            let end = self.code.len();
            let Op::Switch { cases, .. } = &mut self.code[branch] else { unreachable!() };
            cases[0].1 = end;
            let destination = self.place(destination)?;
            self.store(destination.address, length, 8)?;
            return Ok(true);
        }
        if symbol == "getenv" {
            let inputs = sig.inputs();
            if sig.abi() != (ExternAbi::C { unwind: false }) || sig.c_variadic()
                || inputs.len() != 1 || args.len() != 1
                || !matches!(inputs[0].kind(), ty::RawPtr(pointee, rustc_hir::Mutability::Not)
                    if *pointee == tcx.types.i8 || *pointee == tcx.types.u8)
                || !matches!(sig.output().kind(), ty::RawPtr(pointee, rustc_hir::Mutability::Mut)
                    if *pointee == tcx.types.i8 || *pointee == tcx.types.u8)
                || self.layout(inputs[0])?.size.bytes() != 8 || self.layout(sig.output())?.size.bytes() != 8 {
                return Err("invalid getenv signature".into());
            }
            let name = self.scalar(&args[0].node)?;
            let dst = self.reg();
            self.code.push(Op::EnvironmentGet { dst, name });
            let destination = self.place(destination)?;
            self.store(destination.address, dst, 8)?;
            return Ok(true);
        }
        if symbol == "abort" {
            if sig.abi() != (ExternAbi::C { unwind: false }) || sig.c_variadic()
                || !sig.inputs().is_empty() || !sig.output().is_never() || !args.is_empty() {
                return Err("invalid abort signature".into());
            }
            self.code.push(Op::Trap { message: "guest process abort".into() });
            return Ok(true);
        }
        if symbol == "sysctlbyname" {
            if tcx.sess.target.os.desc() != "macos" {
                return Err("CPU-feature query requires macOS".into());
            }
            let inputs = sig.inputs();
            if sig.abi() != (ExternAbi::C { unwind: false }) || sig.c_variadic()
                || inputs.len() != 5 || args.len() != 5 || sig.output() != tcx.types.i32
                || !matches!(inputs[0].kind(), ty::RawPtr(pointee, rustc_hir::Mutability::Not) if *pointee == tcx.types.i8)
                || !matches!(inputs[1].kind(), ty::RawPtr(_, rustc_hir::Mutability::Mut))
                || !matches!(inputs[2].kind(), ty::RawPtr(pointee, rustc_hir::Mutability::Mut) if *pointee == tcx.types.usize)
                || !matches!(inputs[3].kind(), ty::RawPtr(_, rustc_hir::Mutability::Mut))
                || inputs[4] != tcx.types.usize
                || inputs[..4].iter().any(|t| !self.layout(*t).is_ok_and(|l| l.size.bytes() == 8)) {
                return Err("invalid sysctlbyname signature for CPU-feature query".into());
            }
            let name = self.scalar(&args[0].node)?;
            let output = self.scalar(&args[1].node)?;
            let output_len = self.scalar(&args[2].node)?;
            let new_data = self.scalar(&args[3].node)?;
            let new_len = self.scalar(&args[4].node)?;
            let dst = self.reg();
            self.code.push(Op::CpuFeatureQuery { dst, name, output, output_len, new_data, new_len });
            let destination = self.place(destination)?;
            self.store(destination.address, dst, 4)?;
            return Ok(true);
        }
        if tcx.sess.target.os.desc() != "macos" {
            return Err("CommonCrypto randomness requires macOS".into());
        }
        if sig.abi() != (ExternAbi::C { unwind: false }) || sig.c_variadic()
            || sig.inputs().len() != 2
            || !matches!(sig.inputs()[0].kind(), ty::RawPtr(_, rustc_hir::Mutability::Mut))
            || sig.inputs()[1] != tcx.types.usize || sig.output() != tcx.types.i32
            || self.layout(sig.inputs()[0])?.size.bytes() != 8 || args.len() != 2 {
            return Err("invalid CCRandomGenerateBytes signature".into());
        }
        let address = self.scalar(&args[0].node)?;
        let size = self.scalar(&args[1].node)?;
        let dst = self.reg();
        self.code.push(Op::RandomBytes { dst, address, size });
        let destination = self.place(destination)?;
        self.store(destination.address, dst, 4)?;
        Ok(true)
    }
}
