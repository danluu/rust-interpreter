//! Diagnostic only: count narrow operands actually consumed at full width.
use super::*;
use serde_json::{json, Value};

fn reads(op:&Op)->Vec<Reg> {let mut out=vec![];register_widths::visit_full_reads(op,|r|out.push(r));out}

#[test]
fn selective_repair_aliases_and_wide_store_payloads_remain_full() {
    for size in 0..=16 {
        assert_eq!(reads(&Op::Store{address:0,src:0,size}),if size>8 {vec![0]} else {vec![]});
    }
    assert_eq!(reads(&Op::CallIndirect{callee:0,args:vec![0,1],arg_sizes:vec![8,8],
        destination:0,result_size:8}),vec![0]);
    assert_eq!(reads(&Op::Binary{dst:0,overflow:0,op:Binary::Mul,a:0,b:0,bits:128,signed:false}),vec![0,0]);
    assert_eq!(reads(&Op::Select{dst:0,condition:0,yes:0,no:0}),vec![0,0,0]);
}

#[test]
fn selective_repair_checked_handles_and_unreviewed_helpers_stay_full() {
    assert_eq!(reads(&Op::RegisterTlsDestructor{callback:0,argument:1}),vec![0,1]);
    assert_eq!(reads(&Op::CAllocate{dst:0,count:0,size:1,errno:2,zeroed:false}),vec![0,1,2]);
    assert_eq!(reads(&Op::DescriptorWrite{dst:0,descriptor:0,address:1,size:2,errno:3}),vec![0,1,2,3]);
    assert_eq!(reads(&Op::EnvironmentGet{dst:1,name:0}),vec![0]);
    assert_eq!(reads(&Op::Assert{value:0,expected:false,message:"full".into()}),vec![0]);
    assert_eq!(reads(&Op::Switch{value:0,cases:vec![],otherwise:0}),vec![0]);
}

#[test]
fn selective_repair_masked_integer_roles_are_width_bounded() {
    for bits in [8,16,32,64,128] {
        let expected=if bits<=64 {vec![]} else {vec![0]};
        assert_eq!(reads(&Op::Cast{dst:0,src:0,from:bits,to:128,signed:true}),expected);
        assert_eq!(reads(&Op::Unary{dst:0,src:0,op:Unary::CountOnes,bits}),expected);
        let expected=if bits<=64 {vec![]} else {vec![0,1]};
        assert_eq!(reads(&Op::Binary{dst:0,overflow:1,op:Binary::Shl,a:0,b:1,bits,signed:true}),expected);
    }
}

#[test]
fn selective_repair_heap_consumers_ignore_high_bits_in_the_actual_interpreter() {
    use crate::{Engine,Limits,Slot,execute_with_engine};
    let mut code=vec![];
    for (dst,offset) in [(0,16),(1,32),(2,48),(5,64)] {
        code.extend([Op::Local{dst:6,offset},Op::Load{dst,address:6,size:16}]);
    }
    let allocate=Op::Allocate{dst:3,size:0,align:1,zeroed:true};
    let reallocate=Op::Reallocate{dst:4,pointer:3,old_size:0,align:1,new_size:2};
    let deallocate=Op::Deallocate{pointer:4,size:2,align:1};
    for op in [&allocate,&reallocate,&deallocate] {assert!(reads(op).is_empty());}
    code.extend([allocate,Op::Binary{dst:3,overflow:6,op:Binary::Or,a:3,b:5,bits:128,signed:false},
        reallocate,Op::Binary{dst:4,overflow:6,op:Binary::Or,a:4,b:5,bits:128,signed:false},deallocate,Op::Return]);
    let p=Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        data:vec![],statics:vec![],thread_locals:vec![],functions:vec![Function{
            name:"heap high words".into(),frame_size:80,frame_align:16,registers:7,
            args:[16,32,48,64].map(|offset|Slot{offset,size:16}).to_vec(),
            result:Slot{offset:0,size:0},code}]};
    for size in [0,1,8,64] {for align in [1,2,3,8] {for new_size in [0,7,128] {
        let expected=execute_with_engine(&p,&[size,align,new_size,0],Limits::default(),Engine::Interpreter);
        for poison in [1u128<<64,0xabcdefu128<<100] {
            let actual=execute_with_engine(&p,&[size|poison,align|poison,new_size|poison,poison],Limits::default(),Engine::Interpreter);
            match (&expected,actual) {
                (Ok(e),Ok(a))=>assert_eq!((a.value,a.instructions,a.peak_memory),(e.value,e.instructions,e.peak_memory)),
                (Err(e),Err(a))=>assert_eq!(&a,e),
                (e,a)=>panic!("size={size} align={align} new={new_size}: {e:?} vs {a:?}"),
            }
        }
    }}}
}

