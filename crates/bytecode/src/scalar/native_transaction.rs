//! Bounded private store slots. Only the scoped experiment entry selects this.
use super::*;

#[derive(Clone,Copy)]
struct Site {id:Id,address:Id,size:u8,offset:usize}
pub(super) struct Layout {sites:Vec<Site>,scratch:usize,identities:Vec<(Id,u64)>}
impl Layout {
    pub fn new(plan:&Plan,bytes:&mut usize)->Result<Option<Self>,&'static str> {
        let mut sites=vec![];*bytes=(*bytes+15)&!15;
        for (id,n) in plan.nodes.iter().enumerate() {
            if !plan.live[id] {continue;}
            if let Value::Write{address,size,..}=n.value {
                if size==0 || size>16 || sites.len()>=16 {return Err("native_store_limit");}
                sites.push(Site{id,address,size,offset:*bytes});*bytes+=32;
            }
        }
        if sites.is_empty() {return Ok(None);}
        let scratch=*bytes;*bytes+=16;Ok(Some(Self{sites,scratch,identities:addresses(plan)?}))
    }
}

// Equality modulo 2^64 only; independently checked complete ranges establish
// dereferenceability. Never infer equality through a narrow cast or a phi.
#[cfg(test)]
fn address(plan:&Plan,mut id:Id)->(Id,u64) {
    let mut offset=0u64;
    for _ in 0..plan.nodes.len() {
        match &plan.nodes[id].value {
            Value::Cast{src,from:64,to:64,..}=>id=*src,
            Value::Pack(parts) if parts.len()==1 && parts[0].byte==0 && parts[0].size>=8=>id=parts[0].value,
            Value::Binary{a,b,op:Binary::Add,bits:64,overflow:false,..}=>{
                let pair=match (&plan.nodes[*a].value,&plan.nodes[*b].value) {
                    (_,Value::Constant(n))=>Some((*a,*n as u64)),
                    (Value::Constant(n),_)=>Some((*b,*n as u64)),_=>None,
                };
                if let Some((next,n))=pair {id=next;offset=offset.wrapping_add(n);} else {break;}
            },_=>break,
        }
    }
    (id,offset)
}
// SSA inputs precede these non-phi address aliases. Memoizing each identity
// bounds preparation to O(nodes), plus at most 16 prior stores per read.
fn addresses(plan:&Plan)->Result<Vec<(Id,u64)>,&'static str> {
    let mut ids:Vec<(Id,u64)>=Vec::with_capacity(plan.nodes.len());
    for (id,node) in plan.nodes.iter().enumerate() {
        let prior=match &node.value {
            Value::Cast{src,from:64,to:64,..}=>Some((*src,0)),
            Value::Pack(parts) if parts.len()==1 && parts[0].byte==0 && parts[0].size>=8=>Some((parts[0].value,0)),
            Value::Binary{a,b,op:Binary::Add,bits:64,overflow:false,..}=>match (&plan.nodes[*a].value,&plan.nodes[*b].value) {
                (_,Value::Constant(n))=>Some((*a,*n as u64)),(Value::Constant(n),_)=>Some((*b,*n as u64)),_=>None,
            },_=>None,
        };
        let identity=if let Some((src,offset))=prior {
            let (root,base)=*ids.get(src).ok_or("native_address_order")?;(root,base.wrapping_add(offset))
        } else {(id,0)};
        ids.push(identity);
    }
    Ok(ids)
}
#[derive(Clone,Copy)]
enum Relation {Disjoint,Contains(u8),Partial,Unknown}
fn relation(identities:&[(Id,u64)],site:Site,read:Id,size:u8)->Relation {
    let (a,x)=identities[site.address];let (b,y)=identities[read];
    if a!=b {return Relation::Unknown;}
    let delta=y.wrapping_sub(x);let reverse=x.wrapping_sub(y);
    if delta>=u64::from(site.size) && reverse>=u64::from(size) {return Relation::Disjoint;}
    if delta.checked_add(u64::from(size)).is_some_and(|end|end<=u64::from(site.size)) {
        Relation::Contains(delta as u8)
    } else {Relation::Partial}
}
impl Emitter<'_> {
    pub(super) fn transaction_initialize(&mut self) {
        if let Some(t)=&self.transaction {
            let offsets:Vec<_>=t.sites.iter().map(|s|s.offset).collect();
            for offset in offsets {self.store(31,31,offset);}
        }
    }
    pub(super) fn transaction_write(&mut self,id:Id,address:Id,value:Id,size:u8)->Result<(),&'static str> {
        if !self.call_frame {return Err("native_store_call_only");}
        let site=*self.transaction.as_ref().ok_or("native_store_disabled")?.sites.iter().find(|s|s.id==id).ok_or("native_store_slot")?;
        // x4 is the retained read-only prefix; x7/x8 exist only in the heap ABI.
        self.get(9,address,false);self.imm(10,crate::heap::TAG as u64);self.cmp(9,10);
        if self.heap {
            self.three(0xcb000000,11,9,10);self.csel(9,9,11,3);self.csel(12,2,7,3);
            self.load(13,31,self.stack_bytes+24);self.csel(13,13,8,3);self.csel(14,4,31,3);
        } else {self.fail(2);self.mov(12,2);self.load(13,31,self.stack_bytes+24);self.mov(14,4);}
        self.cmp(9,31);self.fail(0);self.cmp(9,13);self.fail(8);
        self.three(0xcb000000,13,13,9);self.imm(10,u64::from(size));self.cmp(13,10);self.fail(3);
        self.cmp(9,14);self.fail(3);self.three(0x8b000000,11,12,9);
        self.store(11,31,site.offset);self.get(12,address,false);self.store(12,31,site.offset+8);
        self.get(9,value,false);self.get(10,value,true);self.store(9,31,site.offset+16);self.store(10,31,site.offset+24);
        Ok(())
    }
    fn transaction_value(&mut self,site:Site,byte:u8,size:u8) {
        self.load(9,31,site.offset+16);self.load(10,31,site.offset+24);
        let shift=byte*8;
        if shift>=64 {self.lsr(9,10,shift-64);self.mov(10,31);} else if shift!=0 {
            self.emit(0x93c00000|(9<<16)|((shift as u32)<<10)|(10<<5)|9);self.lsr(10,10,shift);
        }
        if size<=8 {self.mask(9,size*8);self.mov(10,31);} else {self.mask(10,(size-8)*8);}
    }
    pub(super) fn transaction_read(&mut self,id:Id,source:Id,size:u8)->Result<(),&'static str> {
        let Some(t)=&self.transaction else {return self.read_external(source,size);};
        let sites:Vec<_>=t.sites.iter().copied().filter(|s|s.id<id && !matches!(relation(&t.identities,*s,source,size),Relation::Disjoint)).collect();let scratch=t.scratch;
        if sites.is_empty() {return self.read_external(source,size);}
        let pc=self.plan.nodes[id].pc.ok_or("native_read_pc")?;
        // A preceding store in this same basic block must have executed. Its
        // checked containing range proves the read, including every byte.
        let covering=sites.iter().enumerate().rev().find_map(|(i,s)| {
            let p=self.plan.nodes[s.id].pc?;
            if p<pc && self.plan.at[p]==self.plan.at[pc] {
                if let Relation::Contains(byte)=relation(&t.identities,*s,source,size) {return Some((i,byte));}
            }
            None
        });
        let start=if let Some((i,byte))=covering {self.transaction_value(sites[i],byte,size);i+1}
            else {self.read_external(source,size)?;0};
        if start==sites.len() {return Ok(());}
        self.store(9,31,scratch);self.store(10,31,scratch+8);
        for site in sites.into_iter().skip(start) {
            let relation=relation(&self.transaction.as_ref().unwrap().identities,site,source,size);
            if matches!(relation,Relation::Disjoint) {continue;}
            self.load(11,31,site.offset);self.cmp(11,31);let inactive=self.words.len();self.emit(0x54000000);
            let mut done=None;
            match relation {
                Relation::Contains(byte)=>{self.transaction_value(site,byte,size);self.store(9,31,scratch);self.store(10,31,scratch+8);},
                Relation::Partial=>{self.cmp(31,31);self.fail(0);},
                Relation::Unknown=>{
                    self.get(11,source,false);self.load(12,31,site.offset+8);
                    let unequal=if site.size>=size {
                        self.cmp(11,12);let at=self.words.len();self.emit(0x54000001);
                        self.transaction_value(site,0,size);self.store(9,31,scratch);self.store(10,31,scratch+8);
                        done=Some(self.words.len());self.emit(0x14000000);Some(at)
                    } else {None};
                    if let Some(at)=unequal {self.patch(at,self.words.len(),true)?;}
                    // Complete checked ranges cannot wrap. Modular differences
                    // detect either start falling inside the other range.
                    self.three(0xcb000000,13,11,12);self.imm(14,u64::from(site.size));self.cmp(13,14);self.fail(3);
                    self.three(0xcb000000,13,12,11);self.imm(14,u64::from(size));self.cmp(13,14);self.fail(3);
                },Relation::Disjoint=>unreachable!(),
            }
            let end=self.words.len();self.patch(inactive,end,true)?;if let Some(at)=done {self.patch(at,end,false)?;}
        }
        self.load(9,31,scratch);self.load(10,31,scratch+8);Ok(())
    }
    pub(super) fn transaction_commit(&mut self)->Result<(),&'static str> {
        let Some(t)=&self.transaction else {return Ok(());};let sites=t.sites.clone();
        // No guard, guest failure or branch to the private-failure tail may
        // follow the first publication. The Call bridge likewise cannot fail
        // after this entry returns success and commits its result afterward.
        for site in sites {
            self.load(11,31,site.offset);self.cmp(11,31);let inactive=self.words.len();self.emit(0x54000000);
            self.load(9,31,site.offset+16);self.load(10,31,site.offset+24);
            match site.size {
                1|2|4|8=>{let opcode=match site.size {1=>0x39000000,2=>0x79000000,4=>0xb9000000,_=>0xf9000000};self.emit(opcode|(11<<5)|9);},
                16=>{self.store(9,11,0);self.store(10,11,8);},
                _=>for byte in 0..site.size {self.lsr(12,if byte<8 {9} else {10},(byte%8)*8);self.emit(0x39000000|((byte as u32)<<10)|(11<<5)|12);},
            }
            self.patch(inactive,self.words.len(),true)?;
        }
        Ok(())
    }
}

