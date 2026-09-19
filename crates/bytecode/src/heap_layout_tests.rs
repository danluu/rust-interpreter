use super::*;

struct Pair { candidate: Heap, reference: reference::Heap, known: BTreeMap<usize, (usize, usize)> }
impl Pair {
    fn new(prefix: &[u8], limit: usize) -> Self {
        Self { candidate: Heap::with_statics(prefix,limit), reference: reference::Heap::with_statics(prefix,limit), known:BTreeMap::new() }
    }
    fn same(&self) {
        assert_eq!(self.candidate.bytes,self.reference.bytes);
        assert_eq!(self.candidate.allocations.len(),self.known.len());
        for (&pointer,&layout) in &self.known {
            assert_eq!(self.candidate.owned_layout(pointer-TAG),Some(layout));
            assert_eq!(self.reference.owned_layout(pointer-TAG),Some(layout));
        }
    }
    fn allocate(&mut self,size:usize,align:usize,budget:usize,zeroed:bool) -> Result<usize,String> {
        let a=self.candidate.allocate(size,align,budget,zeroed);
        let b=self.reference.allocate(size,align,budget,zeroed);assert_eq!(a,b);
        if let Ok(pointer)=a {if pointer!=0 {assert!(self.known.insert(pointer,(size,align)).is_none());}}
        self.same();a
    }
    fn deallocate(&mut self,pointer:usize,size:usize,align:usize) -> Result<(),String> {
        let a=self.candidate.deallocate(pointer,size,align);let b=self.reference.deallocate(pointer,size,align);
        assert_eq!(a,b);if a.is_ok(){assert!(self.known.remove(&pointer).is_some());}
        self.same();a
    }
    fn reallocate(&mut self,pointer:usize,old:usize,align:usize,new:usize,budget:usize) -> Result<usize,String> {
        let a=self.candidate.reallocate(pointer,old,align,new,budget);
        let b=self.reference.reallocate(pointer,old,align,new,budget);assert_eq!(a,b);
        if let Ok(next)=a {if next!=0 {assert!(self.known.remove(&pointer).is_some());assert!(self.known.insert(next,(new,align)).is_none());}}
        self.same();a
    }
    fn write(&mut self,pointer:usize,value:u8) {
        let size=self.known[&pointer].0;let start=pointer-TAG;
        self.candidate.bytes[start..start+size].fill(value);self.reference.bytes[start..start+size].fill(value);self.same();
    }
}

#[test]
fn first_fit_alignment_and_coalescing_ignore_hash_iteration_order() {
    for _ in 0..16 { // Distinct standard HashMap seeds must preserve every address.
        let mut p=Pair::new(&[0x39;31],64);let mut pointers=vec![];
        for &(size,align) in &[(9,8),(17,32),(3,1),(32,16),(11,8),(1,64)] {
            let a=p.allocate(size,align,512,false).unwrap();p.write(a,0xa5);pointers.push((a,size,align));
        }
        for &i in &[1,3,0,4] {let (a,size,align)=pointers[i];p.deallocate(a,size,align).unwrap();}
        for &(size,align) in &[(8,8),(4,4),(24,8),(7,1),(16,16)] {let a=p.allocate(size,align,512,true).unwrap();assert_ne!(a,0);}
    }
}

#[test]
fn invalid_layouts_and_failed_growth_preserve_original_allocation() {
    let mut p=Pair::new(&[0x52;32],2);let a=p.allocate(16,16,128,false).unwrap();
    let b=p.allocate(16,16,128,false).unwrap();p.write(a,0xcc);
    assert_eq!(p.allocate(1,1,128,false).unwrap(),0);
    for &(size,align) in &[(0,1),(16,0),(16,3),(8,16),(16,8)] {
        assert!(p.deallocate(a,size,align).is_err());
    }
    for pointer in [0,TAG,TAG+16,a+1,usize::MAX] {assert!(p.deallocate(pointer,16,16).is_err());}
    assert_eq!(p.reallocate(a,16,16,64,128).unwrap(),0);
    assert!(p.reallocate(a,15,16,16,128).is_err());
    assert!(p.reallocate(a,16,16,0,128).is_err());
    p.deallocate(b,16,16).unwrap();let next=p.reallocate(a,16,16,48,128).unwrap();assert_eq!(next,a);
    p.deallocate(a,48,16).unwrap();assert_eq!(p.candidate.bytes,vec![0x52;32]);
}

#[test]
fn grow_shrink_move_zeroing_and_static_prefix_match_reference() {
    let mut p=Pair::new(&[0x73;19],64);
    let a=p.allocate(24,8,512,false).unwrap();let b=p.allocate(32,16,512,false).unwrap();p.write(a,0xdb);
    let moved=p.reallocate(a,24,8,80,512).unwrap();assert_ne!(moved,a);
    assert_eq!(&p.candidate.bytes[moved-TAG..moved-TAG+24],&[0xdb;24]);
    p.reallocate(moved,80,8,8,512).unwrap();p.deallocate(b,32,16).unwrap();
    let fresh=p.allocate(24,8,512,true).unwrap();assert_eq!(&p.candidate.bytes[fresh-TAG..fresh-TAG+24],&[0;24]);
    p.deallocate(fresh,24,8).unwrap();p.deallocate(moved,8,8).unwrap();assert_eq!(p.candidate.bytes,vec![0x73;19]);
}

#[test]
fn seeded_allocator_traces_match_all_addresses_bytes_errors_and_limits() {
    fn next(state:&mut u64)->u64 { *state^=*state<<13;*state^=*state>>7;*state^=*state<<17;*state }
    for seed in 1..=64 {
        let mut state=seed;let mut p=Pair::new(&vec![0x47;(seed%33) as usize],(seed%31+1) as usize);
        for _ in 0..2000 {
            let choice=next(&mut state)%8;let size=(next(&mut state)%129) as usize;
            let align=1usize<<((next(&mut state)%7) as usize);let budget=(next(&mut state)%4097) as usize;
            let selected=if p.known.is_empty(){None}else{
                p.known.iter().nth(next(&mut state) as usize%p.known.len()).map(|(&a,&(n,k))|(a,n,k))};
            match (choice,selected) {
                (0..=2,_)|(_,None)=>{let _=p.allocate(size,align,budget,choice==0);},
                (3,Some((a,n,k)))=>{let _=p.deallocate(a,n,k);},
                (4|5,Some((a,n,k)))=>{let _=p.reallocate(a,n,k,size,budget);},
                (6,Some((a,_,_)))=>p.write(a,next(&mut state) as u8),
                (_,Some((a,n,k)))=>{let _=p.deallocate(a+1,n,k);},
            }
        }
        let live:Vec<_>=p.known.iter().map(|(&a,&(n,k))|(a,n,k)).collect();
        for (a,n,k) in live {p.deallocate(a,n,k).unwrap();}
    }
}
