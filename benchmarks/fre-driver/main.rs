fn main() {
    let escaped = fre::escape("[a+b]");
    if std::env::var_os("RUST_INTERP_BENCH_PROBE").is_some() {
        println!("{escaped}");
        return;
    }
    let iterations: usize = std::env::args().nth(1).map(|s| s.parse().unwrap()).unwrap_or(64);
    let regex = fre::PortableBuilder::new("needle").build().unwrap();
    let mut haystack = vec![b'x'; 65536];
    haystack[65530..].copy_from_slice(b"needle");
    let mut checksum = 0usize;
    for _ in 0..iterations {
        let matched = regex.find_value(std::hint::black_box(&haystack), fre::SearchLimits::default()).unwrap().unwrap();
        checksum += std::hint::black_box(matched.start());
    }
    println!("{escaped} {checksum}");
}
