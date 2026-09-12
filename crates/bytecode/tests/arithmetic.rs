use rust_interp_bytecode::{Binary, binary};

#[test]
fn every_u8_pair_matches_native_checked_arithmetic() {
    for a in 0..=u8::MAX {
        for b in 0..=u8::MAX {
            for (op, expected) in [
                (Binary::Add, a.overflowing_add(b)),
                (Binary::Sub, a.overflowing_sub(b)),
                (Binary::Mul, a.overflowing_mul(b)),
            ] {
                assert_eq!(
                    binary(op, a as u128, b as u128, 8, false).unwrap(),
                    (expected.0 as u128, expected.1)
                );
            }
            let (sa, sb) = (a as i8, b as i8);
            for (op, expected) in [
                (Binary::Add, sa.overflowing_add(sb)),
                (Binary::Sub, sa.overflowing_sub(sb)),
                (Binary::Mul, sa.overflowing_mul(sb)),
            ] {
                assert_eq!(
                    binary(op, a as u128, b as u128, 8, true).unwrap(),
                    (expected.0 as u8 as u128, expected.1)
                );
            }
            assert_eq!(
                binary(Binary::RotateLeft, a as u128, b as u128, 8, false)
                    .unwrap()
                    .0,
                a.rotate_left(b as u32) as u128
            );
            assert_eq!(
                binary(Binary::Shr, a as u128, b as u128, 8, true)
                    .unwrap()
                    .0,
                (sa >> (b % 8)) as u8 as u128
            );
        }
    }
}

#[test]
fn boundary_128_bit_arithmetic() {
    let values = [
        0,
        1,
        127,
        128,
        u64::MAX as u128,
        (1u128 << 127) - 1,
        1u128 << 127,
        u128::MAX,
    ];
    for a in values {
        for b in values {
            for (op, expected) in [
                (Binary::Add, a.overflowing_add(b)),
                (Binary::Sub, a.overflowing_sub(b)),
                (Binary::Mul, a.overflowing_mul(b)),
            ] {
                assert_eq!(binary(op, a, b, 128, false).unwrap(), expected);
            }
            let (sa, sb) = (a as i128, b as i128);
            for (op, expected) in [
                (Binary::Add, sa.overflowing_add(sb)),
                (Binary::Sub, sa.overflowing_sub(sb)),
                (Binary::Mul, sa.overflowing_mul(sb)),
            ] {
                assert_eq!(
                    binary(op, a, b, 128, true).unwrap(),
                    (expected.0 as u128, expected.1)
                );
            }
        }
    }
    assert!(binary(Binary::Div, 128, 255, 8, true).is_err());
    assert!(binary(Binary::Rem, 128, 255, 8, true).is_err());
    assert!(binary(Binary::Div, 1, 0, 64, false).is_err());
}

#[test]
fn shifts_and_rotates_match_native_widths_with_full_width_counts() {
    let values = [
        0,
        1,
        0x80,
        0x8000,
        0x8000_0000,
        1u128 << 63,
        1u128 << 127,
        0x8123_4567_89ab_cdef_fedc_ba98_7654_3210,
        u128::MAX,
    ];
    let counts = [
        0,
        1,
        7,
        8,
        15,
        16,
        31,
        32,
        63,
        64,
        65,
        127,
        128,
        129,
        255,
        (1u128 << 32) | 7,
        1u128 << 64,
        (1u128 << 96) | 127,
        (1u128 << 127) | 65,
        u128::MAX,
    ];
    macro_rules! check_width {
        ($unsigned:ty, $signed:ty) => {
            for value in values {
                for count in counts {
                    let native = value as $unsigned;
                    // Native wrapping shifts and rotates accept u32 counts.
                    // Higher count bits represent whole rotations at every
                    // supported width, so dropping them preserves the result.
                    let native_count = count as u32;
                    for signed in [false, true] {
                        let right = if signed {
                            (value as $signed).wrapping_shr(native_count) as $unsigned
                        } else {
                            native.wrapping_shr(native_count)
                        };
                        for (op, expected) in [
                            (Binary::Shl, native.wrapping_shl(native_count)),
                            (Binary::Shr, right),
                            (Binary::RotateLeft, native.rotate_left(native_count)),
                            (Binary::RotateRight, native.rotate_right(native_count)),
                        ] {
                            assert_eq!(
                                binary(op, value, count, <$unsigned>::BITS as u8, signed),
                                Ok((expected as u128, false)),
                                "{op:?}, width={}, signed={signed}, value={value:x}, count={count:x}",
                                <$unsigned>::BITS,
                            );
                        }
                    }
                }
            }
        };
    }
    check_width!(u8, i8);
    check_width!(u16, i16);
    check_width!(u32, i32);
    check_width!(u64, i64);
    check_width!(u128, i128);
}

