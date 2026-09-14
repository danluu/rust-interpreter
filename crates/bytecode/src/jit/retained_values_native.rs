use super::*;

impl Assembler<'_> {
    pub(in crate::jit) fn capture_retained(&mut self,size:usize) {
        let Some(c)=self.retained.plan.as_ref().and_then(|p|p.captures.get(&self.current_pc)).copied() else{return;};
        assert_eq!(size,c.size);assert!([4,8,16].contains(&size));
        let reg=17+c.slot as u32;
        memory_part!(self,"retained_capture",{
            self.emit((if size==4 {0x1e270000}else{0x9e670000})|(9<<5)|reg); // fmov S/Dd,W/X9
            if size==16 {self.emit(0x4e181c00|(10<<5)|reg);} // ins Vd.d[1],x10
        });
        self.retained.active[c.slot]=Some(self.current_pc);
    }
    pub(in crate::jit) fn retained_load(&mut self,address:Reg,size:usize)->bool {
        let Some(reg)=self.retained.register(self.current_pc,size)else{return false;};
        if self.local_range(address,size).is_none() {return false;}
        memory_part!(self,"retained_load",{
            self.emit((if size==4 {0x1e260000}else{0x9e660000})|(reg<<5)|9); // fmov W/X9,S/Dn
            if size==16 {self.emit(0x4e183c00|(reg<<5)|10);} // umov x10,Vn.d[1]
        });
        true
    }
    pub(in crate::jit) fn retained_copy(&mut self,dst:Reg,src:Reg,size:usize)->bool {
        let Some(reg)=self.retained.register(self.current_pc,size)else{return false;};
        let Some(destination)=self.local_range(dst,size)else{return false;};
        let Some(source)=self.local_range(src,size)else{return false;};
        let forwarded=self.local_value(Some(source),size);
        let immediate=if destination%size==0 && destination/size<4096 {
            memory_part!(self,"frame_address",self.three(0x8b000000,11,2,1));
            (destination/size)as u32
        }else{
            memory_access!(self,"destination",self.address(11,dst,size,true));0
        };
        // Both complete ranges belong to the stable, writable active frame.
        // The captured source precedes any overlapping destination write.
        let opcode=match size {4=>0xbd000000,8=>0xfd000000,16=>0x3d800000,_=>unreachable!()};
        memory_part!(self,"retained_store",self.emit(opcode|(immediate<<10)|(11<<5)|reg));
        self.invalidate_local_memory(Some(destination),size);
        if let Some((source,_))=forwarded {self.remember_local_memory(Some(destination),size,source);}
        // x9 did not receive this value. In particular, do not label the
        // destination with the ordinary Copy path's scratch capture.
        true
    }
}

#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
#[path="retained_values_native_tests.rs"]
mod tests;
