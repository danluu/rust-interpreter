//! Floating-point MIR lowers to our runtime operations, with explicit widths.
use super::*;
use rust_interp_bytecode::{FloatBinary, FloatConversion, FloatUnary};

impl<'a, 'tcx> Lower<'a, 'tcx> {
    pub(super) fn float_width(&self, ty: Ty<'tcx>) -> Result<u8> {
        match ty.kind() {
            ty::Float(ty::FloatTy::F32) => Ok(32),
            ty::Float(ty::FloatTy::F64) => Ok(64),
            _ => Err(format!("unsupported floating-point type {ty}")),
        }
    }

    pub(super) fn float_binary(
        &mut self,
        operation: BinOp,
        a: &Operand<'tcx>,
        b: &Operand<'tcx>,
        dest: Location<'tcx>,
    ) -> Result<()> {
        let bits = self.float_width(self.operand_ty(a))?;
        let op = match operation {
            BinOp::Add => FloatBinary::Add,
            BinOp::Sub => FloatBinary::Sub,
            BinOp::Mul => FloatBinary::Mul,
            BinOp::Div => FloatBinary::Div,
            BinOp::Rem => FloatBinary::Rem,
            BinOp::Eq => FloatBinary::Eq,
            BinOp::Ne => FloatBinary::Ne,
            BinOp::Lt => FloatBinary::Lt,
            BinOp::Le => FloatBinary::Le,
            BinOp::Gt => FloatBinary::Gt,
            BinOp::Ge => FloatBinary::Ge,
            _ => {
                return Err(format!(
                    "unsupported floating-point operation {operation:?}"
                ));
            }
        };
        let a = self.scalar(a)?;
        let b = self.scalar(b)?;
        let dst = self.reg();
        self.code.push(Op::FloatBinary {
            dst,
            op,
            a,
            b,
            bits,
        });
        self.store(dest.address, dst, self.layout(dest.ty)?.size.bytes_usize())
    }

    pub(super) fn float_negate(
        &mut self,
        operand: &Operand<'tcx>,
        dest: Location<'tcx>,
    ) -> Result<()> {
        let bits = self.float_width(self.operand_ty(operand))?;
        let src = self.scalar(operand)?;
        let dst = self.reg();
        self.code.push(Op::FloatUnary {
            dst,
            op: FloatUnary::Neg,
            src,
            bits,
        });
        self.store(dest.address, dst, (bits / 8) as usize)
    }

    pub(super) fn float_cast(
        &mut self,
        cast: CastKind,
        operand: &Operand<'tcx>,
        dest: Location<'tcx>,
    ) -> Result<()> {
        let source = self.operand_ty(operand);
        let (kind, from, to) = match cast {
            CastKind::IntToFloat => {
                let (from, signed) = self.integer(source)?;
                (
                    FloatConversion::IntToFloat { signed },
                    from,
                    self.float_width(dest.ty)?,
                )
            }
            CastKind::FloatToInt => {
                let (to, signed) = self.integer(dest.ty)?;
                (
                    FloatConversion::FloatToInt { signed },
                    self.float_width(source)?,
                    to,
                )
            }
            CastKind::FloatToFloat => (
                FloatConversion::FloatToFloat,
                self.float_width(source)?,
                self.float_width(dest.ty)?,
            ),
            _ => return Err("invalid floating-point cast".into()),
        };
        let src = self.scalar(operand)?;
        let dst = self.reg();
        self.code.push(Op::FloatConvert {
            dst,
            kind,
            src,
            from,
            to,
        });
        self.store(dest.address, dst, (to / 8) as usize)
    }

    pub(super) fn float_intrinsic(
        &mut self,
        name: &str,
        args: &[rustc_span::Spanned<Operand<'tcx>>],
        dest: Location<'tcx>,
    ) -> Result<bool> {
        let unary = match name {
            "fabs" => Some(FloatUnary::Abs),
            "roundf32" | "roundf64" => Some(FloatUnary::Round),
            "round_ties_even_f32" | "round_ties_even_f64" => Some(FloatUnary::RoundTiesEven),
            "ceilf32" | "ceilf64" => Some(FloatUnary::Ceil),
            "floorf32" | "floorf64" => Some(FloatUnary::Floor),
            "truncf32" | "truncf64" => Some(FloatUnary::Trunc),
            "sqrtf32" | "sqrtf64" => Some(FloatUnary::Sqrt),
            "log10" => Some(FloatUnary::Log10),
            _ => None,
        };
        let binary = match name {
            "minimum_number_nsz_f32" | "minimum_number_nsz_f64" => Some(FloatBinary::MinNumber),
            "maximum_number_nsz_f32" | "maximum_number_nsz_f64" => Some(FloatBinary::MaxNumber),
            "powif32" | "powif64" => Some(FloatBinary::PowI),
            "copysignf32" | "copysignf64" => Some(FloatBinary::CopySign),
            _ => None,
        };
        if unary.is_none() && binary.is_none() {
            return Ok(false);
        }
        let expected = if unary.is_some() { 1 } else { 2 };
        if args.len() != expected {
            return Err("floating-point intrinsic arity".into());
        }
        let bits = self.float_width(self.operand_ty(&args[0].node))?;
        if self.float_width(dest.ty)? != bits {
            return Err("floating-point intrinsic result width".into());
        }
        let a = self.scalar(&args[0].node)?;
        let dst = self.reg();
        if let Some(op) = unary {
            self.code.push(Op::FloatUnary {
                dst,
                op,
                src: a,
                bits,
            });
        } else if let Some(op) = binary {
            let second = self.operand_ty(&args[1].node);
            if matches!(op, FloatBinary::PowI) {
                if !matches!(second.kind(), ty::Int(ty::IntTy::I32)) {
                    return Err("powi exponent must be i32".into());
                }
            } else if self.float_width(second)? != bits {
                return Err("floating-point intrinsic argument width".into());
            }
            let b = self.scalar(&args[1].node)?;
            self.code.push(Op::FloatBinary {
                dst,
                op,
                a,
                b,
                bits,
            });
        }
        self.store(dest.address, dst, (bits / 8) as usize)?;
        Ok(true)
    }
}