#[test]
fn division_and_remainder_match_native_widths_and_faults() {
    macro_rules! check_width {
        ($unsigned:ty, $signed:ty) => {
            let sign = <$signed>::MIN as $unsigned as u128;
            let max = <$unsigned>::MAX as u128;
            let values = [
                0,
                1,
                2,
                3,
                sign - 1,
                sign,
                sign + 1,
                max - 1,
                max,
                1u128 << 127,
                (1u128 << 127) | 3,
                0x8123_4567_89ab_cdef_fedc_ba98_7654_3210,
                u128::MAX,
            ];
            for a in values {
                for b in values {
                    let (ua, ub) = (a as $unsigned, b as $unsigned);
                    for (op, expected) in [
                        (Binary::Div, ua.checked_div(ub)),
                        (Binary::Rem, ua.checked_rem(ub)),
                    ] {
                        let expected = expected
                            .map(|value| (value as u128, false))
                            .ok_or_else(|| "integer division by zero".to_owned());
                        assert_eq!(
                            binary(op, a, b, <$unsigned>::BITS as u8, false),
                            expected,
                            "{op:?}, width={}, unsigned, a={a:x}, b={b:x}",
                            <$unsigned>::BITS,
                        );
                    }
                    let (sa, sb) = (a as $signed, b as $signed);
                    for (op, expected) in [
                        (Binary::Div, sa.checked_div(sb)),
                        (Binary::Rem, sa.checked_rem(sb)),
                    ] {
                        let expected = expected
                            .map(|value| (value as $unsigned as u128, false))
                            .ok_or_else(|| {
                                if sb == 0 {
                                    "integer division by zero"
                                } else {
                                    "signed division overflow"
                                }
                                .to_owned()
                            });
                        assert_eq!(
                            binary(op, a, b, <$unsigned>::BITS as u8, true),
                            expected,
                            "{op:?}, width={}, signed, a={a:x}, b={b:x}",
                            <$unsigned>::BITS,
                        );
                    }
                }
            }
        };
    }
    check_width!(u8, i8);
    check_width!(u16, i16);
    check_width!(u32, i32);
    check_width!(u64, i64);
    check_width!(u128, i128);
}

#[test]
fn shifts_rotates_and_division_reject_every_unsupported_width() {
    for bits in 0..=u8::MAX {
        if [8, 16, 32, 64, 128].contains(&bits) {
            continue;
        }
        for op in [
            Binary::Shl,
            Binary::Shr,
            Binary::RotateLeft,
            Binary::RotateRight,
            Binary::Div,
            Binary::Rem,
        ] {
            for signed in [false, true] {
                assert_eq!(
                    binary(op, u128::MAX, 0, bits, signed),
                    Err("invalid integer width".into()),
                    "{op:?}, width={bits}, signed={signed}",
                );
            }
        }
    }
}

#[test]
fn comparisons_match_native_ordering_after_guest_width_truncation() {
    use std::cmp::Ordering;

    macro_rules! check_width {
        ($unsigned:ty, $signed:ty) => {
            let sign = <$signed>::MIN as $unsigned as u128;
            let max = <$unsigned>::MAX as u128;
            let values = [
                0,
                1,
                sign - 1,
                sign,
                sign + 1,
                max - 1,
                max,
                1u128 << 127,
                (1u128 << 127) | 1,
                0x8123_4567_89ab_cdef_fedc_ba98_7654_3210,
                u128::MAX,
            ];
            for a in values {
                for b in values {
                    for (signed, ordering) in [
                        (false, (a as $unsigned).cmp(&(b as $unsigned))),
                        (true, (a as $signed).cmp(&(b as $signed))),
                    ] {
                        let comparison = match ordering {
                            Ordering::Less => 255,
                            Ordering::Equal => 0,
                            Ordering::Greater => 1,
                        };
                        for (op, expected) in [
                            (Binary::Eq, u128::from(ordering.is_eq())),
                            (Binary::Ne, u128::from(ordering.is_ne())),
                            (Binary::Lt, u128::from(ordering.is_lt())),
                            (Binary::Le, u128::from(ordering.is_le())),
                            (Binary::Gt, u128::from(ordering.is_gt())),
                            (Binary::Ge, u128::from(ordering.is_ge())),
                            (Binary::Cmp, comparison),
                        ] {
                            assert_eq!(
                                binary(op, a, b, <$unsigned>::BITS as u8, signed),
                                Ok((expected, false)),
                                "{op:?}, width={}, signed={signed}, a={a:x}, b={b:x}",
                                <$unsigned>::BITS,
                            );
                        }
                    }
                }
            }
        };
    }
    check_width!(u8, i8);
    check_width!(u16, i16);
    check_width!(u32, i32);
    check_width!(u64, i64);
    check_width!(u128, i128);
}
