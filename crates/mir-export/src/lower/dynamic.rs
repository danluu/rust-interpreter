//! Trait-object metadata and dispatch use guest tables and guest function handles.
use super::*;

impl<'tcx> Exporter<'tcx> {
    pub(super) fn vtable(
        &mut self,
        concrete: Ty<'tcx>,
        principal: Option<ty::PolyExistentialTraitRef<'tcx>>,
    ) -> Result<usize> {
        let principal = principal.map(|p| self.tcx.instantiate_bound_regions_with_erased(p));
        let allocation = self.tcx.vtable_allocation((concrete, principal));
        self.alloc(allocation)
    }
}

impl<'a, 'tcx> Lower<'a, 'tcx> {
    fn layout_sum(&mut self, left: Reg, right: Reg) -> Reg {
        let (value, overflow) = self.bin(Binary::Add, left, right, 64, false);
        self.code.push(Op::Assert {
            value: overflow, expected: false, message: "dynamic size overflow".into(),
        });
        value
    }

    pub(super) fn align_dynamic(&mut self, offset: Reg, align: Reg) -> Reg {
        // align comes from a compiler layout or a checked guest vtable field.
        let one = self.imm(1);
        let addend = self.bin(Binary::Sub, align, one, 64, false).0;
        let sum = self.layout_sum(offset, addend);
        let zero = self.imm(0);
        let negative = self.bin(Binary::Sub, zero, align, 64, false).0;
        self.bin(Binary::And, sum, negative, 64, false).0
    }

    pub(super) fn packed_alignment(&mut self, parent: Ty<'tcx>, align: Reg) -> Reg {
        if let ty::Adt(def, _) = parent.kind()
            && let Some(packed) = def.repr().pack
        {
            let cap = self.imm(packed.bytes() as u128);
            let smaller = self.bin(Binary::Lt, align, cap, 64, false).0;
            let dst = self.reg();
            self.code.push(Op::Select { dst, condition: smaller, yes: align, no: cap });
            dst
        } else {
            align
        }
    }

    /// Match the pinned compiler's size_of_val and field-projection rules.
    /// Metadata belongs to the final unsized tail, even through nested ADTs.
    pub(super) fn dynamic_layout(&mut self, ty: Ty<'tcx>, metadata: Option<Reg>) -> Result<(Reg, Reg)> {
        let layout = self.layout(ty)?;
        if layout.is_sized() {
            return Ok((self.imm(layout.size.bytes() as u128), self.imm(layout.align.abi.bytes() as u128)));
        }
        match ty.kind() {
            ty::Dynamic(..) => {
                let table = metadata.ok_or("dynamic layout has no vtable")?;
                let size_at = self.add(table, 8);
                let align_at = self.add(table, 16);
                let size = self.load(size_at, 8)?;
                let align = self.load(align_at, 8)?;
                let zero = self.imm(0);
                let nonzero = self.bin(Binary::Ne, align, zero, 64, false).0;
                self.code.push(Op::Assert { value: nonzero, expected: true, message: "zero dynamic alignment".into() });
                let one = self.imm(1);
                let lower_bits = self.bin(Binary::Sub, align, one, 64, false).0;
                let extra_bits = self.bin(Binary::And, align, lower_bits, 64, false).0;
                self.code.push(Op::Assert { value: extra_bits, expected: false, message: "dynamic alignment is not a power of two".into() });
                Ok((size, align))
            }
            ty::Slice(_) | ty::Str => {
                let (unit, align) = match ty.kind() {
                    ty::Slice(element) => {
                        let element = self.layout(*element)?;
                        (element.size.bytes(), element.align.abi.bytes())
                    }
                    _ => (1, 1),
                };
                let length = metadata.ok_or("dynamic layout has no length")?;
                let scale = self.imm(unit as u128);
                let (size, overflow) = self.bin(Binary::Mul, length, scale, 64, false);
                self.code.push(Op::Assert { value: overflow, expected: false, message: "dynamic size overflow".into() });
                Ok((size, self.imm(align as u128)))
            }
            ty::Adt(..) | ty::Tuple(..) => {
                let last = layout.fields.count().checked_sub(1).ok_or("unsized aggregate has no tail")?;
                let tail = layout.field(&LayoutCx::new(self.tcx(), env()), last).ty;
                let (tail_size, tail_align) = self.dynamic_layout(tail, metadata)?;
                let tail_align = self.packed_alignment(ty, tail_align);
                let prefix_align = self.imm(layout.align.abi.bytes() as u128);
                let stronger = self.bin(Binary::Gt, prefix_align, tail_align, 64, false).0;
                let full_align = self.reg();
                self.code.push(Op::Select { dst: full_align, condition: stronger, yes: prefix_align, no: tail_align });
                let offset = self.imm(self.field_offset(layout, last)? as u128);
                let size = self.layout_sum(offset, tail_size);
                // Tail size is already a multiple of tail alignment. Rounding
                // the combined size to the full alignment also supplies the
                // padding before that tail, as in rustc's size_of_val.rs.
                let size = self.align_dynamic(size, full_align);
                Ok((size, full_align))
            }
            _ => Err(format!("unsupported dynamic layout for {ty}")),
        }
    }

