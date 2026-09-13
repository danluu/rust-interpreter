//@ incremental
//@ compile-flags: -Copt-level=0 -Ccodegen-units=1 -Zstable-mono-cgu-partitioning

#![crate_type = "rlib"]

//~ MONO_ITEM fn first @@ stable_mono_merging-stable-mono-cgu-v1.1-0[External]
pub fn first(x: u64) -> u64 {
    twice(x)
}

//~ MONO_ITEM fn second @@ stable_mono_merging-stable-mono-cgu-v1.1-0[External]
pub fn second(x: u64) -> u64 {
    twice(x) + 1
}

//~ MONO_ITEM fn twice @@ stable_mono_merging-stable-mono-cgu-v1.1-0[Internal]
#[inline(always)]
pub fn twice(x: u64) -> u64 {
    x * 2
}
