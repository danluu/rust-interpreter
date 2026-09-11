#![feature(core_intrinsics, repr_simd)]
#![allow(internal_features)]
use std::intrinsics::simd::*;

#[repr(simd)] #[derive(Clone, Copy)] struct U8x16([u8;16]);
#[repr(simd)] #[derive(Clone, Copy)] struct I8x16([i8;16]);
#[repr(simd)] #[derive(Clone, Copy)] struct U8x8([u8;8]);
#[repr(simd)] #[derive(Clone, Copy)] struct I8x8([i8;8]);
#[repr(simd)] #[derive(Clone, Copy)] struct U16x8([u16;8]);
#[repr(simd)] #[derive(Clone, Copy)] struct I16x8([i16;8]);
#[repr(simd)] #[derive(Clone, Copy)] struct U32x16([u32;16]);
#[repr(simd)] #[derive(Clone, Copy)] struct U64x2([u64;2]);
#[repr(simd)] #[derive(Clone, Copy)] struct U128x2([u128;2]);
#[repr(simd)] #[derive(Clone, Copy)] struct I128x2([i128;2]);
const SHUFFLE: U32x16 = U32x16([31,0,17,2,19,4,21,6,23,8,25,10,27,12,29,14]);
const REVERSE: U32x16 = U32x16([15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0]);

