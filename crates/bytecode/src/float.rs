//! Scalar floating-point semantics for our VM. Values remain raw guest bits.
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub enum FloatBinary {
    Add,
    Sub,
    Mul,
    Div,
    Rem,
    Eq,
    Ne,
    Lt,
    Le,
    Gt,
    Ge,
    MinNumber,
    MaxNumber,
    PowI,
    CopySign,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub enum FloatUnary {
    Neg,
    Abs,
    Round,
    RoundTiesEven,
    Ceil,
    Floor,
    Trunc,
    Sqrt,
    Log10,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub enum FloatConversion {
    IntToFloat { signed: bool },
    FloatToInt { signed: bool },
    FloatToFloat,
}

pub(crate) fn width(bits: u8) -> Result<(), String> {
    if matches!(bits, 32 | 64) {
        Ok(())
    } else {
        Err("invalid floating-point width".into())
    }
}

pub(crate) fn conversion_widths(kind: FloatConversion, from: u8, to: u8) -> Result<(), String> {
    let int_width = |bits| {
        if matches!(bits, 8 | 16 | 32 | 64 | 128) {
            Ok(())
        } else {
            Err("invalid integer conversion width".to_string())
        }
    };
    match kind {
        FloatConversion::IntToFloat { .. } => {
            int_width(from)?;
            width(to)
        }
        FloatConversion::FloatToInt { .. } => {
            width(from)?;
            int_width(to)
        }
        FloatConversion::FloatToFloat => {
            width(from)?;
            width(to)
        }
    }
}

pub(crate) fn binary(op: FloatBinary, a: u128, b: u128, bits: u8) -> Result<u128, String> {
    width(bits)?;
    if matches!(op, FloatBinary::CopySign) {
        let sign = 1u128 << (bits - 1);
        return Ok(((a & !sign) | (b & sign)) & super::mask(bits));
    }
    macro_rules! calculate {
        ($ty:ty, $raw:ty) => {{
            let x = <$ty>::from_bits(a as $raw);
            let y = <$ty>::from_bits(b as $raw);
            let value = match op {
                FloatBinary::Eq => return Ok((x == y) as u128),
                FloatBinary::Ne => return Ok((x != y) as u128),
                FloatBinary::Lt => return Ok((x < y) as u128),
                FloatBinary::Le => return Ok((x <= y) as u128),
                FloatBinary::Gt => return Ok((x > y) as u128),
                FloatBinary::Ge => return Ok((x >= y) as u128),
                FloatBinary::Add => x + y,
                FloatBinary::Sub => x - y,
                FloatBinary::Mul => x * y,
                FloatBinary::Div => x / y,
                FloatBinary::Rem => x % y,
                FloatBinary::MinNumber => x.min(y),
                FloatBinary::MaxNumber => x.max(y),
                FloatBinary::PowI => x.powi(b as i32),
                FloatBinary::CopySign => unreachable!(),
            };
            value.to_bits() as u128
        }};
    }
    Ok(if bits == 32 {
        calculate!(f32, u32)
    } else {
        calculate!(f64, u64)
    })
}

pub(crate) fn unary(op: FloatUnary, raw: u128, bits: u8) -> Result<u128, String> {
    width(bits)?;
    let sign = 1u128 << (bits - 1);
    match op {
        FloatUnary::Neg => return Ok((raw ^ sign) & super::mask(bits)),
        FloatUnary::Abs => return Ok(raw & (sign - 1)),
        _ => {}
    }
    macro_rules! calculate {
        ($ty:ty, $raw:ty) => {{
            let x = <$ty>::from_bits(raw as $raw);
            let value = match op {
                FloatUnary::Round => x.round(),
                FloatUnary::RoundTiesEven => x.round_ties_even(),
                FloatUnary::Ceil => x.ceil(),
                FloatUnary::Floor => x.floor(),
                FloatUnary::Trunc => x.trunc(),
                FloatUnary::Sqrt => x.sqrt(),
                FloatUnary::Log10 => x.log10(),
                FloatUnary::Neg | FloatUnary::Abs => unreachable!(),
            };
            value.to_bits() as u128
        }};
    }
    Ok(if bits == 32 {
        calculate!(f32, u32)
    } else {
        calculate!(f64, u64)
    })
}

pub(crate) fn convert(kind: FloatConversion, raw: u128, from: u8, to: u8) -> Result<u128, String> {
    conversion_widths(kind, from, to)?;
    Ok(match kind {
        FloatConversion::IntToFloat { signed } => {
            // Convert directly from the integer width. Going through f64
            // first would introduce double rounding for i128/u128 -> f32.
            let raw = raw & super::mask(from);
            if signed {
                let x = super::signed(raw, from);
                if to == 32 {
                    (x as f32).to_bits() as u128
                } else {
                    (x as f64).to_bits() as u128
                }
            } else if to == 32 {
                (raw as f32).to_bits() as u128
            } else {
                (raw as f64).to_bits() as u128
            }
        }
        FloatConversion::FloatToInt { signed } => {
            // f32 is represented exactly by f64. Rust's host casts perform
            // truncation and NaN/overflow saturation; clamp to the guest width.
            let x = if from == 32 {
                f32::from_bits(raw as u32) as f64
            } else {
                f64::from_bits(raw as u64)
            };
            if signed {
                let (low, high) = if to == 128 {
                    (i128::MIN, i128::MAX)
                } else {
                    (-(1i128 << (to - 1)), (1i128 << (to - 1)) - 1)
                };
                (x as i128).clamp(low, high) as u128 & super::mask(to)
            } else {
                (x as u128).min(super::mask(to))
            }
        }
        FloatConversion::FloatToFloat => {
            if from == to {
                raw & super::mask(to)
            } else if from == 32 {
                (f32::from_bits(raw as u32) as f64).to_bits() as u128
            } else {
                (f64::from_bits(raw as u64) as f32).to_bits() as u128
            }
        }
    })
}
