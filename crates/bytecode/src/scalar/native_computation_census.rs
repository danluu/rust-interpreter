//! Read-only scalar computation census. No guest execution or code publication.
use super::*;
use serde_json::{Value as Json, json};
use sha2::{Digest, Sha256};

fn known(value: &Value, facts: &[Option<u128>]) -> Option<u128> {
    let get = |id: Id| facts.get(id).copied().flatten();
    match value {
        Value::Constant(v) => Some(*v),
        Value::Input(_) | Value::Base(_) => None,
        Value::Pack(parts) => {
            let mut value=0; let mut shift=0;
            for p in parts { value |= slice(get(p.value)?,*p)<<shift; shift+=p.size as u32*8; }
            Some(value)
        },
        Value::Phi(parts) => {
            let first=parts.first()?.1;
            let value=slice(get(first.value)?,first);
            for (_,p) in parts { if slice(get(p.value)?,*p)!=value { return None; } }
            Some(value)
        },
        Value::Binary{a,b,op,bits,signed,overflow} => {
            // An error stays unknown: a failed constant division cannot be
            // replaced by a value, including when only its overflow is used.
            let (value,over)=crate::binary(*op,get(*a)?,get(*b)?,*bits,*signed).ok()?;
            Some(if *overflow {u128::from(over)} else {value})
        },
        Value::Unary{src,op,bits} => {
            let v=get(*src)?&mask(*bits);
            Some(match op {
                Unary::Not=>!v&mask(*bits), Unary::Neg=>v.wrapping_neg()&mask(*bits),
                Unary::CountOnes=>v.count_ones() as u128,
                Unary::LeadingZeros=>(v.leading_zeros()-(128-u32::from(*bits))) as u128,
                Unary::TrailingZeros=>v.trailing_zeros().min(u32::from(*bits)) as u128,
                Unary::SwapBytes=>v.swap_bytes()>>(128-*bits),
            })
        },
        Value::Cast{src,from,to,signed} => {
            let v=get(*src)?;
            let n=if *signed {(((v<<(128-*from)) as i128)>>(128-*from)) as u128} else {v&mask(*from)};
            Some(n&mask(*to))
        },
        Value::Select{condition,yes,no} => get(if get(*condition)?!=0 {*yes} else {*no}),
    }
}

// Maximum possibly nonzero low bits, independent of the runtime arguments.
// This models opportunities only; it does not change the plan or emitter.
fn bit_bound(node:&Node,bounds:&[u16]) -> u16 {
    let get=|id:Id|bounds[id];
    let part=|p:Slice|get(p.value).saturating_sub(u16::from(p.byte)*8).min(u16::from(p.size)*8);
    match &node.value {
        Value::Constant(v)=>(128-v.leading_zeros()) as u16,
        Value::Input(_)=>u16::from(node.width)*8,Value::Base(_)=>64,
        Value::Phi(parts)=>parts.iter().map(|(_,p)|part(*p)).max().unwrap_or(0),
        Value::Pack(parts)=>{
            let mut bits=0;let mut shift=0;
            for p in parts {let n=part(*p);if n!=0 {bits=bits.max(shift+n);}shift+=u16::from(p.size)*8;}
            bits
        },
        Value::Binary{overflow:true,..}=>1,
        Value::Binary{a,b,op,bits,signed,..}=>{
            let limit=u16::from(*bits);let left=get(*a).min(limit);let right=get(*b).min(limit);
            match op {
                Binary::Eq|Binary::Ne|Binary::Lt|Binary::Le|Binary::Gt|Binary::Ge=>1,
                Binary::Cmp=>8,
                Binary::And=>left.min(right),Binary::Or|Binary::Xor=>left.max(right),
                Binary::Add=>(left.max(right)+1).min(limit),Binary::Mul=>(left+right).min(limit),
                Binary::Div|Binary::Rem|Binary::Shr if !signed=>left,
                _=>limit,
            }
        },
        Value::Unary{op,bits,..}=>match op {
            Unary::CountOnes|Unary::LeadingZeros|Unary::TrailingZeros=>8,
            _=>u16::from(*bits),
        },
        Value::Cast{src,from,to,signed}=>{
            let bound=get(*src);let from=u16::from(*from);let to=u16::from(*to);
            if !signed || bound<from {bound.min(from).min(to)} else {to}
        },
        Value::Select{yes,no,..}=>get(*yes).max(get(*no)),
    }
}