    pub(super) fn unsize_pointer(
        &mut self,
        operand: &Operand<'tcx>,
        dest: Location<'tcx>,
    ) -> Result<()> {
        let source_ty = self.operand_ty(operand);
        let address = self.operand(operand)?;
        let source_layout = self.layout(source_ty)?;
        // Retain the existing direct path for references, raw pointers, and
        // ordinary Box values whose entire representation is the pointer.
        if source_ty.builtin_deref(true).is_some()
            && dest.ty.builtin_deref(true).is_some()
            && matches!(source_layout.size.bytes(), 8 | 16)
            && self.layout(dest.ty)?.size.bytes() == 16
        {
            return self.unsize_pointer_at(address, source_ty, dest);
        }
        let align = source_layout.align.abi.bytes_usize();
        if !source_layout.is_sized() || align > rust_interp_bytecode::MAX_ALIGNMENT {
            return Err("unsupported coercion source layout".into());
        }
        // A wide destination can have different field offsets and can overlap
        // the source. Snapshot all source fields before the first write.
        let snapshot = self.temporary_aligned(source_layout.size.bytes_usize(), align);
        self.code.push(Op::Copy { src: address, dst: snapshot, size: source_layout.size.bytes_usize() });
        self.coerce_unsized_value(Location {
            address: snapshot, ty: source_ty, variant: None, metadata: None,
        }, dest)
    }

    fn coerce_unsized_value(&mut self, source: Location<'tcx>, dest: Location<'tcx>) -> Result<()> {
        match (*source.ty.kind(), *dest.ty.kind()) {
            (ty::Pat(from, from_pattern), ty::Pat(to, to_pattern))
                if matches!((*from_pattern, *to_pattern), (ty::PatternKind::NotNull, ty::PatternKind::NotNull)) =>
            {
                self.coerce_unsized_value(Location { ty: from, ..source }, Location { ty: to, ..dest })
            }
            (ty::Ref(..), ty::Ref(..) | ty::RawPtr(..)) | (ty::RawPtr(..), ty::RawPtr(..)) => {
                self.unsize_pointer_at(source.address, source.ty, dest)
            }
            (ty::Adt(from, _), ty::Adt(to, _)) if from == to && from.is_struct() => {
                let source_layout = self.layout(source.ty)?;
                let dest_layout = self.layout(dest.ty)?;
                let cx = LayoutCx::new(self.tcx(), env());
                for index in 0..from.non_enum_variant().fields.len() {
                    let source_field = source_layout.field(&cx, index);
                    let dest_field = dest_layout.field(&cx, index);
                    if dest_field.is_zst() { continue; }
                    let src = self.add(source.address, self.field_offset(source_layout, index)?);
                    let dst = self.add(dest.address, self.field_offset(dest_layout, index)?);
                    if source_field.ty == dest_field.ty {
                        if source_field.size != dest_field.size {
                            return Err("equal coercion field types have different sizes".into());
                        }
                        self.code.push(Op::Copy { src, dst, size: source_field.size.bytes_usize() });
                    } else {
                        self.coerce_unsized_value(
                            Location { address: src, ty: source_field.ty, variant: None, metadata: None },
                            Location { address: dst, ty: dest_field.ty, variant: None, metadata: None },
                        )?;
                    }
                }
                Ok(())
            }
            _ => Err(format!("unsupported structural coercion {} to {}", source.ty, dest.ty)),
        }
    }

