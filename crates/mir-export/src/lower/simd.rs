//! Integer vector intrinsics expressed in the engine's scalar instructions.
//! This first tier favors semantic coverage; it does not invoke LLVM or native
//! SIMD helpers. The custom JIT can compile the resulting scalar sequences.
use super::*;

impl<'a, 'tcx> Lower<'a, 'tcx> {
    fn snapshot_operand(&mut self, op: &Operand<'tcx>) -> Result<Reg> {
        let layout = self.layout(self.operand_ty(op))?;
        let size = layout.size.bytes_usize();
        let src = self.operand(op)?;
        let dst = self.temporary_aligned(size, layout.align.abi.bytes() as usize);
        self.code.push(Op::Copy { dst, src, size });
        Ok(dst)
    }
    pub(super) fn target_intrinsic(
        &mut self,
        instance: Instance<'tcx>,
        args: &[rustc_span::Spanned<Operand<'tcx>>],
        destination: Place<'tcx>,
    ) -> Result<bool> {
        let symbol = self
            .tcx()
            .codegen_fn_attrs(instance.def_id())
            .symbol_name
            .ok_or("target intrinsic has no symbol")?;
        let symbol = symbol.as_str();
        if symbol == "llvm.aarch64.isb" {
            // core::hint::spin_loop reaches ISB SY on this target. Guest code
            // is immutable and the machine has no architectural configuration
            // changes to synchronize, so the barrier has no runtime effect.
            let dest = self.place(destination)?;
            if args.len() != 1
                || self.layout(dest.ty)?.size.bytes() != 0
                || self.integer(self.operand_ty(&args[0].node))? != (32, true)
            {
                return Err("unsupported instruction barrier signature".into());
            }
            let argument = self.scalar(&args[0].node)?;
            let sy = self.imm(15);
            let valid = self.bin(Binary::Eq, argument, sy, 32, false).0;
            self.code.push(Op::Assert {
                value: valid,
                expected: true,
                message: "unsupported instruction barrier argument".into(),
            });
            return Ok(true);
        }
        if symbol == "llvm.aarch64.neon.tbl1.v16i8" {
            let dest = self.place(destination)?;
            let shape = self.vector_shape(dest.ty)?;
            if args.len() != 2
                || (shape.0, shape.1) != (16, 8)
                || self.vector_shape(self.operand_ty(&args[0].node))? != shape
                || self.vector_shape(self.operand_ty(&args[1].node))? != (16, 8, false)
            {
                return Err("invalid byte table lookup shape".into());
            }
            // The named target intrinsic is implemented entirely in our IR.
            // Snapshot both inputs before any destination write, including
            // when the destination aliases either operand after MIR inlining.
            let table = self.snapshot_operand(&args[0].node)?;
            let indices = self.snapshot_operand(&args[1].node)?;
            let limit = self.imm(16);
            let zero = self.imm(0);
            for lane in 0..16 {
                let index = self.vector_lane(indices, lane, 8)?;
                let valid = self.bin(Binary::Lt, index, limit, 8, false).0;
                let safe_index = self.reg();
                self.code.push(Op::Select {
                    dst: safe_index,
                    condition: valid,
                    yes: index,
                    no: zero,
                });
                // Out-of-range lanes still perform a valid one-byte read,
                // then select zero. Never form an out-of-table load address.
                let address = self.bin(Binary::Add, table, safe_index, 64, false).0;
                let value = self.load(address, 1)?;
                let result = self.reg();
                self.code.push(Op::Select {
                    dst: result,
                    condition: valid,
                    yes: value,
                    no: zero,
                });
                self.store_lane(dest.address, lane, 8, result)?;
            }
            return Ok(true);
        }
        if !symbol.starts_with("llvm.aarch64.neon.umaxp.") {
            return Err(format!("unsupported target intrinsic {symbol}"));
        }
        let dest = self.place(destination)?;
        let (lanes, bits, _) = self.vector_shape(dest.ty)?;
        if args.len() != 2
            || lanes % 2 != 0
            || ![8, 16, 32].contains(&bits)
            || symbol != format!("llvm.aarch64.neon.umaxp.v{lanes}i{bits}")
        {
            return Err("invalid pairwise unsigned maximum shape".into());
        }
        for arg in args {
            let shape = self.vector_shape(self.operand_ty(&arg.node))?;
            if (shape.0, shape.1) != (lanes, bits) {
                return Err("pairwise maximum input shape".into());
            }
        }
        // The standard library describes this instruction using an LLVM
        // symbol. Implement its lane semantics in our IR; no LLVM call occurs.
        let a = self.snapshot_operand(&args[0].node)?;
        let b = self.snapshot_operand(&args[1].node)?;
        for (half, base) in [(0, a), (lanes / 2, b)] {
            for i in 0..lanes / 2 {
                let x = self.vector_lane(base, i * 2, bits)?;
                let y = self.vector_lane(base, i * 2 + 1, bits)?;
                let condition = self.bin(Binary::Ge, x, y, bits, false).0;
                let dst = self.reg();
                self.code.push(Op::Select {
                    dst,
                    condition,
                    yes: x,
                    no: y,
                });
                self.store_lane(dest.address, half + i, bits, dst)?;
            }
        }
        Ok(true)
    }
    fn vector_shape(&self, ty: Ty<'tcx>) -> Result<(usize, u8, bool)> {
        if !ty.is_simd() {
            return Err(format!("expected SIMD vector, got {ty}"));
        }
        let (lanes, element) = ty.simd_size_and_type(self.tcx());
        let (bits, signed) = self.integer(element)?;
        if lanes == 0 || lanes > 128 {
            return Err("unsupported SIMD lane count".into());
        }
        Ok((lanes as usize, bits, signed))
    }
    fn vector_lane(&mut self, base: Reg, index: usize, bits: u8) -> Result<Reg> {
        let address = self.add(base, index * (bits as usize / 8));
        self.load(address, bits as usize / 8)
    }
    fn store_lane(&mut self, base: Reg, index: usize, bits: u8, value: Reg) -> Result<()> {
        let address = self.add(base, index * (bits as usize / 8));
        self.store(address, value, bits as usize / 8)
    }
    pub(super) fn simd_intrinsic(
        &mut self,
        name: &str,
        args: &[rustc_span::Spanned<Operand<'tcx>>],
        dest: Location<'tcx>,
    ) -> Result<bool> {
        let first = args.first().ok_or("missing SIMD argument")?;
        if name == "simd_splat" {
            let (lanes, bits, _) = self.vector_shape(dest.ty)?;
            if self.integer(self.operand_ty(&first.node))?.0 != bits {
                return Err("SIMD splat element width mismatch".into());
            }
            let value = self.scalar(&first.node)?;
            for i in 0..lanes {
                self.store_lane(dest.address, i, bits, value)?;
            }
            return Ok(true);
        }
        let (lanes, bits, signed) = self.vector_shape(self.operand_ty(&first.node))?;
        let left = self.snapshot_operand(&first.node)?;
        let result_size = self.layout(dest.ty)?.size.bytes_usize();

        if name == "simd_reduce_add_ordered" || name == "simd_reduce_mul_ordered" {
            if args.len() != 2
                || self.integer(dest.ty)? != (bits, signed)
                || self.integer(self.operand_ty(&args[1].node))? != (bits, signed)
            {
                return Err("ordered SIMD reduction scalar type mismatch".into());
            }
            let mut value = self.scalar(&args[1].node)?;
            let operation = if name == "simd_reduce_add_ordered" {
                Binary::Add
            } else {
                Binary::Mul
            };
            // Integer SIMD arithmetic wraps at the lane width. Include the
            // caller's accumulator and process every lane from left to right.
            for i in 0..lanes {
                let lane = self.vector_lane(left, i, bits)?;
                value = self.bin(operation, value, lane, bits, signed).0;
            }
            self.store(dest.address, value, result_size)?;
            return Ok(true);
        }

        if name == "simd_bitmask" {
            if result_size > 16 || result_size * 8 < lanes {
                return Err("SIMD bitmask size".into());
            }
            let width = if lanes <= 64 { 64 } else { 128 };
            let sign_bit = self.imm((bits - 1) as u128);
            let mut value = self.imm(0);
            for i in 0..lanes {
                let lane = self.vector_lane(left, i, bits)?;
                let sign = self.bin(Binary::Shr, lane, sign_bit, bits, false).0;
                let shift = self.imm(i as u128);
                let placed = self.bin(Binary::Shl, sign, shift, width, false).0;
                value = self.bin(Binary::Or, value, placed, width, false).0;
            }
            self.store(dest.address, value, result_size)?;
            return Ok(true);
        }
        if [
            "simd_reduce_max",
            "simd_reduce_min",
            "simd_reduce_or",
            "simd_reduce_and",
            "simd_reduce_xor",
            "simd_reduce_add_unordered",
            "simd_reduce_mul_unordered",
            "simd_reduce_any",
            "simd_reduce_all",
        ]
        .contains(&name)
        {
            let mut value = self.vector_lane(left, 0, bits)?;
            for i in 1..lanes {
                let lane = self.vector_lane(left, i, bits)?;
                if name == "simd_reduce_max" || name == "simd_reduce_min" {
                    let choose = self
                        .bin(
                            if name == "simd_reduce_max" {
                                Binary::Gt
                            } else {
                                Binary::Lt
                            },
                            value,
                            lane,
                            bits,
                            signed,
                        )
                        .0;
                    let dst = self.reg();
                    self.code.push(Op::Select {
                        dst,
                        condition: choose,
                        yes: value,
                        no: lane,
                    });
                    value = dst;
                } else {
                    let op = match name {
                        "simd_reduce_or" | "simd_reduce_any" => Binary::Or,
                        "simd_reduce_and" | "simd_reduce_all" => Binary::And,
                        "simd_reduce_xor" => Binary::Xor,
                        "simd_reduce_add_unordered" => Binary::Add,
                        _ => Binary::Mul,
                    };
                    value = self.bin(op, value, lane, bits, signed).0;
                }
            }
            if name == "simd_reduce_any" || name == "simd_reduce_all" {
                let zero = self.imm(0);
                value = self.bin(Binary::Ne, value, zero, bits, false).0;
            }
            self.store(dest.address, value, result_size)?;
            return Ok(true);
        }
        if name == "simd_extract"
            || name == "simd_extract_dyn"
            || name == "simd_insert"
            || name == "simd_insert_dyn"
        {
            let index = self.scalar(&args.get(1).ok_or("missing SIMD index")?.node)?;
            let limit = self.imm(lanes as u128);
            let valid = self.bin(Binary::Lt, index, limit, 64, false).0;
            self.code.push(Op::Assert {
                value: valid,
                expected: true,
                message: "SIMD index".into(),
            });
            let stride = self.imm((bits / 8) as u128);
            let offset = self.bin(Binary::Mul, index, stride, 64, false).0;
            if name.starts_with("simd_extract") {
                let address = self.bin(Binary::Add, left, offset, 64, false).0;
                let value = self.load(address, bits as usize / 8)?;
                self.store(dest.address, value, result_size)?;
            } else {
                if self.vector_shape(dest.ty)? != (lanes, bits, signed) {
                    return Err("SIMD insert shape".into());
                }
                let value = self.scalar(&args.get(2).ok_or("missing SIMD inserted value")?.node)?;
                self.code.push(Op::Copy {
                    dst: dest.address,
                    src: left,
                    size: result_size,
                });
                let address = self.bin(Binary::Add, dest.address, offset, 64, false).0;
                self.store(address, value, bits as usize / 8)?;
            }
            return Ok(true);
        }

        let (out_lanes, out_bits, _) = self.vector_shape(dest.ty)?;
        if name == "simd_cast" || name == "simd_as" {
            if out_lanes != lanes {
                return Err("SIMD cast lane count".into());
            }
            for i in 0..lanes {
                let src = self.vector_lane(left, i, bits)?;
                let dst = self.reg();
                self.code.push(Op::Cast {
                    dst,
                    src,
                    from: bits,
                    to: out_bits,
                    signed,
                });
                self.store_lane(dest.address, i, out_bits, dst)?;
            }
            return Ok(true);
        }
        let second = args.get(1).ok_or("missing second SIMD vector")?;
        if self.vector_shape(self.operand_ty(&second.node))? != (lanes, bits, signed) {
            return Err("SIMD input shape mismatch".into());
        }
        let right = self.snapshot_operand(&second.node)?;
        if name == "simd_shuffle" {
            if out_bits != bits {
                return Err("SIMD shuffle element width".into());
            }
            let indices = args.get(2).ok_or("missing SIMD shuffle indices")?;
            if self.vector_shape(self.operand_ty(&indices.node))? != (out_lanes, 32, false) {
                return Err("SIMD shuffle index shape".into());
            }
            let indices = self.snapshot_operand(&indices.node)?;
            let limit = self.imm((lanes * 2) as u128);
            let half = self.imm(lanes as u128);
            let stride = self.imm((bits / 8) as u128);
            for i in 0..out_lanes {
                let index = self.vector_lane(indices, i, 32)?;
                let valid = self.bin(Binary::Lt, index, limit, 64, false).0;
                self.code.push(Op::Assert {
                    value: valid,
                    expected: true,
                    message: "SIMD shuffle index".into(),
                });
                let in_left = self.bin(Binary::Lt, index, half, 64, false).0;
                let relative = self.bin(Binary::Sub, index, half, 64, false).0;
                let selected_index = self.reg();
                self.code.push(Op::Select {
                    dst: selected_index,
                    condition: in_left,
                    yes: index,
                    no: relative,
                });
                let selected_base = self.reg();
                self.code.push(Op::Select {
                    dst: selected_base,
                    condition: in_left,
                    yes: left,
                    no: right,
                });
                let offset = self.bin(Binary::Mul, selected_index, stride, 64, false).0;
                let address = self.bin(Binary::Add, selected_base, offset, 64, false).0;
                let value = self.load(address, bits as usize / 8)?;
                self.store_lane(dest.address, i, bits, value)?;
            }
            return Ok(true);
        }
        let op = match name {
            "simd_add" => Binary::Add,
            "simd_sub" => Binary::Sub,
            "simd_mul" => Binary::Mul,
            "simd_and" => Binary::And,
            "simd_or" => Binary::Or,
            "simd_xor" => Binary::Xor,
            "simd_shl" => Binary::Shl,
            "simd_shr" => Binary::Shr,
            "simd_eq" => Binary::Eq,
            "simd_ne" => Binary::Ne,
            "simd_lt" => Binary::Lt,
            "simd_le" => Binary::Le,
            "simd_gt" => Binary::Gt,
            "simd_ge" => Binary::Ge,
            _ => return Err(format!("unsupported integer SIMD intrinsic {name}")),
        };
        if (out_lanes, out_bits) != (lanes, bits) {
            return Err("SIMD result shape mismatch".into());
        }
        let comparison = matches!(
            op,
            Binary::Eq | Binary::Ne | Binary::Lt | Binary::Le | Binary::Gt | Binary::Ge
        );
        for i in 0..lanes {
            let a = self.vector_lane(left, i, bits)?;
            let b = self.vector_lane(right, i, bits)?;
            let mut value = self.bin(op, a, b, bits, signed).0;
            if comparison {
                let zero = self.imm(0);
                value = self.bin(Binary::Sub, zero, value, bits, false).0;
            }
            self.store_lane(dest.address, i, bits, value)?;
        }
        Ok(true)
    }
}
