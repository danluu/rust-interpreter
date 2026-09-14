//! Guard and commit phases for the experimental direct-effect entry.
use super::*;
#[derive(Clone,Copy)]
struct Site {id:Id,size:u8,offset:usize}
pub(super) struct Layout {pub needed:Vec<bool>,pub saved:Vec<Option<usize>>,sites:Vec<Site>}
impl Layout {
    pub fn new(plan:&Plan,slots:&[Option<usize>],bytes:&mut usize)->Result<Self,&'static str> {
        let guard=super::super::path_entry::guard_slice(plan)?;
        let mut saved=vec![None;plan.nodes.len()];let mut sites=vec![];
        for (id,node) in plan.nodes.iter().enumerate() {
            if !plan.live[id] {continue;}
            if let Value::Write{size,..}=node.value {
                if size==0 || size>16 || sites.len()>=16 {return Err("native_path_store_limit");}
                sites.push(Site{id,size,offset:*bytes});*bytes+=8;
            } else if guard.needed[id] && !matches!(node.value,Value::Constant(_)|Value::Input(_)|Value::Base(_)) {
                saved[id]=Some(if let Some(offset)=slots[id] {offset} else {let offset=*bytes;*bytes+=if node.width>8 {16} else {8};offset});
            }
        }
        Ok(Self{needed:guard.needed,saved,sites})
    }
}
impl Emitter<'_> {
    pub(super) fn path_initialize(&mut self) {
        if let Some(path)=&self.path {let offsets:Vec<_>=path.sites.iter().map(|s|s.offset).collect();for offset in offsets {self.store(31,31,offset);}}
    }
    pub(super) fn path_node_needed(&self,id:Id)->bool {
        self.path.as_ref().is_none_or(|p|if self.path_guard {p.needed[id]} else {p.saved[id].is_none()})
    }
    fn path_address(&mut self,address:Id,size:u8,write:bool,check:bool)->Result<(),&'static str> {
        if !self.call_frame || size==0 || size>16 {return Err("native_path_address_shape");}
        self.get(9,address,false);self.imm(10,crate::heap::TAG as u64);self.cmp(9,10);
        if self.heap {
            self.three(0xcb000000,11,9,10);self.csel(9,9,11,3);self.csel(12,2,7,3);
            if check {self.load(13,31,self.stack_bytes+24);self.csel(13,13,8,3);self.csel(14,4,31,3);}
        } else {
            if check {self.fail(2);self.load(13,31,self.stack_bytes+24);self.mov(14,4);}self.mov(12,2);
        }
        if check {
            self.cmp(9,31);self.fail(0);self.cmp(9,13);self.fail(8);
            self.three(0xcb000000,13,13,9);self.imm(10,u64::from(size));self.cmp(13,10);self.fail(3);
            if write {self.cmp(9,14);self.fail(3);}
        }
        self.three(0x8b000000,11,12,9);Ok(())
    }
    pub(super) fn path_read(&mut self,id:Id,address:Id,size:u8)->Result<(),&'static str> {
        self.path_address(address,size,false,self.path_guard)?;
        if self.path_guard {
            if !self.path.as_ref().unwrap().needed[id] {return Ok(());}
            let sites=self.path.as_ref().unwrap().sites.clone();
            // Only ranges visited on this guard path have a nonzero host base.
            // Both full ranges were checked against stable disjoint arenas.
            for site in sites {
                self.load(12,31,site.offset);self.cmp(12,31);let inactive=self.words.len();self.emit(0x54000000);
                self.three(0xcb000000,13,11,12);self.imm(14,u64::from(site.size));self.cmp(13,14);self.fail(3);
                self.three(0xcb000000,13,12,11);self.imm(14,u64::from(size));self.cmp(13,14);self.fail(3);
                self.patch(inactive,self.words.len(),true)?;
            }
        }
        match size {
            1|2|4|8=>{let opcode=match size {1=>0x39400000,2=>0x79400000,4=>0xb9400000,_=>0xf9400000};self.emit(opcode|(11<<5)|9);self.mov(10,31);},
            16=>{self.load(9,11,0);self.load(10,11,8);},
            _=>{self.mov(9,31);self.mov(10,31);for byte in 0..size {
                self.emit(0x39400000|((byte as u32)<<10)|(11<<5)|12);self.lsl(12,12,(byte%8)*8);
                let output=if byte<8 {9} else {10};self.three(0xaa000000,output,output,12);
            }},
        }
        self.put(id);Ok(())
    }
    pub(super) fn path_write(&mut self,id:Id,address:Id,value:Id,size:u8)->Result<(),&'static str> {
        self.path_address(address,size,true,self.path_guard)?;
        if self.path_guard {
            let offset=self.path.as_ref().unwrap().sites.iter().find(|s|s.id==id).ok_or("native_path_store_site")?.offset;
            self.store(11,31,offset);return Ok(());
        }
        self.get(9,value,false);if size>8 {self.get(10,value,true);}
        match size {
            1|2|4|8=>{let opcode=match size {1=>0x39000000,2=>0x79000000,4=>0xb9000000,_=>0xf9000000};self.emit(opcode|(11<<5)|9);},
            16=>{self.store(9,11,0);self.store(10,11,8);},
            _=>for byte in 0..size {self.lsr(12,if byte<8 {9} else {10},(byte%8)*8);self.emit(0x39000000|((byte as u32)<<10)|(11<<5)|12);},
        }
        Ok(())
    }
}