#[test]
fn scalar_computation_width_bounds_keep_signed_casts_and_overflow_bits() {
    let node=|value|Node{value,width:16,pc:Some(0)};
    assert_eq!(bit_bound(&node(Value::Binary{a:0,b:1,op:Binary::Eq,bits:64,signed:true,overflow:false}),&[64,64]),1);
    assert_eq!(bit_bound(&node(Value::Binary{a:0,b:1,op:Binary::Add,bits:64,signed:false,overflow:false}),&[8,8]),9);
    assert_eq!(bit_bound(&node(Value::Binary{a:0,b:1,op:Binary::Mul,bits:64,signed:false,overflow:false}),&[8,8]),16);
    assert_eq!(bit_bound(&node(Value::Cast{src:0,from:8,to:64,signed:true}),&[8]),64);
    assert_eq!(bit_bound(&node(Value::Cast{src:0,from:8,to:64,signed:true}),&[7]),7);
    assert_eq!(bit_bound(&node(Value::Cast{src:0,from:8,to:4,signed:true}),&[8]),4);
    assert_eq!(bit_bound(&node(Value::Pack(vec![Slice{value:0,byte:0,size:1},Slice{value:1,byte:0,size:1}])),&[1,0]),1);
}

#[test]
fn scalar_computation_facts_preserve_faults_overflow_and_byte_joins() {
    let binary=|op,bits,signed,overflow| Value::Binary{a:0,b:1,op,bits,signed,overflow};
    assert_eq!(known(&binary(Binary::Mul,8,false,false),&[Some(255),Some(2)]),Some(254));
    assert_eq!(known(&binary(Binary::Mul,8,false,true),&[Some(255),Some(2)]),Some(1));
    assert_eq!(known(&binary(Binary::Add,8,true,false),&[Some(127),Some(1)]),Some(128));
    assert_eq!(known(&binary(Binary::Add,8,true,true),&[Some(127),Some(1)]),Some(1));
    for op in [Binary::Div,Binary::Rem] { for overflow in [false,true] {
        assert_eq!(known(&binary(op,64,false,overflow),&[Some(1),Some(0)]),None);
        assert_eq!(known(&binary(op,64,true,overflow),&[Some(1<<63),Some(u64::MAX as u128)]),None);
    }}
    assert_eq!(known(&Value::Cast{src:0,from:8,to:128,signed:true},&[Some(255)]),Some(u128::MAX));
    let a=Slice{value:0,byte:1,size:1};let b=Slice{value:1,byte:0,size:1};
    assert_eq!(known(&Value::Phi(vec![(0,a),(1,b)]),&[Some(0x1234),Some(0x12)]),Some(0x12));
    assert_eq!(known(&Value::Phi(vec![(0,a),(1,b)]),&[Some(0x1234),Some(0x13)]),None);
    assert_eq!(known(&Value::Pack(vec![a,b]),&[Some(0x1234),Some(0x56)]),Some(0x5612));
    assert_eq!(known(&Value::Pack(vec![a,b]),&[Some(0x1234),None]),None);
    assert_eq!(known(&Value::Select{condition:0,yes:1,no:2},&[Some(0),None,Some(42)]),Some(42));
}

