//! Offline coverage only. No relaxed production key, JIT owner or native execution.
use super::*;
use bincode::Options;
use serde::{Deserialize,Serialize};
use sha2::{Digest,Sha256};

fn regions(f:&Function)->Vec<(usize,usize)> {
    if f.code.is_empty() {return vec![];}
    let fills=local_fills(f);
    let native=|pc:usize|supported(&f.code[pc]) || fills.contains_key(&pc) || transfers::supported(&f.code[pc]);
    let mut starts=vec![false;f.code.len()];starts[0]=true;
    for (pc,op) in f.code.iter().enumerate() {
        match op {
            Op::Jump{target}=>starts[*target]=true,
            Op::Switch{cases,otherwise,..}=>{starts[*otherwise]=true;for (_,target) in cases {starts[*target]=true;}},
            _=>{},
        }
        if (!native(pc) || branch(op)) && pc+1<f.code.len() {starts[pc+1]=true;}
    }
    let mut result=vec![];let mut pc=0;
    while pc<f.code.len() {
        let start=pc;
        while pc<f.code.len() && pc-start<1024 && (pc==start || !starts[pc]) && native(pc) {pc+=1;}
        if pc>start {result.push((start,pc));} else {pc+=1;}
    }
    result
}

fn eligible(f:&Function)->Vec<usize> {
    let Some(values)=values::analyze(f) else {return vec![];};
    let mut out=vec![];
    for (start,end) in regions(f) {
        let (mut forbidden,mut stored,mut written)=(BTreeSet::new(),BTreeSet::new(),BTreeSet::new());
        let mut memory_read=false;
        for pc in (start..end).rev() {
            let op=&f.code[pc];
            if let Op::Imm{dst,..}=op {
                if stored.contains(dst) && !forbidden.contains(dst) && !memory_read
                    && (written.contains(dst) || !values.live.after(end-1,*dst)) {out.push(pc);}
            }
            // Every read of this definition must be a Store value. A later
            // definition kills this value, independently of register reuse.
            let mut reads=vec![];let mut writes=vec![];
            crate::registers::visit_registers(op,|r|reads.push(r),|r|writes.push(r));
            for r in writes {forbidden.remove(&r);stored.remove(&r);written.insert(r);}
            for r in reads {
                if matches!(op,Op::Store{src,address,..} if *src==r && *address!=r) {stored.insert(r);}
                else {forbidden.insert(r);}
            }
            // Reject possible propagation through memory within this native
            // region, including copies/helpers. Unknown operations decline.
            if !matches!(op,Op::Imm{..}|Op::Local{..}|Op::Store{..}|Op::Binary{..}|Op::Unary{..}
                |Op::Cast{..}|Op::Select{..}|Op::Assert{..}|Op::Jump{..}|Op::Switch{..}) {memory_read=true;}
        }
    }
    out.sort_unstable();out
}

// MOVZ always materializes the low16bits. Each nonzero upper16bit chunk adds
// one MOVK. Preserve that shape independently in each u64 half.
fn shape(value:u128)->u128 {
    let mut result=0;
    for part in [1,2,3,5,6,7] {if (value>>(part*16))&0xffff!=0 {result|=1u128<<(part*16);}}
    result
}
fn digest(bytes:&[u8])->String {format!("{:x}",Sha256::digest(bytes))}
#[derive(Serialize)]
struct Signature {name:String,exact:String,shape:String,eligible:usize,immediates:usize}
fn signature(f:&Function)->Signature {
    let selected=eligible(f);let mut normalized=f.clone();
    for &pc in &selected {let Op::Imm{value,..}=&mut normalized.code[pc] else {unreachable!()};*value=shape(*value);}
    Signature{name:f.name.clone(),exact:digest(&bincode::serialize(f).unwrap()),
        shape:digest(&bincode::serialize(&(selected.as_slice(),normalized)).unwrap()),eligible:selected.len(),
        immediates:f.code.iter().filter(|op|matches!(op,Op::Imm{..})).count()}
}

fn fixture(code:Vec<Op>)->Function {
    Function{name:"census".into(),frame_size:32,frame_align:8,registers:4,args:vec![],
        result:crate::Slot{offset:0,size:0},code}
}
fn base()->Vec<Op> {vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:0x123456},
    Op::Store{address:0,src:1,size:8},Op::Return]}
