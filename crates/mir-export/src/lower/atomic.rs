//! Atomic operations for one guest thread with exclusively owned guest memory.
//!
//! There are no guest threads, host callbacks, signal handlers, shared mappings,
//! or resumable executions that can observe an operation partway through. Thus
//! ordered checked loads/stores implement an allowed sequential execution of
//! every supported ordering. Adding any such concurrency requires revisiting
//! this lowering; these sequences are not a concurrent atomic implementation.
use super::*;
use rustc_middle::ty::AtomicOrdering;

impl<'a, 'tcx> Lower<'a, 'tcx> {
    pub(super) fn atomic_intrinsic(
        &mut self,
        instance: Instance<'tcx>,
        name: &str,
        args: &[rustc_span::Spanned<Operand<'tcx>>],
        dest: Location<'tcx>,
    ) -> Result<bool> {
        use AtomicOrdering::*;
        let order = |index| {
            instance.args.const_at(index).to_value().to_branch()[0]
                .to_leaf()
                .to_atomic_ordering()
        };
        if matches!(name, "atomic_fence" | "atomic_singlethreadfence") {
            if !args.is_empty() || self.layout(dest.ty)?.size.bytes() != 0 {
                return Err("invalid atomic fence signature".into());
            }
            if matches!(order(0), Relaxed) {
                return Err("invalid relaxed atomic fence".into());
            }
            return Ok(true);
        }
        let two_types = matches!(
            name,
            "atomic_xadd"
                | "atomic_xsub"
                | "atomic_and"
                | "atomic_nand"
                | "atomic_or"
                | "atomic_xor"
        );
        let exchange = matches!(name, "atomic_cxchg" | "atomic_cxchgweak");
        let count = match name {
            "atomic_load" => 1,
            "atomic_store" | "atomic_xchg" | "atomic_xadd" | "atomic_xsub" | "atomic_and"
            | "atomic_nand" | "atomic_or" | "atomic_xor" | "atomic_max" | "atomic_min"
            | "atomic_umax" | "atomic_umin" => 2,
            "atomic_cxchg" | "atomic_cxchgweak" => 3,
            _ => return Err(format!("unsupported intrinsic {name}")),
        };
        if args.len() != count {
            return Err("atomic intrinsic arity".into());
        }
        let ty = instance.args.type_at(0);
        if !matches!(ty.kind(), ty::Int(_) | ty::Uint(_) | ty::RawPtr(..)) {
            return Err(format!("unsupported atomic value type {ty}"));
        }
        let (bits, signed) = self.integer(ty)?;
        let bytes = (bits / 8) as usize;
        if two_types {
            let second = instance.args.type_at(1);
            if !((ty.is_integral() && second == ty)
                || (ty.is_raw_ptr() && second == self.tcx().types.usize))
            {
                return Err("atomic arithmetic argument type mismatch".into());
            }
        }
        if (matches!(name, "atomic_max" | "atomic_min") && !matches!(ty.kind(), ty::Int(_)))
            || (matches!(name, "atomic_umax" | "atomic_umin") && !matches!(ty.kind(), ty::Uint(_)))
        {
            return Err("atomic min/max signedness mismatch".into());
        }
        let ordering = order(if two_types { 2 } else { 1 });
        if (name == "atomic_load" && matches!(ordering, Release | AcqRel))
            || (name == "atomic_store" && matches!(ordering, Acquire | AcqRel))
            || (exchange && matches!(order(2), Release | AcqRel))
        {
            return Err("invalid atomic memory ordering".into());
        }
        // Every access is executed, including volatile guest-memory accesses.
        // External memory and MMIO cannot be represented by a guest pointer.
        let address = self.scalar(&args[0].node)?;
        let align_mask = self.imm((bytes - 1) as u128);
        let misaligned = self.bin(Binary::And, address, align_mask, 64, false).0;
        self.code.push(Op::Assert {
            value: misaligned,
            expected: false,
            message: "unaligned atomic memory access".into(),
        });
        if name == "atomic_store" {
            let value = self.scalar(&args[1].node)?;
            self.store(address, value, bytes)?;
            return Ok(true);
        }
        let old = self.load(address, bytes)?;
        if name == "atomic_load" {
            self.store(dest.address, old, bytes)?;
            return Ok(true);
        }
        let rhs = self.scalar(&args[1].node)?;
        if exchange {
            let new = self.scalar(&args[2].node)?;
            let equal = self.bin(Binary::Eq, old, rhs, bits, false).0;
            // Weak CAS is allowed to succeed whenever the comparison matches.
            // Do not write at all on failure, even when the bytes would agree.
            let branch = self.code.len();
            self.code.push(Op::Switch {
                value: equal,
                cases: vec![],
                otherwise: branch + 1,
            });
            self.store(address, new, bytes)?;
            let after = self.code.len();
            if let Op::Switch { cases, .. } = &mut self.code[branch] {
                cases.push((0, after));
            }
            let layout = self.layout(dest.ty)?;
            let old_at = self.add(dest.address, self.field_offset(layout, 0)?);
            let ok_at = self.add(dest.address, self.field_offset(layout, 1)?);
            self.store(old_at, old, bytes)?;
            self.store(ok_at, equal, 1)?;
            return Ok(true);
        }
        let new = match name {
            "atomic_xchg" => rhs,
            "atomic_xadd" => self.bin(Binary::Add, old, rhs, bits, false).0,
            "atomic_xsub" => self.bin(Binary::Sub, old, rhs, bits, false).0,
            "atomic_and" => self.bin(Binary::And, old, rhs, bits, false).0,
            "atomic_or" => self.bin(Binary::Or, old, rhs, bits, false).0,
            "atomic_xor" => self.bin(Binary::Xor, old, rhs, bits, false).0,
            "atomic_nand" => {
                let and = self.bin(Binary::And, old, rhs, bits, false).0;
                let dst = self.reg();
                self.code.push(Op::Unary {
                    dst,
                    op: Unary::Not,
                    src: and,
                    bits,
                });
                dst
            }
            "atomic_max" | "atomic_min" | "atomic_umax" | "atomic_umin" => {
                let op = if matches!(name, "atomic_max" | "atomic_umax") {
                    Binary::Gt
                } else {
                    Binary::Lt
                };
                let condition = self.bin(op, old, rhs, bits, signed).0;
                let dst = self.reg();
                self.code.push(Op::Select {
                    dst,
                    condition,
                    yes: old,
                    no: rhs,
                });
                dst
            }
            _ => unreachable!(),
        };
        self.store(address, new, bytes)?;
        self.store(dest.address, old, bytes)?;
        Ok(true)
    }
}
