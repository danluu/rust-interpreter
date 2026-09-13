#![no_std]

include!(concat!(env!("OUT_DIR"), "/generated.rs"));
const MACRO_VALUE: u64 = host_mir_macros::offset!();

pub fn value(x: u64) -> u64 {
    host_mir_shared::shared_value(x) + HOST_VALUE + MACRO_VALUE
}

#[cfg(test)]
mod tests {
    #[test]
    fn checks_host_and_guest_dependencies() {
        assert_eq!(super::HOST_VALUE, 8);
        assert_eq!(super::MACRO_VALUE, 9);
        assert_eq!(super::value(2), 26);
    }

    #[test]
    fn checks_another_input() {
        assert_eq!(super::value(3), 27);
    }
}