#[test]
#[ignore = "Requires pinned public artifacts and closed scalar profiles"]
fn observe_original_scalar_computations() {
    let input:Json=serde_json::from_slice(&std::fs::read(std::env::var("SCALAR_COMPUTATION_INPUT").unwrap()).unwrap()).unwrap();
    let mut cases=vec![];
    for case in input.as_array().unwrap() {
        let read=|key:&str| {
            let data=std::fs::read(case[key].as_str().unwrap()).unwrap();
            assert!(data.len()<=128*1024*1024);
            assert_eq!(format!("{:x}",Sha256::digest(&data)),case[format!("{key}_sha256")]);
            data
        };
        let artifact=read("artifact");let program:crate::Program=bincode::deserialize(&artifact).unwrap();
        crate::validate(&program).unwrap();
        let profile:Json=serde_json::from_slice(&read("profile")).unwrap();
        let mapping:Json=serde_json::from_slice(&read("map")).unwrap();let code=read("code");
        assert_eq!(mapping["profiled"],true);assert_eq!(mapping["architecture"],"aarch64");
        let mut work=crate::proof::MAX_GLOBAL_WORK;let mut rows=vec![];
        for (function,f) in program.functions.iter().enumerate() {
            let memory=crate::proof::memory_plan(&program,function,&mut work);
            let ranges:Vec<_>=mapping["ranges"].as_array().unwrap().iter().filter(|r|
                r["kind"]=="scalar_leaf" && r["function"]==function).collect();
            if ranges.is_empty() {continue;}assert_eq!(ranges.len(),1);let range=ranges[0];
            assert_eq!(range["name"],f.name);let plan=lower(f,&memory,250_000).unwrap();
            let emitted=emit_prechecked(&plan,true).unwrap();
            let bytes:Vec<_>=emitted.words.iter().flat_map(|w|w.to_le_bytes()).collect();
            assert_eq!(&bytes, &code[range["offset"].as_u64().unwrap() as usize..range["end"].as_u64().unwrap() as usize],"source-qualified native body differs: {function}");
            let observed=&profile["functions"][function];assert_eq!(observed["name"],f.name);
            let hits:Vec<u64>=serde_json::from_value(observed["jit_scalar_hits"].clone()).unwrap();assert_eq!(hits.len(),f.code.len());
            let mut facts=vec![];let mut bounds=vec![];let mut aliases=vec![];
            let mut constants=vec![];let mut duplicate_pairs=vec![];let mut effects=vec![];
            for (id,node) in plan.nodes.iter().enumerate() {
                assert!(node.inputs().iter().all(|&input|input<id));
                let fact=known(&node.value,&facts);facts.push(fact);
                let bound=bit_bound(node,&bounds);assert!(bound<=128);bounds.push(bound);
                if plan.live[id] {
                    let alias=match &node.value {
                        Value::Pack(parts) if parts.len()==1 && parts[0].byte==0 && bounds[parts[0].value]<=u16::from(parts[0].size)*8=>Some(("pack",parts[0].value)),
                        Value::Cast{src,from,to,signed} if bounds[*src]<=u16::from((*from).min(*to)) && (!signed || from==to || bounds[*src]<u16::from(*from))=>Some(("cast",*src)),
                        _=>None,
                    };
                    if let Some((kind,source))=alias {
                        let pc=node.pc.unwrap();aliases.push(json!({"node":id,"pc":pc,"kind":kind,"source":source,
                            "source_bits":bounds[source],"successful_computations":hits[pc]}));
                    }
                }
                if !plan.live[id] || fact.is_none() {continue;}
                let (kind,pc)=match &node.value {
                    Value::Constant(_)|Value::Input(_)|Value::Base(_)=>continue,
                    Value::Phi(_)=> ("phi",plan.blocks.iter().find(|b|b.phis.contains(&id)).unwrap().start),
                    Value::Pack(_)=>("pack",node.pc.unwrap()),Value::Binary{overflow:true,..}=>("overflow",node.pc.unwrap()),
                    Value::Binary{..}=>("binary",node.pc.unwrap()),Value::Unary{..}=>("unary",node.pc.unwrap()),
                    Value::Cast{..}=>("cast",node.pc.unwrap()),Value::Select{..}=>("select",node.pc.unwrap()),
                };
                constants.push(json!({"node":id,"pc":pc,"kind":kind,"value":format!("{:x}",fact.unwrap()),"successful_computations":hits[pc]}));
            }
            for (pc,ids) in plan.computations.iter().enumerate() {
                if ids.len()!=2 || !plan.live[ids[0]] || !plan.live[ids[1]] {continue;}
                if let (Value::Binary{a,b,op,bits,signed,overflow:false},Value::Binary{a:c,b:d,op:other,bits:width,signed:sign,overflow:true})=(&plan.nodes[ids[0]].value,&plan.nodes[ids[1]].value) {
                    if a==c && b==d && bits==width && signed==sign && matches!((op,other),
                        (Binary::Add,Binary::Add)|(Binary::Sub,Binary::Sub)|(Binary::Mul,Binary::Mul)) {
                        duplicate_pairs.push(json!({"pc":pc,"operation":format!("{op:?}"),"bits":bits,"signed":signed,
                            "both_constant":facts[ids[0]].is_some() && facts[ids[1]].is_some(),"successful_pairs":hits[pc]}));
                    }
                }
            }
            for (pc,effect) in plan.effects.iter().enumerate() {
                match effect {
                    Effect::Assert{value,expected,..}=>if let Some(v)=facts[*value] {
                        assert!(hits[pc]==0 || (v!=0)==*expected);
                        effects.push(json!({"pc":pc,"kind":"assert","passes":(v!=0)==*expected,"successful_visits":hits[pc]}));
                    },
                    Effect::Switch{value,..}=>if facts[*value].is_some() {
                        effects.push(json!({"pc":pc,"kind":"switch","successful_visits":hits[pc]}));
                    },_=>{},
                }
            }
            rows.push(json!({"function":function,"name":f.name,"calls":hits[0],"constant_nodes":constants,"width_aliases":aliases,
                "duplicate_arithmetic_pairs":duplicate_pairs,"constant_effects":effects,"native_bytes_reconstructed":bytes.len()}));
        }
        let expected=mapping["ranges"].as_array().unwrap().iter().filter(|r|r["kind"]=="scalar_leaf").count();
        assert_eq!(rows.len(),expected);cases.push(json!({"index":case["index"],"functions":rows}));
    }
    let output=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("SCALAR_COMPUTATION_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(output,&json!({"status":"passed","cases":cases,"guest_commands":0,"executable_code_publications":0,
        "performance_measurement":false,"scope":"Static scalar computations weighted by exact successful original-PC counts. Failed private attempts excluded. Categories overlap; counts are not hardware instructions, removed work or measured speedups."})).unwrap();
}
