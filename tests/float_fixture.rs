fn bits64(value: f64) -> u64 {
    if value.is_nan() { f64::NAN.to_bits() } else { value.to_bits() }
}
fn bits32(value: f32) -> u64 {
    if value.is_nan() { f32::NAN.to_bits() as u64 } else { value.to_bits() as u64 }
}
fn fold(hash: &mut u64, value: u64) { *hash = hash.rotate_left(9).wrapping_add(value); }

trait Compute { fn compute(&self, x: f64) -> f64; }
struct Scale(f64);
impl Compute for Scale { fn compute(&self, x: f64) -> f64 { x * self.0 } }
#[inline(never)]
fn mixed(a: f64, b: f32) -> f64 { a + b as f64 }

pub fn rust_interp_entry(seed: u64) -> u64 {
    let x = f64::from_bits(std::hint::black_box(seed));
    let y = f64::from_bits(seed.rotate_left(19) ^ 0x0123_4567_89ab_cdef);
    let mut hash = seed;
    assert_eq!(x.to_bits(), seed);
    assert_eq!(f32::from_bits(seed as u32).to_bits(), seed as u32);
    // A value just above an f32 halfway point that would double-round if
    // conversion first passed through f64.
    let above_half = std::hint::black_box((1u128 << 100) + (1u128 << 76) + 1);
    assert_eq!((above_half as f32).to_bits(), 0x7180_0001);
    assert_eq!((-(above_half as i128) as f32).to_bits(), 0xf180_0001);
    let signed = ((seed as u128) << 64 | seed.rotate_left(7) as u128) as i128;
    let unsigned = signed as u128;
    fold(&mut hash, bits32(signed as f32));
    fold(&mut hash, bits64(signed as f64));
    fold(&mut hash, bits32(unsigned as f32));
    fold(&mut hash, bits64(unsigned as f64));

    let exponent = (seed % 17) as i32 - 8;
    for a in [x, 0.0, -0.0, 0.5, -0.5, 1.5, 2.5, -3.5, f64::MIN_POSITIVE,
              f64::from_bits(1), f64::MAX, -f64::MAX, f64::INFINITY, f64::NEG_INFINITY,
              f64::from_bits(0x7ff0_0000_0000_0001)] {
        for b in [y, 0.0, -0.0, 1.0, -1.0] {
            for value in [a+b, a-b, a*b, a/b, a%b] { fold(&mut hash, bits64(value)); }
            fold(&mut hash, (a==b) as u64 | ((a!=b) as u64)<<1 | ((a<b) as u64)<<2
                | ((a<=b) as u64)<<3 | ((a>b) as u64)<<4 | ((a>=b) as u64)<<5);
            // min/max permit either zero sign, and arithmetic NaN payloads
            // are unspecified. Normalize only those unspecified results.
            for value in [a.min(b), a.max(b)] {
                fold(&mut hash, bits64(if value == 0.0 { 0.0 } else { value }));
            }
            fold(&mut hash, a.copysign(b).to_bits());
        }
        for value in [-a, a.abs(), a.round(), a.round_ties_even(), a.ceil(), a.floor(),
                      a.trunc(), a.sqrt(), a.log10(), a.powi(exponent)] {
            fold(&mut hash, bits64(value));
        }
        fold(&mut hash, bits32(a as f32));
        macro_rules! cast_integer {
            ($($t:ty),*) => {$( {
                let v = a as $t;
                let raw = v as u128;
                fold(&mut hash, raw as u64 ^ (raw >> 64) as u64);
                fold(&mut hash, bits32(v as f32));
                fold(&mut hash, bits64(v as f64));
            } )*};
        }
        cast_integer!(u8,i8,u16,i16,u32,i32,u64,i64,u128,i128,usize,isize);
    }
    let z = f32::from_bits(seed as u32);
    for a in [z, 0.0, -0.0, 0.5, -0.5, 1.5, 2.5, f32::MIN_POSITIVE,
              f32::from_bits(1), f32::MAX, -f32::MAX, f32::INFINITY, f32::NEG_INFINITY,
              f32::from_bits(0x7f80_0001)] {
        for b in [y as f32, 0.0, -0.0, 1.0, -1.0] {
            for value in [a+b, a-b, a*b, a/b, a%b] { fold(&mut hash, bits32(value)); }
            fold(&mut hash, (a==b) as u64 | ((a!=b) as u64)<<1 | ((a<b) as u64)<<2
                | ((a<=b) as u64)<<3 | ((a>b) as u64)<<4 | ((a>=b) as u64)<<5);
            for value in [a.min(b), a.max(b)] {
                fold(&mut hash, bits32(if value == 0.0 { 0.0 } else { value }));
            }
            fold(&mut hash, a.copysign(b).to_bits() as u64);
        }
        for value in [-a, a.abs(), a.round(), a.round_ties_even(), a.ceil(), a.floor(),
                      a.trunc(), a.sqrt(), a.log10(), a.powi(exponent)] {
            fold(&mut hash, bits32(value));
        }
        fold(&mut hash, bits64(a as f64));
        macro_rules! cast_integer {
            ($($t:ty),*) => {$( {
                let v = a as $t;
                let raw = v as u128;
                fold(&mut hash, raw as u64 ^ (raw >> 64) as u64);
            } )*};
        }
        cast_integer!(u8,i8,u16,i16,u32,i32,u64,i64,u128,i128,usize,isize);
    }
    let compute: Box<dyn Compute> = Box::new(Scale(0.25));
    let values: Vec<_> = [x, y, seed as f64].into_iter().map(|v| compute.compute(v)).collect();
    for value in values { fold(&mut hash, bits64(value)); }
    let callback: fn(f64, f32) -> f64 = std::hint::black_box(mixed);
    fold(&mut hash, bits64(callback(x, z)));
    hash
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
