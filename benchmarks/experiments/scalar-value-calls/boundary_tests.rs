
#[test]
fn value_return_publication_checks_caller_register_width_and_tag_context() {
    let mut f=Fixture::new();f.program.version=crate::scalar_abi::SCALAR_VERSION;
    f.program.functions[1].result.size=8;
    f.memory.bytes.resize(128,0);f.register_bytes=10*16;
    f.frames.push(Frame{function:1,pc:0,base:64,register_base:4,return_address:3,
        tls_callback:false,return_value:true});
    let valid=|f:&Fixture|Boundary::new(&f.program,&f.memory,&f.registers,&f.frames,f.register_bytes,100,&f.limits,
        Capacity{memory:512,registers:64,frames:8},std::ptr::null_mut()).is_ok();
    assert!(valid(&f));
    f.frames[1].return_address=4;assert!(!valid(&f));f.frames[1].return_address=3;
    f.frames[1].tls_callback=true;assert!(!valid(&f));f.frames[1].tls_callback=false;
    f.program.functions[1].result.size=0;assert!(!valid(&f));f.program.functions[1].result.size=8;
    f.program.version=crate::VERSION;assert!(!valid(&f));f.program.version=crate::scalar_abi::SCALAR_VERSION;
    f.frames.pop();f.register_bytes=4*16;f.memory.bytes.truncate(64);
    f.frames[0].return_value=true;assert!(!valid(&f));
}
