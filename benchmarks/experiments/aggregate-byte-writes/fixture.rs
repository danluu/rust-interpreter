//! Exercise private aggregate lifetimes, partial writes, enum layouts and ABIs.
#[derive(Clone,Copy)]
#[repr(C,align(32))]
struct Block { tag:u8, words:[u64;7] }
#[derive(Clone,Copy)]
enum Choice { Small(u8), Large(Block) }

#[track_caller]
#[inline(never)]
fn make(seed:u64)->Block {
    let line=std::panic::Location::caller().line() as u64;
    Block{tag:seed as u8,words:[seed.wrapping_add(line);7]}
}
#[inline(never)]
fn read(value:Block,index:usize)->u64 {
    value.words[index%7].rotate_left(value.tag as u32)+value.tag as u64
}
#[inline(never)]
fn change(value:&mut Block,seed:u64) { value.words[seed as usize%7]^=seed;value.tag=value.tag.wrapping_add(3); }
#[inline(never)]
fn closure_call<F:FnOnce(u64,u64)->u64>(f:F,a:u64,b:u64)->u64 { f(a,b) }

pub fn rust_interp_entry(seed:u64)->u64 {
    let mut total=seed;
    let mut held=make(seed.rotate_right(11));
    let retained=&mut held;
    for i in 0..9 {
        let first=make(seed.wrapping_add(i));
        total^=read(first,i as usize);
        let second=make(total);
        total=total.wrapping_add(read(second,seed as usize));
        let choice=if i%2==0 {Choice::Large(make(total))} else {Choice::Small(i as u8)};
        let v=match choice {Choice::Large(b)=>read(b,i as usize),Choice::Small(b)=>b as u64};
        total^=v;
        // Address-exposed storage and projected stores must remain dedicated.
        change(retained,total);
        let niche=std::num::NonZeroU64::new(total);
        total=closure_call(|a,b|a.wrapping_add(b),total,niche.map_or(17,|n|n.get()));
    }
    total^read(held,seed as usize)
}
fn main() {
    for arg in std::env::args().skip(1) { println!("{}",rust_interp_entry(arg.parse().unwrap())); }
}