#[test]
fn native_private_low_address_relations_preserve_wrap_and_narrowing() {
    let values=vec![Value::Input(0),Value::Constant(u64::MAX as u128),
        Value::Binary{a:0,b:1,op:Binary::Add,bits:64,signed:false,overflow:false},Value::Constant(2),
        Value::Binary{a:2,b:3,op:Binary::Add,bits:64,signed:false,overflow:false},
        Value::Cast{src:4,from:64,to:32,signed:false},Value::Cast{src:4,from:64,to:64,signed:true}];
    let p=Plan{nodes:values.into_iter().map(|value|Node{value,width:8,pc:None}).collect(),
        blocks:vec![],at:vec![],computations:vec![],effects:vec![],live:vec![],reachable:vec![],
        maximum_steps:0,success_steps:None,result_size:0,work:0};
    let identities=addresses(&p).unwrap();
    for (id,identity) in identities.iter().enumerate() {assert_eq!(*identity,address(&p,id));}
    let site=Site{id:0,address:0,size:16,offset:0};
    assert!(matches!(relation(&identities,site,4,8),Relation::Contains(1)));
    assert!(matches!(relation(&identities,site,6,8),Relation::Contains(1)));
    assert!(matches!(relation(&identities,site,5,8),Relation::Unknown));
    assert!(matches!(relation(&identities,site,2,1),Relation::Disjoint));
    assert!(matches!(relation(&identities,site,2,2),Relation::Partial));
    for base in [0u64,1,2,u64::MAX-1,u64::MAX] {
        assert_eq!(base.wrapping_add(u64::MAX).wrapping_add(2),base.wrapping_add(address(&p,6).1));
    }
}
