fn main() {
    for value in std::env::args().skip(1) {
        println!("{}",value.parse::<u64>().unwrap().wrapping_add(7));
    }
}
