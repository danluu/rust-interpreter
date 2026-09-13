//! The actual Darwin libc getcwd ABI; no path or build-script special cases.
use super::*;

impl<'tcx> Lower<'_, 'tcx> {
    pub(super) fn getcwd_function(&mut self, instance: Instance<'tcx>,
        args: &[rustc_span::Spanned<Operand<'tcx>>], destination: Place<'tcx>) -> Result<bool> {
        let tcx = self.tcx();
        if tcx.symbol_name(instance).name != "getcwd" { return Ok(false); }
        if tcx.sess.target.os.desc() != "macos" || tcx.sess.target.arch.desc() != "aarch64" {
            return Err("getcwd requires the AArch64 Darwin target".into());
        }
        let sig = tcx.fn_sig(instance.def_id()).instantiate(tcx, instance.args);
        let sig = tcx.normalize_erasing_regions(env(), sig);
        let sig = tcx.instantiate_bound_regions_with_erased(sig);
        let inputs = sig.inputs();
        if sig.abi() != (ExternAbi::C { unwind: false }) || sig.c_variadic()
            || inputs.len() != 2 || args.len() != 2 || inputs[1] != tcx.types.usize
            || inputs[0] != sig.output()
            || !matches!(inputs[0].kind(), ty::RawPtr(pointee, rustc_hir::Mutability::Mut)
                if *pointee == tcx.types.i8 || *pointee == tcx.types.u8)
            || self.layout(inputs[0])?.size.bytes() != 8 {
            return Err("invalid getcwd signature for Darwin guest".into());
        }
        let address = self.scalar(&args[0].node)?;
        let size = self.scalar(&args[1].node)?;
        let error = self.exporter.errno_address()?;
        let errno = self.imm_pointer(error as u128, 0, PointerKind::Errno, || "guest errno".into())?;
        let dst = self.reg();
        self.code.push(Op::CurrentDirectory { dst, address, size, errno });
        let destination = self.place(destination)?;
        self.store(destination.address, dst, 8)?;
        Ok(true)
    }
}
