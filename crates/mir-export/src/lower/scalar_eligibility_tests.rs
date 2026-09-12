use super::*;
use rustc_middle::mir::visit::NonUseContext;

fn contexts() -> Vec<(PlaceContext, bool)> {
    let mut contexts = vec![];
    for context in [NonUseContext::StorageLive, NonUseContext::StorageDead,
        NonUseContext::AscribeUserTy(ty::Variance::Covariant),
        NonUseContext::AscribeUserTy(ty::Variance::Contravariant),
        NonUseContext::AscribeUserTy(ty::Variance::Invariant),
        NonUseContext::AscribeUserTy(ty::Variance::Bivariant),
        NonUseContext::VarDebugInfo, NonUseContext::BackwardIncompatibleDropHint]
    {
        contexts.push((PlaceContext::NonUse(context), true));
    }
    for (context, preserves) in [(NonMutatingUseContext::Copy, true),
        (NonMutatingUseContext::Move, true), (NonMutatingUseContext::Inspect, false),
        (NonMutatingUseContext::SharedBorrow, false), (NonMutatingUseContext::FakeBorrow, false),
        (NonMutatingUseContext::RawBorrow, false), (NonMutatingUseContext::PlaceMention, false),
        (NonMutatingUseContext::Projection, false)]
    {
        contexts.push((PlaceContext::NonMutatingUse(context), preserves));
    }
    for (context, preserves) in [(MutatingUseContext::Store, true),
        (MutatingUseContext::SetDiscriminant, false), (MutatingUseContext::AsmOutput, false),
        (MutatingUseContext::Call, false), (MutatingUseContext::Yield, false),
        (MutatingUseContext::Drop, false), (MutatingUseContext::Borrow, false),
        (MutatingUseContext::RawBorrow, false), (MutatingUseContext::Projection, false)]
    {
        contexts.push((PlaceContext::MutatingUse(context), preserves));
    }
    contexts
}

fn fallback_context(eligible: &mut [bool], local: mir::Local, context: PlaceContext) {
    Uses { eligible }.visit_local(local, context,
        mir::Location { block: mir::START_BLOCK, statement_index: 0 });
}

#[test]
fn packing_and_fallback_visitors_match_every_pinned_context_policy() {
    let local = mir::Local::from_usize(1);
    for (context, preserves) in contexts() {
        for initially_eligible in [false, true] {
            let mut packed = [true, initially_eligible, false];
            let mut fallback = packed;
            scalar_frame::visit_eligibility_context(&mut packed, local, context);
            fallback_context(&mut fallback, local, context);
            assert_eq!(packed, [true, initially_eligible && preserves, false], "{context:?}");
            assert_eq!(packed, fallback, "{context:?}");
        }
    }
}

#[test]
fn direct_operand_exclusions_commute_with_packing_and_fallback_visitors() {
    let first = mir::Local::from_usize(0);
    let second = mir::Local::from_usize(1);
    for (before, _) in contexts() {
        for (after, _) in contexts() {
            for operand in [Operand::Copy(Place::from(first)), Operand::Move(Place::from(first))] {
                let mut interleaved = [true; 3];
                fallback_context(&mut interleaved, first, before);
                exclude_operand(&mut interleaved, &operand);
                fallback_context(&mut interleaved, second, after);

                let mut reused = [true; 3];
                scalar_frame::visit_eligibility_context(&mut reused, first, before);
                scalar_frame::visit_eligibility_context(&mut reused, second, after);
                exclude_operand(&mut reused, &operand);
                assert_eq!(reused, interleaved, "before={before:?} after={after:?}");
                assert!(!reused[0]);
                assert!(reused[2]); // unrelated private scalar remains eligible
            }
        }
    }
}