fn mix(mut result: u64, bytes: &[u8]) -> u64 {
    for &b in bytes { result = result.rotate_left(7).wrapping_mul(31) ^ b as u64; }
    result
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut bytes = [0;16];
    for i in 0..16 {
        bytes[i] = (seed.rotate_left(i as u32 * 3) as u8).wrapping_add((i*17) as u8);
    }
    let mut result = seed;
    unsafe {
        macro_rules! vector16 { ($value:expr) => {{
            let bytes: [u8;16] = std::mem::transmute($value);
            result = mix(result, &bytes);
        }}; }
        let a = U8x16(bytes);
        let b: U8x16 = simd_splat(seed as u8);
        macro_rules! ordered {
            ($array:expr, $vector:ident, $initial:expr, $scalar:ty) => {{
                let lanes = $array;
                let initial: $scalar = $initial;
                let mut sum = initial;
                let mut product = initial;
                for lane in lanes { sum = sum.wrapping_add(lane); product = product.wrapping_mul(lane); }
                let actual_sum: $scalar = simd_reduce_add_ordered($vector(lanes),initial);
                let actual_product: $scalar = simd_reduce_mul_ordered($vector(lanes),initial);
                assert_eq!(actual_sum,sum); assert_eq!(actual_product,product);
                result = result.rotate_left(7) ^ actual_sum as u64 ^ actual_product as u64;
            }};
        }
        ordered!(bytes,U8x16,seed as u8,u8);
        ordered!([seed as i8,127,-128,-1,1,3,5,-7,11,13,-17,19,23,-29,31,37],I8x16,(seed>>8) as i8,i8);
        ordered!([seed as u16,65535,32768,1,3,7,11,13],U16x8,(seed>>16) as u16,u16);
        ordered!([seed as i16,32767,-32768,1,-3,7,-11,13],I16x8,(seed>>16) as i16,i16);
        ordered!([seed,u64::MAX],U64x2,seed.rotate_left(13),u64);
        let big = ((seed as u128) << 64) | ((!seed) as u128);
        ordered!([big,u128::MAX-2],U128x2,big.rotate_left(13),u128);
        ordered!([big as i128,i128::MIN+3],I128x2,big.rotate_left(7) as i128,i128);
        let narrow_bytes = [seed as u8,255,128,0,1,3,7,11];
        let narrow_sum = narrow_bytes.iter().fold(0u8,|sum,&byte|sum.wrapping_add(byte));
        assert_eq!(std::arch::aarch64::vaddv_u8(std::mem::transmute(narrow_bytes)),narrow_sum);
        let wide_sum = bytes.iter().fold(0u8,|sum,&byte|sum.wrapping_add(byte));
        assert_eq!(std::arch::aarch64::vaddvq_u8(std::mem::transmute(bytes)),wide_sum);
        vector16!(simd_add(a,b)); vector16!(simd_sub(a,b)); vector16!(simd_mul(a,b));
        vector16!(simd_and(a,b)); vector16!(simd_or(a,b)); vector16!(simd_xor(a,b));
        let eq: U8x16 = simd_eq(a,b);
        let lt: U8x16 = simd_lt(a,b);
        vector16!(eq); vector16!(lt);
        vector16!(simd_ne::<_,U8x16>(a,b)); vector16!(simd_le::<_,U8x16>(a,b));
        vector16!(simd_gt::<_,U8x16>(a,b)); vector16!(simd_ge::<_,U8x16>(a,b));
        result = result.wrapping_add(simd_bitmask::<_,u16>(lt) as u64);
        result = result.rotate_left(3) ^ simd_reduce_any(eq) as u64;
        result = result.rotate_left(3) ^ simd_reduce_all(eq) as u64;
        result = result.rotate_left(3) ^ simd_reduce_max::<_,u8>(a) as u64;
        result = result.rotate_left(3) ^ simd_reduce_min::<_,u8>(a) as u64;
        result = result.rotate_left(3) ^ simd_reduce_or::<_,u8>(a) as u64;
        result = result.rotate_left(3) ^ simd_reduce_and::<_,u8>(a) as u64;
        result = result.rotate_left(3) ^ simd_reduce_xor::<_,u8>(a) as u64;
        result = result.rotate_left(3) ^ simd_reduce_add_unordered::<_,u8>(a) as u64;
        result = result.rotate_left(3) ^ simd_reduce_mul_unordered::<_,u8>(a) as u64;
        let signed: I8x16 = std::mem::transmute(a);
        let signed_b: I8x16 = std::mem::transmute(b);
        vector16!(simd_lt::<_,I8x16>(signed,signed_b));
        result = result.rotate_left(3) ^ simd_reduce_min::<_,i8>(signed) as u64;
        result = result.rotate_left(3) ^ simd_reduce_max::<_,i8>(signed) as u64;
        result ^= simd_extract::<_,u8>(a, 7) as u64;
        result = result.rotate_left(3) ^ simd_extract_dyn::<_,u8>(a, (seed%16) as u32) as u64;
        vector16!(simd_insert(a, 3, (seed>>8) as u8));
        vector16!(simd_insert_dyn(a, (seed%16) as u32, (seed>>16) as u8));
        vector16!(simd_shuffle::<_,_,U8x16>(a,b,SHUFFLE));
        let mut aliased = a;
        for _ in 0..3 {
            aliased = simd_shuffle(aliased,b,REVERSE);
        }
        vector16!(aliased);
        let na: std::arch::aarch64::uint8x16_t = std::mem::transmute(a);
        let nb: std::arch::aarch64::uint8x16_t = std::mem::transmute(b);
        vector16!(std::arch::aarch64::vpmaxq_u8(na,nb));
        // Compare native TBL and both engines against independent array
        // semantics. Every possible index occurs in every output lane.
        for offset in 0..256u16 {
            let mut indices = [0u8;16];
            let mut expected = [0u8;16];
            for lane in 0..16 {
                let index = (offset as u8).wrapping_add(lane as u8 * 17);
                indices[lane] = index;
                expected[lane] = if index < 16 { bytes[index as usize] } else { 0 };
            }
            let index_vector = std::mem::transmute(indices);
            let actual: [u8;16] = std::mem::transmute(std::arch::aarch64::vqtbl1q_u8(na,index_vector));
            assert_eq!(actual,expected);
            result = mix(result,&actual);
            let signed_actual: [u8;16] = std::mem::transmute(std::arch::aarch64::vqtbl1q_s8(std::mem::transmute(na),index_vector));
            assert_eq!(signed_actual,expected);
        }
        let reverse = std::mem::transmute([15u8,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0]);
        let mut table_alias = na;
        let mut expected_alias = bytes;
        for _ in 0..5 {
            table_alias = std::arch::aarch64::vqtbl1q_u8(table_alias,reverse);
            expected_alias.reverse();
            let actual: [u8;16] = std::mem::transmute(table_alias);
            assert_eq!(actual,expected_alias);
            result = mix(result,&actual);
        }
        let mut index_alias = reverse;
        let mut expected_indices = [15u8,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0];
        for _ in 0..3 {
            index_alias = std::arch::aarch64::vqtbl1q_u8(na,index_alias);
            for index in &mut expected_indices {
                *index = if *index < 16 { bytes[*index as usize] } else { 0 };
            }
            let actual: [u8;16] = std::mem::transmute(index_alias);
            assert_eq!(actual,expected_indices);
            result = mix(result,&actual);
        }
        let mut both = reverse;
        for _ in 0..3 { both = std::arch::aarch64::vqtbl1q_u8(both,both); }
        vector16!(both);
        let wide: U16x8 = simd_splat(seed as u16);
        let shifts = U16x8([0,1,2,3,4,5,6,7]);
        vector16!(simd_shl(wide,shifts)); vector16!(simd_shr(wide,shifts));
        let signed_wide: I16x8 = std::mem::transmute(wide);
        let signed_shifts: I16x8 = std::mem::transmute(shifts);
        vector16!(simd_shr(signed_wide,signed_shifts));
        let narrow: U8x8 = simd_cast(wide);
        vector16!(simd_cast::<_,U16x8>(narrow));
        let signed_narrow: I8x8 = std::mem::transmute(narrow);
        vector16!(simd_as::<_,I16x8>(signed_narrow));
    }
    result
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
