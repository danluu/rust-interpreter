//! Complete Call/Return comparisons, including memory on every error exit.
use super::*;
use crate::scalar_call_model::with_memory_snapshot;

struct Observation {
    result:Result<(u128,u64,usize),String>,
    memory:Option<(Vec<u8>,Vec<u8>)>,
    counts:Option<Vec<Vec<u64>>>,
    commits:usize,
}
fn observe(p:&Program,args:&[u128],limits:Limits,engine:Engine,profiled:bool)->Observation {
    let ((result,profile),memory)=with_memory_snapshot(|| {
        if profiled {match execute_profiled(p,args,limits,engine) {
            Ok((execution,profile))=>(Ok(execution),Some(profile)),Err(e)=>(Err(e),None),
        }} else {(crate::execute_with_engine(p,args,limits,engine),None)}
    });
    let commits=profile.as_ref().map_or(0,|profile|profile.functions.iter().zip(&p.functions).map(|(row,f)|
        row.jit_scalar_hits.iter().zip(&f.code).filter(|(_,op)|matches!(op,Op::Return)).map(|(h,_)|*h as usize).sum::<usize>()).sum());
    if let (Ok(run),Some(profile))=(&result,&profile) {
        let native=profile.functions.iter().map(|row|row.jit_scalar_hits.iter().sum::<u64>()+
            row.jit_blocks.iter().enumerate().map(|(pc,h)|if *h==0 {0} else {*h*(row.jit_block_ends[pc]-pc) as u64}).sum::<u64>()).sum::<u64>();
        assert_eq!(run.jit_instructions,native);
    }
    Observation{result:result.map(|r|(r.value,r.instructions,r.peak_memory)),memory,
        counts:profile.as_ref().map(counts),commits}
}
fn compare_complete(p:&Program,args:&[u128],limits:Limits)->usize {
    let mut commits=0;
    for profiled in [false,true] {
        let reference=observe(p,args,limits.clone(),Engine::Interpreter,profiled);
        for persistent in [false,true] {
            let mut options=limits.clone();options.jit_resumable_calls=true;options.jit_persistent_registers=persistent;
            let baseline=observe(p,args,options.clone(),Engine::Jit,profiled);
            options.jit_scalar_calls=true;options.jit_indirect_calls=true;
            let actual=observe(p,args,options,Engine::Jit,profiled);
            assert_eq!(actual.result,baseline.result,"baseline JIT result/error");
            assert_eq!(actual.memory,baseline.memory,"baseline JIT full error/success memory");
            assert_eq!(actual.counts,baseline.counts);
            assert_eq!(actual.memory,reference.memory,"ordinary interpreter full error/success memory");
            match (&reference.result,&actual.result) {
                (Ok(a),Ok(b))=>{assert_eq!(a,b);assert_eq!(reference.counts,actual.counts);},
                (Err(a),Err(b))=>assert!(a==b || (b=="JIT guest memory access failed"
                    && matches!(a.as_str(),"invalid guest memory access"|"write to read-only guest memory")),"interpreter {a}, JIT {b}"),
                (a,b)=>panic!("interpreter {a:?}, native indirect/scalar {b:?}"),
            }
            if profiled {commits=actual.commits;}
        }
    }
    commits
}

