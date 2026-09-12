//! Checked Darwin callback registration; execution remains in guest frames.
use super::*;

impl<'tcx> Lower<'_, 'tcx> {
    pub(super) fn try_callback(&mut self, args: &[rustc_span::Spanned<Operand<'tcx>>],
        destination: Location<'tcx>) -> Result<bool> {
        let tcx = self.tcx();
        if args.len() != 3 || !destination.ty.is_bool() {
            return Err("invalid catch_unwind signature".into());
        }
        let types: Vec<_> = args.iter().map(|arg| self.operand_ty(&arg.node)).collect();
        if !matches!(types[0].kind(), ty::FnPtr(..)) || !matches!(types[2].kind(), ty::FnPtr(..))
            || !matches!(types[1].kind(), ty::RawPtr(_, rustc_hir::Mutability::Mut))
            || !self.layout(types[1]).is_ok_and(|l| l.size.bytes() == 8) {
            return Err("invalid catch_unwind callback signature".into());
        }
        let run = tcx.instantiate_bound_regions_with_erased(types[0].fn_sig(tcx));
        let catch = tcx.instantiate_bound_regions_with_erased(types[2].fn_sig(tcx));
        if run.abi() != ExternAbi::Rust || run.c_variadic() || run.inputs() != [types[1]]
            || !run.output().is_unit() || catch.abi() != ExternAbi::Rust || catch.c_variadic()
            || catch.inputs().len() != 2 || catch.inputs()[0] != types[1] || !catch.output().is_unit()
            || !matches!(catch.inputs()[1].kind(), ty::RawPtr(pointee, rustc_hir::Mutability::Mut) if *pointee == tcx.types.u8) {
            return Err("invalid catch_unwind callback signature".into());
        }
        let callee = self.scalar(&args[0].node)?;
        let data = self.operand(&args[1].node)?;
        let _ = self.operand(&args[2].node)?;
        self.require_indirect_calls(CallShape { args: vec![8], result: 0 });
        self.code.push(Op::CallIndirect { callee, args: vec![data], arg_sizes: vec![8],
            destination: destination.address, result_size: 0 });
        // Only normal return reaches this store. Guest panic, unavailable calls,
        // invalid memory and all resource-limit failures remain command errors.
        // This explicit option does not implement catching or stack unwinding.
        let success = self.imm(0);
        self.store(destination.address, success, 1)?;
        Ok(true)
    }

    pub(super) fn tls_registration(&mut self, instance: Instance<'tcx>,
        args: &[rustc_span::Spanned<Operand<'tcx>>]) -> Result<bool> {
        let tcx = self.tcx();
        if tcx.symbol_name(instance).name != "_tlv_atexit" { return Ok(false); }
        if tcx.sess.target.os.desc() != "macos" || tcx.sess.target.arch.desc() != "aarch64" {
            return Err("TLS destructor registration requires the AArch64 Darwin target".into());
        }
        let sig = tcx.fn_sig(instance.def_id()).instantiate(tcx, instance.args);
        let sig = tcx.normalize_erasing_regions(env(), sig);
        let sig = tcx.instantiate_bound_regions_with_erased(sig);
        let inputs = sig.inputs();
        if sig.abi() != (ExternAbi::C { unwind: false }) || sig.c_variadic()
            || !sig.output().is_unit() || inputs.len() != 2 || args.len() != 2
            || !matches!(inputs[0].kind(), ty::FnPtr(..))
            || !matches!(inputs[1].kind(), ty::RawPtr(_, rustc_hir::Mutability::Mut))
            || !self.layout(inputs[1]).is_ok_and(|l| l.size.bytes() == 8) {
            return Err("invalid _tlv_atexit signature for guest TLS registration".into());
        }
        let callback = tcx.instantiate_bound_regions_with_erased(inputs[0].fn_sig(tcx));
        if callback.abi() != (ExternAbi::C { unwind: false }) || callback.c_variadic()
            || callback.inputs() != [inputs[1]] || !callback.output().is_unit() {
            return Err("invalid _tlv_atexit callback signature for guest TLS registration".into());
        }
        let callback = self.scalar(&args[0].node)?;
        let argument = self.scalar(&args[1].node)?;
        self.require_indirect_calls(CallShape { args: vec![8], result: 0 });
        self.code.push(Op::RegisterTlsDestructor { callback, argument });
        Ok(true)
    }
}
