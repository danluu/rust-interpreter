// All callback addresses are materialized before the first indirect call.
// Lowering each callback then discovers a distinct helper. Callback processing
// order must not depend on a randomly seeded host hash table.
macro_rules! callback {
    ($outer:ident, $inner:ident, $shift:literal) => {
        #[inline(never)]
        fn $outer(value: u64) -> u64 {
            $inner(value).wrapping_add($shift)
        }
        #[inline(never)]
        fn $inner(value: u64) -> u64 {
            value.rotate_left($shift).wrapping_mul(2 * $shift + 1)
        }
    };
}
callback!(alpha, alpha_inner, 1);
callback!(beta, beta_inner, 3);
callback!(gamma, gamma_inner, 5);
callback!(delta, delta_inner, 7);
callback!(epsilon, epsilon_inner, 11);
callback!(zeta, zeta_inner, 13);
callback!(eta, eta_inner, 17);
callback!(theta, theta_inner, 19);

pub fn rust_interp_entry(seed: u64) -> u64 {
    let callbacks: [fn(u64) -> u64; 8] = [
        alpha, beta, gamma, delta, epsilon, zeta, eta, theta,
    ];
    let mut result = 0u64;
    for index in 0..8 {
        result = result.wrapping_add(callbacks[(index + (seed as usize & 7)) & 7](
            seed.wrapping_add(index as u64),
        ));
    }
    result
}

fn main() {
    for argument in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(argument.parse().unwrap()));
    }
}