#[test]
#[ignore="Requires retained artifact/current-host profiles; diagnostic JSON only"]
fn observe_selective_repair() {
    let bytes=std::fs::read(std::env::var("SELECTIVE_REPAIR_ARTIFACT").unwrap()).unwrap();
    assert!(bytes.len()<=128*1024*1024);
    let p:Program=bincode::deserialize(&bytes).unwrap();crate::validate(&p).unwrap();
    let proofs:Vec<_>=p.functions.iter().map(register_widths::prove).collect();
    let paths:Vec<String>=serde_json::from_str(&std::env::var("SELECTIVE_REPAIR_PROFILES").unwrap()).unwrap();assert_eq!(paths.len(),2);
    let mut cases=vec![];
    for path in paths {
        let bytes=std::fs::read(&path).unwrap();assert!(bytes.len()<=256*1024*1024);
        let profile:Value=serde_json::from_slice(&bytes).unwrap();
        let fs=profile["functions"].as_array().unwrap();assert_eq!(fs.len(),p.functions.len());
        let mut totals=BTreeMap::<&str,u64>::new();let mut by_kind=BTreeMap::<String,[u64;4]>::new();
        let mut rows=vec![];
        for (id,((f,p),proof)) in p.functions.iter().zip(fs).zip(&proofs).enumerate() {
            let fallback=vec![false;f.registers];let narrow=proof.as_ref().unwrap_or(&fallback);
            let original=serde_json::to_value(super::narrow_storage::work(f,p,narrow).unwrap()).unwrap();
            let mut needed=0u64;let mut unique=0u64;let mut instructions=0u64;
            for (pc,op) in f.code.iter().enumerate() {
                let count=p["interpreted"][pc].as_u64().unwrap();if count==0 {continue;}
                let mut all=0u64;crate::registers::visit_registers(op,|r|all+=u64::from(narrow[r as usize]),|_|{});
                let used:Vec<_>=reads(op).into_iter().filter(|&r|narrow[r as usize]).collect();
                let n=used.len() as u64;let distinct=used.into_iter().collect::<BTreeSet<_>>().len() as u64;
                assert!(distinct<=n&&n<=all);
                let add=|a:&mut u64,b:u64| {*a=a.checked_add(count.checked_mul(b).unwrap()).unwrap();};
                add(&mut needed,n);add(&mut unique,distinct);add(&mut instructions,u64::from(n!=0));
                let kind=format!("{op:?}").split([' ','{']).next().unwrap().to_owned();
                let row=by_kind.entry(kind).or_default();
                for (a,b) in row.iter_mut().zip([1,all,n,distinct]) {add(a,b);}
            }
            for (key,value) in [("interpreted_instructions",original["interpreted_instructions"].as_u64().unwrap()),
                ("all_narrow_read_operands",original["narrow_read_operands"].as_u64().unwrap()),
                ("full_narrow_read_operands",needed),("unique_full_narrow_reads",unique),
                ("instructions_with_full_narrow_reads",instructions)] {
                let entry=totals.entry(key).or_default();*entry=entry.checked_add(value).unwrap();
            }
            rows.push(json!({"function":id,"original":original,"full_reads":needed,"unique_full_reads":unique,
                "instructions_with_full_reads":instructions}));
        }
        cases.push(json!({"path":path,"sha256":format!("{:x}",Sha256::digest(bytes)),
            "totals":totals,"by_kind":by_kind,"functions":rows}));
    }
    let output=std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("SELECTIVE_REPAIR_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(output,&json!({"status":"passed","cases":cases,
        "artifact_sha256":format!("{:x}",Sha256::digest(bytes)),"guest_commands":0,
        "production_runtime_changes":0,"executable_code_publications":0})).unwrap();
}