#[test]
fn accepts_store_value_and_preserves_native_immediate_width() {
    let f=fixture(base());assert_eq!(eligible(&f),[1]);
    let mut g=f.clone();let Op::Imm{value,..}=&mut g.code[1] else {unreachable!()};*value=0x345678;
    assert_ne!(signature(&f).exact,signature(&g).exact);assert_eq!(signature(&f).shape,signature(&g).shape);
    let Op::Imm{value,..}=&mut g.code[1] else {unreachable!()};*value=7;
    assert_ne!(signature(&f).shape,signature(&g).shape);
    for value in [0,1,0xffff,0x10000,0x100000001, u128::MAX,1<<127] {
        for shift in [0,64] {
            let mut a=Assembler::default();let mut b=Assembler::default();
            a.imm(9,(value>>shift) as u64);b.imm(9,(shape(value)>>shift) as u64);
            assert_eq!(a.words.len(),b.words.len());
        }
    }
}
#[test]
fn rejects_arithmetic_address_and_branch_uses() {
    for op in [Op::Binary{dst:2,overflow:3,op:Binary::Add,a:1,b:0,bits:64,signed:false},
        Op::Store{address:1,src:1,size:8},Op::Switch{value:1,cases:vec![],otherwise:4}] {
        let mut code=base();code.insert(3,op);assert!(eligible(&fixture(code)).is_empty());
    }
}
#[test]
fn rejects_memory_forwarding_and_live_successors() {
    let mut code=base();code.insert(3,Op::Load{dst:2,address:0,size:8});assert!(eligible(&fixture(code)).is_empty());
    let mut code=base();code.insert(3,Op::Jump{target:4});code.insert(4,Op::Store{address:0,src:1,size:8});
    assert!(eligible(&fixture(code)).is_empty());
}
#[test]
fn register_overwrite_separates_definitions() {
    let mut code=base();code.splice(3..3,[Op::Imm{dst:1,value:1},
        Op::Binary{dst:2,overflow:3,op:Binary::Add,a:1,b:0,bits:64,signed:false}]);
    assert_eq!(eligible(&fixture(code)),[1]);
}
#[test]
fn liveness_decline_and_size_split_are_conservative() {
    let mut f=fixture(base());f.registers=65_537;assert!(eligible(&f).is_empty());
    let mut code=vec![Op::Local{dst:0,offset:0}];code.extend((1..1023).map(|_|Op::Local{dst:2,offset:8}));
    code.push(Op::Imm{dst:1,value:123});code.push(Op::Store{address:0,src:1,size:8});code.push(Op::Return);
    let f=fixture(code);assert_eq!(regions(&f),[(0,1024),(1024,1025)]);assert!(eligible(&f).is_empty());
}

#[derive(Deserialize)]
struct Artifact {path:String,sha256:String,state:i32}
#[derive(Deserialize,Serialize)]
struct Attempt {previous:Option<usize>,ordinal:usize,function:usize,worker:usize,emission_ns:u128}
#[derive(Deserialize)]
struct Input {artifacts:Vec<Artifact>,attempts:Vec<Attempt>}
fn bytes(path:&str,limit:u64)->Vec<u8> {
    use std::io::Read;
    let file=std::fs::File::open(path).unwrap();assert!(file.metadata().unwrap().len()<=limit);
    let mut data=vec![];file.take(limit+1).read_to_end(&mut data).unwrap();assert!(data.len() as u64<=limit);data
}
#[test]
#[ignore="requires closed exact parser artifacts and actual miss trace; no guest or JIT owner"]
fn census_saved_parser_immediate_shapes() {
    let input=bytes(&std::env::var("RUST_INTERP_IMMEDIATE_CENSUS_INPUT").unwrap(),16*1024*1024);
    let parsed:Input=serde_json::from_slice(&input).unwrap();
    assert_eq!(parsed.artifacts.iter().map(|a|a.state).collect::<Vec<_>>(),[0,-1,1,2,3,4,5,0]);
    assert!(parsed.attempts.len()<=32_768);
    let mut needed=vec![BTreeSet::new();8];
    for e in &parsed.attempts {
        assert!(e.ordinal<8 && parsed.artifacts[e.ordinal].state>0 && e.worker<2);
        needed[e.ordinal].insert(e.function);
        if let Some(old)=e.previous {assert!(old<=e.ordinal);needed[old].insert(e.function);}
    }
    let mut signatures=vec![];
    for (artifact,ids) in parsed.artifacts.iter().zip(&needed) {
        let raw=bytes(&artifact.path,64*1024*1024);assert_eq!(digest(&raw),artifact.sha256);
        let p:Program=bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64*1024*1024)
            .reject_trailing_bytes().deserialize(&raw).unwrap();crate::validate(&p).unwrap();
        signatures.push(ids.iter().map(|&id|(id,signature(&p.functions[id]))).collect::<BTreeMap<_,_>>());
    }
    let rows=parsed.attempts.iter().map(|e| {
        let now=&signatures[e.ordinal][&e.function];
        let old=e.previous.map(|old|&signatures[old][&e.function]);
        let category=match old {
            None=>"first_worker_function",
            Some(old) if old.exact==now.exact=>"unchanged_body",
            Some(old) if old.shape==now.shape=>"eligible_immediate_shape_match",
            _=>"not_matched",
        };
        serde_json::json!({"attempt":e,"category":category,"current":now,"previous":old})
    }).collect::<Vec<_>>();
    let report=serde_json::json!({"input_sha256":digest(&input),"rows":rows,"guest_commands":0,
        "executable_code_publications":0,"cache_admission":false,"performance_measurement":false,
        "scope":"Conservative function-shape coverage only. Callee/scalar/context identity and native relocation completeness remain unproven. Diagnostic intervals overlap; not predicted savings."});
    let data=serde_json::to_vec(&report).unwrap();assert!(data.len()<=16*1024*1024);
    use std::io::Write;
    std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("RUST_INTERP_IMMEDIATE_CENSUS_OUTPUT").unwrap())
        .unwrap().write_all(&data).unwrap();
}
