use super::*;

#[test]
fn signed_branch_boundaries_are_exact_without_offset_wrapping() {
    for (bits, kind) in [(19, CodegenLimit::ConditionalBranch), (26, CodegenLimit::Jump)] {
        let half = 1usize << (bits - 1);
        assert_eq!(branch_displacement(0, half - 1, bits, kind), Ok((half - 1) as u32));
        assert_eq!(branch_displacement(half, 0, bits, kind), Ok(half as u32));
        assert_eq!(branch_displacement(0, half, bits, kind), Err(EmitError::Limit(kind)));
        assert_eq!(branch_displacement(half + 1, 0, bits, kind), Err(EmitError::Limit(kind)));
        assert_eq!(branch_displacement(usize::MAX, 0, bits, kind), Err(EmitError::Limit(kind)));
        assert_eq!(branch_displacement(0, usize::MAX, bits, kind), Err(EmitError::Limit(kind)));
        assert_eq!(branch_displacement(usize::MAX - 1, usize::MAX, bits, kind), Ok(1));
    }
}

#[test]
fn assertion_number_exhaustion_is_a_limit_including_usize_overflow() {
    assert_eq!(assertion_code(0, 0), Ok(ASSERTION_FAILURE_BASE));
    assert_eq!(assertion_code(2, 3), Ok(ASSERTION_FAILURE_BASE - 5));
    assert_eq!(assertion_code(usize::MAX, 1), Err(EmitError::Limit(CodegenLimit::Assertions)));
    if let Ok(last) = usize::try_from(ASSERTION_FAILURE_BASE - FAILURE_MIN) {
        assert_eq!(assertion_code(last, 0), Ok(FAILURE_MIN));
        assert_eq!(assertion_code(last, 1), Err(EmitError::Limit(CodegenLimit::Assertions)));
    }
}

#[test]
fn invalid_relocations_are_distinct_from_encoding_limits_and_do_not_mutate_code() {
    let mut a = Assembler::default();
    a.words = vec![0x54000001, 0x14000000, 0xd65f03c0];
    let original = a.words.clone();
    for (at, target) in [(3, 0), (1, 0), (0, 4)] {
        assert!(matches!(a.patch_conditional(at, target), Err(EmitError::InvalidRelocation(_))));
        assert_eq!(a.words, original);
    }
    a.patch_conditional(0, 3).unwrap(); // local forward label, next word to append
    assert_eq!(a.words[0], 0x54000061);
    assert!(matches!(a.patch_conditional(0, 2), Err(EmitError::InvalidRelocation(_))));
    assert_eq!(a.words[0], 0x54000061);
    assert!(matches!(patch_jump(&mut a.words, 2, 0), Err(EmitError::InvalidRelocation(_))));
    patch_jump(&mut a.words, 1, 0).unwrap();
    assert_eq!(a.words[1], 0x17ffffff);
}
