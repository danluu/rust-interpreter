//! Adapters for the Result<(), E> convention of ordinary Rust test bodies.
use super::*;

impl<'a, 'tcx> Lower<'a, 'tcx> {
    pub(super) fn test_adapter(
        exporter: &'a mut Exporter<'tcx>,
        instance: Instance<'tcx>,
        function: usize,
        output: Ty<'tcx>,
    ) -> Result<Function> {
        // The original function has already been lowered with its real ABI.
        // Only this outer adapter consumes its Result and returns unit; callers
        // and function pointers still see the original aggregate result.
        let body = exporter.tcx.instance_mir(instance.def);
        let mut this = Self::empty(exporter, instance, body);
        let layout = this.layout(output)?;
        let align = layout.align.abi.bytes_usize();
        if !layout.is_sized() || align > rust_interp_bytecode::MAX_ALIGNMENT {
            return Err("unsupported test-result layout".into());
        }
        let address = this.temporary_aligned(layout.size.bytes_usize(), align);
        this.code.push(Op::Call { function, args: vec![], destination: address });
        let result = Location { address, ty: output, variant: None, metadata: None };
        let discriminant = this.discriminant(result, 8)?;
        let ty::Adt(def, _) = output.kind() else {
            return Err("test-result adapter requires Result<(), E>".into());
        };
        let ok = this.tcx().lang_items().result_ok_variant().ok_or("missing Result::Ok")?;
        let variant = def.variant_index_with_id(ok);
        let ok = output.discriminant_for_variant(this.tcx(), variant)
            .ok_or("missing Result::Ok discriminant")?.val;
        let expected = this.imm(ok);
        let success = this.bin(Binary::Eq, discriminant, expected, 8, false).0;
        this.code.push(Op::Assert {
            value: success,
            expected: true,
            message: format!("test {} returned Err", this.tcx().def_path_str(instance.def_id())),
        });
        // Failure stops the VM, like its existing non-unwinding panic boundary.
        // It does not run E's Debug/Drop implementation or emulate stdio.
        this.code.push(Op::Return);
        Ok(Function {
            name: format!("Result test adapter: {}", this.tcx().def_path_str(instance.def_id())),
            frame_size: this.frame_size,
            frame_align: this.frame_align,
            registers: this.registers as usize,
            args: vec![],
            result: Slot { offset: 0, size: 0 },
            code: this.code,
        })
    }
}