fn limits()->Limits {Limits{instructions:1024,memory:65536,frames:8,..Limits::default()}}
fn pair(fault:u8)->Program {
    let parent=function("indirect parent",96,16,vec![Slot{offset:0,size:8},Slot{offset:8,size:8}],Slot{offset:16,size:8},vec![
        local(0,0),local(1,8),Op::Imm{dst:2,value:(crate::FUNCTION_POINTER_TAG|2) as u128},local(3,16),
        Op::CallIndirect{callee:2,args:vec![0,1],arg_sizes:vec![8,8],destination:3,result_size:8},
        Op::CallIndirect{callee:2,args:vec![0,1],arg_sizes:vec![8,8],destination:3,result_size:8},Op::Return]);
    let mut middle=function("indirect target with scalar child",64,64,vec![Slot{offset:0,size:8},Slot{offset:8,size:8}],Slot{offset:32,size:8},vec![
        local(0,0),local(1,32),Op::Call{function:2,args:vec![0],destination:1},local(2,8),load(3,2,8),load(4,1,8)]);
    if fault==1 {middle.code.push(Op::Trap{message:"before external write".into()});}
    middle.code.push(Op::Store{address:3,src:4,size:8});
    if fault==2 {middle.code.push(Op::Trap{message:"after external write".into()});}
    middle.code.push(Op::Return);
    let child=function("confined scalar child",24,32,vec![Slot{offset:8,size:8}],Slot{offset:0,size:8},vec![
        local(0,8),load(1,0,8),Op::Imm{dst:2,value:7},
        Op::Binary{dst:1,overflow:3,op:crate::Binary::Add,a:1,b:2,bits:64,signed:false},
        local(4,0),Op::Store{address:4,src:1,size:8},Op::Return]);
    let mut p=program(vec![parent,middle,child]);p.data=vec![0x55;64];p.statics=vec![0x66;64];p
}
fn addresses()->Vec<u128> {let h=crate::heap::TAG as u128;
    vec![0,1,63,64,65,152,153,160,168,184,192,200,h,h+1,h+56,h+57,h+64,u64::MAX as u128]}

#[test]
fn indirect_scalar_complete_memory_on_success_and_ordered_faults() {
    for fault in 0..=2 {
        let p=pair(fault);
        for address in addresses() {compare_complete(&p,&[41,address],limits());}
    }
    assert_eq!(compare_complete(&pair(0),&[41,crate::heap::TAG as u128+1],limits()),2);
}

#[test]
fn indirect_scalar_complete_memory_at_instruction_and_resource_tails() {
    let p=pair(0);let args=[41,crate::heap::TAG as u128+1];
    let total=crate::execute_with_engine(&p,&args,limits(),Engine::Interpreter).unwrap().instructions;
    for instructions in 0..=total+1 {compare_complete(&p,&args,Limits{instructions,..limits()});}
    for frames in 0..=4 {for memory in [0,63,64,127,255,511,767,1023,4096] {
        compare_complete(&p,&args,Limits{frames,memory,..limits()});
    }}
}

#[test]
fn indirect_scalar_warm_faults_preserve_complete_memory() {
    for fault in 0..=2 {for persistent in [false,true] {
        let p=pair(fault);let options=Limits{jit_resumable_calls:true,jit_scalar_calls:true,jit_indirect_calls:true,
            jit_persistent_registers:persistent,..limits()};
        let mut prepared=crate::PreparedJit::new(&p,&options).unwrap();
        let _=prepared.execute_entry(1,&[41,crate::heap::TAG as u128+1],options.clone());
        for address in addresses() {
            let args=[41,address];let reference=observe(&p,&args,limits(),Engine::Interpreter,false);
            let (actual,memory)=with_memory_snapshot(||prepared.execute(&args,options.clone()));
            let actual=actual.map(|r|(r.value,r.instructions,r.peak_memory));
            assert_eq!(memory,reference.memory,"full memory after warm indirect target, fault={fault} address={address}");
            match (actual,reference.result) {
                (Ok(a),Ok(b))=>assert_eq!(a,b),
                (Err(a),Err(b))=>assert!(a==b || a=="JIT guest memory access failed" &&
                    matches!(b.as_str(),"invalid guest memory access"|"write to read-only guest memory")),
                (a,b)=>panic!("warm native/interpreter result mismatch: {a:?} / {b:?}"),
            }
        }
    }}
}

fn readonly_pair(fault:u8)->Program {
    let mut p=pair(fault);
    let parent=&mut p.functions[0];
    parent.code.insert(1,load(7,0,8));
    parent.code.insert(5,Op::Switch{value:7,cases:vec![(0,7)],otherwise:6});
    p.functions[2].name="readonly scalar child through indirect target".into();
    p.functions[2].code=vec![local(0,8),load(1,0,8),load(2,1,8),Op::Imm{dst:3,value:7},
        Op::Binary{dst:2,overflow:4,op:crate::Binary::Add,a:2,b:3,bits:64,signed:false},
        local(5,0),Op::Store{address:5,src:2,size:8},Op::Return];
    crate::validate(&p).unwrap();p
}

