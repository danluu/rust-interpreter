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
