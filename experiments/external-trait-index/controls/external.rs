#![feature(trait_alias)]
#![allow(non_upper_case_globals)]

pub struct Foreign(pub u32);
pub trait Unused {}
impl Unused for Foreign {}

pub mod left {
    pub trait Select {
        type Item;
        const Item: u32;
        fn selected(&self) -> u32;
        fn absent_from_right(&self) -> u32 { 7 }
    }
    impl Select for super::Foreign {
        type Item = u32;
        const Item: u32 = 31;
        fn selected(&self) -> u32 { self.0 + 11 }
    }
}

pub mod right {
    pub trait Select { fn selected(&self) -> u32; }
    impl Select for super::Foreign {
        fn selected(&self) -> u32 { self.0 + 22 }
    }
}

pub trait Alias = left::Select;
pub mod reexport {
    pub use crate::left::Select as Renamed;
    pub mod nested { pub use super::Renamed as Selected; }
}

#[macro_export]
macro_rules! make_local_trait {
    () => {
        trait LocalMethod { fn locally_defined(&self) -> u32; }
        impl LocalMethod for external::Foreign {
            fn locally_defined(&self) -> u32 { self.0 + 5 }
        }
    };
}