    fn unsize_pointer_at(&mut self, address: Reg, source_ty: Ty<'tcx>, dest: Location<'tcx>) -> Result<()> {
        let source = source_ty.builtin_deref(true).ok_or("unsize pointer")?;
        let target = dest.ty.builtin_deref(true).ok_or("unsize destination")?;
        let (tail, target_tail) =
            self.tcx()
                .struct_lockstep_tails_for_codegen(source, target, env());
        if self.layout(dest.ty)?.size.bytes() != 16 {
            return Err("unsupported unsized pointer carrier layout".into());
        }
        let data = self.load(address, 8)?;
        let metadata = match (tail.kind(), target_tail.kind()) {
            (ty::Array(_, n), ty::Slice(_)) => self.imm(
                n.try_to_target_usize(self.tcx())
                    .ok_or("unsize array length")? as u128,
            ),
            (ty::Dynamic(from, ..), ty::Dynamic(to, ..)) => {
                let metadata_address = self.add(address, 8);
                let previous = self.load(metadata_address, 8)?;
                if from.principal_def_id() == to.principal_def_id()
                    || to.principal_def_id().is_none()
                {
                    previous
                } else if let Some(slot) = self.tcx().supertrait_vtable_slot((tail, target_tail)) {
                    let field = self.add(
                        previous,
                        slot.checked_mul(8).ok_or("vtable offset overflow")?,
                    );
                    self.load(field, 8)?
                } else {
                    previous
                }
            }
            (_, ty::Dynamic(predicates, ..)) => {
                if !self.layout(tail)?.is_sized() {
                    return Err(
                        "concrete trait-object tail is not sized".into(),
                    );
                }
                let table = self.exporter.vtable(tail, predicates.principal())?;
                self.imm(table as u128)
            }
            _ => return Err("unsupported unsized metadata".into()),
        };
        // Snapshot both components before modifying possibly aliased storage.
        self.store(dest.address, data, 8)?;
        let at = self.add(dest.address, 8);
        self.store(at, metadata, 8)
    }

    pub(super) fn virtual_call(
        &mut self,
        slot: usize,
        func: &Operand<'tcx>,
        args: &[rustc_span::Spanned<Operand<'tcx>>],
        destination: Place<'tcx>,
        tracked: bool,
        source_info: mir::SourceInfo,
    ) -> Result<()> {
        let (mut arguments, mut sizes) = self.call_arguments(func, args)?;
        if sizes.first() != Some(&16) {
            return Err("virtual call requires a fat-pointer receiver".into());
        }
        let metadata = self.add(arguments[0], 8);
        let table = self.load(metadata, 8)?;
        let field = self.add(table, slot.checked_mul(8).ok_or("vtable offset overflow")?);
        let callee = self.load(field, 8)?;
        // The concrete vtable method receives just the data pointer. The
        // remaining arguments retain their ordinary MIR/guest ABI layouts.
        sizes[0] = 8;
        if tracked {
            arguments.push(self.caller_argument(source_info)?);
            sizes.push(8);
        }
        let destination = self.place(destination)?;
        let result_size = self.layout(destination.ty)?.size.bytes_usize();
        self.exporter.require_indirect_calls(CallShape {
            args: sizes.clone(),
            result: result_size,
        });
        self.code.push(Op::CallIndirect {
            callee,
            args: arguments,
            arg_sizes: sizes,
            destination: destination.address,
            result_size,
        });
        Ok(())
    }

    pub(super) fn drop_dynamic(&mut self, loc: Location<'tcx>) -> Result<()> {
        let table = loc.metadata.ok_or("dynamic drop has no vtable")?;
        let callee = self.load(table, 8)?;
        let pointer = self.temporary(8);
        self.store(pointer, loc.address, 8)?;
        let destination = self.imm(0);
        self.exporter.require_indirect_calls(CallShape {
            args: vec![8],
            result: 0,
        });
        // Rust omits the drop method for types needing no destruction. These
        // are bytecode PC targets, independent of the later MIR block fixups.
        let branch = self.code.len();
        self.code.push(Op::Switch {
            value: callee,
            cases: vec![(0, branch + 2)],
            otherwise: branch + 1,
        });
        self.code.push(Op::CallIndirect {
            callee,
            args: vec![pointer],
            arg_sizes: vec![8],
            destination,
            result_size: 0,
        });
        Ok(())
    }
}
