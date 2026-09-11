//! Normal-control-flow reachability after monomorphization. Strict rustc type
//! and borrow checking precedes this backend analysis. No runtime test selection
//! or guessed branch probabilities participate in the proof.
use super::*;

impl<'tcx> Lower<'_, 'tcx> {
    pub(super) fn reachable_blocks(&self) -> Result<Vec<bool>> {
        // We only infer values for an integer temporary whose address is never
        // taken, and whose last assignment in the same block is Discriminant.
        // Calls cannot occur between a MIR statement and its terminator.
        let mut exposed = HashSet::new();
        for block in self.body.basic_blocks.iter() {
            for statement in &block.statements {
                if let StatementKind::Assign(pair) = &statement.kind {
                    if let Rvalue::Ref(_, _, place) | Rvalue::RawPtr(_, place) = &pair.1 {
                        exposed.insert(place.local);
                    }
                }
            }
        }
        let mut reachable = vec![false; self.body.basic_blocks.len()];
        let mut pending = vec![mir::START_BLOCK];
        while let Some(bb) = pending.pop() {
            if reachable[bb.as_usize()] { continue; }
            reachable[bb.as_usize()] = true;
            let block = &self.body.basic_blocks[bb];
            match &block.terminator().kind {
                TerminatorKind::SwitchInt { discr, targets } => {
                    let mut domain = None;
                    if let Operand::Copy(place) | Operand::Move(place) = discr {
                        if place.projection.is_empty() && !exposed.contains(&place.local) {
                            for statement in block.statements.iter().rev() {
                                if let StatementKind::Assign(pair) = &statement.kind {
                                    if pair.0.local != place.local { continue; }
                                    if pair.0.projection.is_empty() {
                                        if let Rvalue::Discriminant(value) = &pair.1 {
                                            let ty = self.mono(value.ty(&self.body.local_decls, self.tcx()).ty);
                                            if let ty::Adt(adt, _) = ty.kind() {
                                                if adt.is_enum() {
                                                    let layout = self.layout(ty)?;
                                                    let bits = self.layout(self.operand_ty(discr))?.size.bits();
                                                    let mask = u128::MAX >> (128 - bits);
                                                    let values = adt.discriminants(self.tcx())
                                                        .filter(|(variant, _)| !layout.is_variant_uninhabited(*variant))
                                                        .map(|(_, value)| value.val & mask).collect::<HashSet<_>>();
                                                    domain = Some(values);
                                                }
                                            }
                                        }
                                    }
                                    break;
                                }
                            }
                        }
                    }
                    if let Some(mut values) = domain {
                        for (value, target) in targets.iter() {
                            if values.remove(&value) { pending.push(target); }
                        }
                        if !values.is_empty() { pending.push(targets.otherwise()); }
                    } else { pending.extend(targets.all_targets()); }
                }
                // Unwinding never occurs in this engine: a panic terminates
                // execution. Do not expand cleanup-only calls or destructors.
                TerminatorKind::Call { target, .. } => pending.extend(target),
                TerminatorKind::Drop { target, .. } | TerminatorKind::Assert { target, .. } => pending.push(*target),
                other => pending.extend(other.successors()),
            }
        }
        Ok(reachable)
    }
}