#[test]
fn composed_indirect_readonly_and_dead_branch_preserve_full_memory() {
    for fault in 0..=2 {for heap in [false,true] {
        let mut p=readonly_pair(fault);if !heap {p.statics.clear();}
        let destination=if heap {crate::heap::TAG as u128+1} else {80};
        for pointer in addresses() {compare_complete(&p,&[pointer,destination],limits());}
        for destination in addresses() {compare_complete(&p,&[32,destination],limits());}
    }}
    assert_eq!(compare_complete(&readonly_pair(0),&[crate::heap::TAG as u128+1,crate::heap::TAG as u128+1],limits()),2);
}

#[test]
fn composed_indirect_readonly_all_budgets_and_resource_tails_match() {
    let p=readonly_pair(0);let args=[32,crate::heap::TAG as u128+1];
    let total=crate::execute_with_engine(&p,&args,limits(),Engine::Interpreter).unwrap().instructions;
    for instructions in 0..=total+1 {compare_complete(&p,&args,Limits{instructions,..limits()});}
    for frames in 0..=4 {for memory in [0,63,64,127,255,511,767,1023,4096] {
        compare_complete(&p,&args,Limits{frames,memory,..limits()});
    }}
    for capacity in [0,4,64,1024,16*1024*1024] {
        compare_complete(&p,&args,Limits{jit_code_bytes:capacity,..limits()});
    }
}

#[test]
#[cfg(feature="jit-template-session")]
fn session_composition_verified_history_preserves_readonly_indirect_memory_and_faults() {
    for verify in [false,true] {for persistent in [false,true] {
        let history=crate::TemplateHistory::new(1024*1024,verify).unwrap();let mut hits=0;
        for edit in 0..4 {
            let mut p=readonly_pair(0);
            let mut extra=p.functions[2].clone();extra.name="unrelated signature edit".into();
            extra.result.size=if edit%2==0 {16} else {4};p.functions.push(extra);
            p.data[32]=if edit<2 {0x55} else {0x77};
            if edit>=2 {
                p.functions[1].frame_size=96;p.functions[1].frame_align=32;p.functions[1].registers+=1;
                let zero=p.functions[1].registers as Reg-1;
                p.functions[1].code.insert(0,Op::Assert{value:zero,expected:false,message:"fresh changed registers".into()});
            }
            for indirect in [false,true] {for instructions in [0,1,7,19,1024] {
                let options=Limits{instructions,jit_resumable_calls:true,jit_scalar_calls:true,
                    jit_indirect_calls:indirect,jit_persistent_registers:persistent,..limits()};
                let mut cached=crate::PreparedJit::with_template_history(&p,&options,&history).unwrap();
                for pointer in [32,crate::heap::TAG as u128+1,u64::MAX as u128] {
                    let args=[pointer,crate::heap::TAG as u128+1];
                    let reference=observe(&p,&args,Limits{instructions,..limits()},Engine::Interpreter,false);
                    let (actual,memory)=with_memory_snapshot(||cached.execute(&args,options.clone()));
                    assert_eq!(memory,reference.memory,"edit={edit} indirect={indirect} budget={instructions} pointer={pointer}");
                    match (actual.map(|r|(r.value,r.instructions,r.peak_memory)),reference.result) {
                        (Ok(a),Ok(b))=>assert_eq!(a,b),
                        (Err(a),Err(b))=>assert!(a==b || a=="JIT guest memory access failed" &&
                            matches!(b.as_str(),"invalid guest memory access"|"write to read-only guest memory")),
                        (a,b)=>panic!("cached composition/interpreter outcome differs: {a:?} / {b:?}"),
                    }
                }
                let stats=cached.template_statistics().unwrap();hits+=stats.hits;
                assert_eq!(stats.verified_hits,if verify {stats.hits} else {0});
            }}
        }
        assert!(hits>0);assert!(history.storage().charged_bytes<=1024*1024);
    }}
}
