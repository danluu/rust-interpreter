//! Explicit literal parameters. Opaque to optimization, materialized through a ledger.
use super::*;
use serde::{Serialize,Serializer,ser::SerializeSeq};
pub(super) type Site=(usize,usize,cross_program_templates::Kind);
pub(super) fn append(out:&mut Vec<Site>,sites:Vec<Site>,base:usize) {
    out.extend(sites.into_iter().map(|(word,words,kind)|(word+base,words,kind)));
}

pub(super) fn selected_with_fills(f:&Function,fills:&BTreeMap<usize,LocalFill>)->BTreeSet<usize> {
    let mut pcs=f.code.iter().enumerate().filter_map(|(pc,op)|match op {
        Op::Imm{value,..} if *value as u64>=65_536=>Some(pc),_=>None,
    }).collect::<BTreeSet<_>>();
    // The fused fill consumes literal byte/length values during emission.
    for &pc in fills.keys() {pcs.remove(&(pc-2));pcs.remove(&(pc-1));}
    pcs
}
pub(super) fn selected(f:&Function)->BTreeSet<usize> {selected_with_fills(f,&local_fills(f))}
pub(super) fn shape(value:u128)->u128 {
    let mut shape=0;
    for part in [1,2,3,5,6,7] {if (value>>(part*16))&0xffff!=0 {shape|=1u128<<(part*16);}}
    shape
}

#[derive(Serialize)]
pub(super) struct FunctionInput<'a> {
    name:&'a str,frame_size:usize,frame_align:usize,registers:usize,
    args:&'a [crate::Slot],result:&'a crate::Slot,code:CodeInput<'a>,
}
impl<'a> FunctionInput<'a> {
    pub fn new(f:&'a Function,selected:&'a BTreeSet<usize>)->Self {
        Self{name:&f.name,frame_size:f.frame_size,frame_align:f.frame_align,registers:f.registers,
            args:&f.args,result:&f.result,code:CodeInput{f,selected}}
    }
}
struct CodeInput<'a> {f:&'a Function,selected:&'a BTreeSet<usize>}
impl Serialize for CodeInput<'_> {
    fn serialize<S:Serializer>(&self,serializer:S)->Result<S::Ok,S::Error> {
        let mut seq=serializer.serialize_seq(Some(self.f.code.len()))?;
        for (pc,op) in self.f.code.iter().enumerate() {
            if let Op::Imm{dst,value}=op {
                if self.selected.contains(&pc) {
                    seq.serialize_element(&Op::Imm{dst:*dst,value:shape(*value)})?;continue;
                }
            }
            seq.serialize_element(op)?;
        }
        seq.end()
    }
}

impl Assembler<'_> {
    pub(super) fn literal(&mut self,rd:u32,pc:usize,value:u128,high:bool) {
        let value=if high {(value>>64) as u64} else {value as u64};
        let word=self.words.len();self.imm(rd,value);
        let site=(word,self.words.len()-word,cross_program_templates::Kind::Literal{pc,high,rd});
        // Keep the typed emission manifest independently of the relocation
        // list. Capture rejects a lost/reassociated record before retention.
        self.literal_sites.push(site);
        self.model_relocations.push(cross_program_templates::Relocation{word,words:self.words.len()-word,value,
            kind:site.2});
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn function(code:Vec<Op>)->Function {Function{name:"literal".into(),frame_size:131072,frame_align:8,
        registers:5,args:vec![],result:crate::Slot{offset:0,size:0},code}}
    #[test]
    fn empty_selection_serialization_equals_original_function() {
        let f=function(vec![Op::Imm{dst:0,value:7},Op::Return]);
        assert_eq!(bincode::serialize(&FunctionInput::new(&f,&BTreeSet::new())).unwrap(),bincode::serialize(&f).unwrap());
    }
    #[test]
    fn selection_excludes_fused_fill_values_and_retains_width() {
        let f=function(vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:0x123456},
            Op::Imm{dst:2,value:8},Op::FillBytes{address:0,value:1,size:2},Op::Imm{dst:3,value:0x345678},Op::Return]);
        assert_eq!(selected(&f),BTreeSet::from([4]));
        for value in [0,1,65535,65536,0x123456789abcdef0,u64::MAX] {
            let mut a=Assembler::default();let mut b=Assembler::default();a.imm(9,value);b.imm(9,shape(value as u128) as u64);
            assert_eq!(a.words.len(),b.words.len());
        }
    }
    #[test]
    fn selected_literals_cannot_supply_call_slot_or_range_hints() {
        let f=function(vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:65536},
            Op::Binary{dst:2,overflow:3,op:Binary::Add,a:0,b:1,bits:64,signed:false},
            Op::Call{function:1,args:vec![2],destination:0},Op::Return]);
        let mut leaf=function(vec![Op::Return]);leaf.args=vec![crate::Slot{offset:0,size:8}];
        let p=Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions:vec![f,leaf],
            data:vec![],statics:vec![],thread_locals:vec![]};
        let f=&p.functions[0];assert!(call_slots::collect(f,&p).contains_key(&3));
        assert!(call_slots::collect_with_literals(f,&p,&selected(f)).is_empty());
        let mut f=function(vec![Op::Imm{dst:1,value:65536},Op::Imm{dst:2,value:65544},
            Op::Binary{dst:1,overflow:3,op:Binary::Sub,a:2,b:1,bits:64,signed:false},
            Op::Binary{dst:2,overflow:3,op:Binary::Add,a:0,b:1,bits:64,signed:false}]);
        f.code.extend((0..8).map(|_|Op::Load{dst:4,address:2,size:8}));
        assert!(range_groups::runtime_plan(&f,0,f.code.len(),&mut 4_000_000).is_some());
        assert!(range_groups::runtime_plan_with_literals(&f,0,f.code.len(),&mut 4_000_000,&selected(&f)).is_none());
    }
}
