use super::*;

fn cached_observation() -> Observation {
    Observation {
        id: 2, name: "caller".into(), origins: BTreeMap::from([(0, 1)]), abi_count: 1,
        capture_nanos: 91, extent: 32, slots: vec![Slot { offset: 0, size: 16 }],
        shapes: vec![(16, 8)], reasons: vec![None],
        events: vec![vec![Event { reads: Set::new(), writes: Set::from([0]) }]],
        successors: vec![vec![]], baseline: true, decline: None,
        writes: vec![Write { block: 0, event: 0, local: 0,
            coverage: Coverage { calls: vec![(0, 0, vec![])], straight: true, ..Coverage::default() } }],
    }
}

#[test]
fn cached_frame_observation_rebinds_callee_layout_and_preserves_byte_coverage() {
    let original = cached_observation();
    let bytes = bincode::serialize(&original).unwrap();
    let mut restored: Observation = bincode::deserialize(&bytes).unwrap();
    assert_eq!(restored.semantic_bytes().unwrap(), original.semantic_bytes().unwrap());
    restored.rebind(7, &BTreeMap::from([(0, 1)])).unwrap();
    assert_eq!(restored.id, 7);
    assert_eq!(restored.capture_nanos, 0);
    let mut p = program(8, &[]);
    p.functions.push(program(16, &[]).functions.remove(0));
    let slot = Slot { offset: 0, size: 16 };
    assert!(!original.writes[0].coverage.clone().complete(slot, &p));
    assert!(restored.writes[0].coverage.clone().complete(slot, &p));
    p.functions[1].args.push(Slot { offset: 0, size: 8 });
    assert!(!restored.writes[0].coverage.clone().complete(slot, &p));
    assert!(cached_observation().rebind(7, &BTreeMap::new()).is_err());
}

#[test]
fn cached_frame_observation_retains_closed_decline_reasons_without_interning() {
    let mut original = cached_observation();
    original.reasons = vec![None, Some("abi"), Some("zero_size"), Some("address_or_unsupported_context")];
    original.decline = Some("origin_bound");
    let bytes = bincode::serialize(&original).unwrap();
    let restored: Observation = bincode::deserialize(&bytes).unwrap();
    assert_eq!(restored.reasons, original.reasons);
    assert_eq!(restored.decline, original.decline);
    let mut json = serde_json::to_value(&original).unwrap();
    json["decline"] = serde_json::json!("unexpected cache-supplied label");
    assert!(serde_json::from_value::<Observation>(json).is_err());
}

fn program(result: usize, args: &[usize]) -> Program {
    Program { version: VERSION, target: "diagnostic".into(), entry: 0, data: vec![], statics: vec![], thread_locals: vec![],
        functions: vec![Function { name: "callee".into(), frame_size: 128, frame_align: 16, registers: 0,
            args: args.iter().map(|&size| Slot { offset: 0, size }).collect(),
            result: Slot { offset: 0, size: result }, code: vec![Op::Return] }] }
}

#[test]
fn coverage_matches_independent_byte_cells_including_padding_and_partial_stores() {
    let p = program(0, &[]);
    let slot = Slot { offset: 8, size: 8 };
    let mut seed = 0x3541eabc_u64;
    for _ in 0..10_000 {
        let mut next = |n: usize| { seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17; seed as usize % n };
        let mut c = Coverage { straight: true, ..Coverage::default() };
        let mut cells = [false; 32];
        let mut observed = false;
        for _ in 0..6 {
            let (at, size) = (next(24), next(9));
            if next(4) == 0 {
                c.reads.push((at, size));
                observed |= (at..at+size).any(|i| (8..16).contains(&i));
            } else {
                c.writes.push((at, size));
                for i in at..at+size { cells[i] = true; }
            }
        }
        assert_eq!(c.complete(slot, &p), !observed && cells[8..16].iter().all(|x| *x), "rng state {seed:x}");
    }
    let c = Coverage { straight: true, writes: vec![(8,1),(12,4)], ..Coverage::default() };
    assert!(!c.complete(slot, &p)); // holes cannot be borrowed from another lifetime
    let c = Coverage { straight: true, writes: vec![(usize::MAX,8)], ..Coverage::default() };
    assert!(!c.complete(slot, &p));
}

#[test]
fn owned_coverage_preserves_range_read_and_zero_size_edge_decisions() {
    let p = program(0, &[]);
    let cases = [
        ("adjacent unsorted", 8, 8, true, vec![(12,4),(8,4)], vec![], true),
        ("duplicate", 8, 8, true, vec![(8,4),(8,4),(12,4)], vec![], true),
        ("overlap", 8, 8, true, vec![(8,6),(12,4)], vec![], true),
        ("hole", 8, 8, true, vec![(8,2),(12,4)], vec![], false),
        ("initial gap", 8, 8, true, vec![(9,8)], vec![], false),
        ("cover from before", 8, 8, true, vec![(0,16)], vec![], true),
        ("read after write", 8, 8, true, vec![(8,8)], vec![(15,1)], false),
        ("touching reads", 8, 8, true, vec![(8,8)], vec![(0,8),(16,1)], true),
        ("empty read", 8, 8, true, vec![(8,8)], vec![(12,0)], true),
        ("saturating read end", 8, 8, true, vec![(8,8)], vec![(7,usize::MAX)], false),
        ("nonstraight", 8, 8, false, vec![(8,8)], vec![], false),
        ("slot overflow", usize::MAX, 1, true, vec![], vec![], false),
        ("write overflow", 8, 8, true, vec![(8,usize::MAX)], vec![], false),
        ("overflow before gap check", 8, 8, true, vec![(usize::MAX,1)], vec![], false),
        ("success before later overflow", 8, 8, true, vec![(usize::MAX,1),(8,8)], vec![], true),
        ("empty slot", 8, 0, true, vec![], vec![], true),
        ("read straddles empty slot", 8, 0, true, vec![], vec![(7,2)], false),
        ("read starts at empty slot", 8, 0, true, vec![], vec![(8,1)], true),
        ("empty slot with write gap", 8, 0, true, vec![(9,1)], vec![], true),
        ("empty slot with overflowing write", 8, 0, true, vec![(usize::MAX,1)], vec![], false),
    ];
    for (label, offset, size, straight, writes, reads, expected) in cases {
        let c = Coverage { straight, writes, reads, calls: vec![] };
        assert_eq!(c.complete(Slot { offset, size }, &p), expected, "{label}");
    }
}

#[test]
fn owned_coverage_checks_deferred_calls_before_empty_or_already_covered_success() {
    let p = program(8, &[8]);
    for size in [0,8] {
        for (label, calls) in [
            ("missing callee", vec![(1,0,vec![None])]),
            ("argument count", vec![(0,0,vec![])]),
            ("later missing callee", vec![(0,0,vec![None]),(1,0,vec![None])]),
        ] {
            let c = Coverage { straight: true, writes: vec![(0,8)], calls, ..Coverage::default() };
            assert!(!c.complete(Slot { offset: 0, size }, &p), "{label}, slot size {size}");
        }
    }
}

#[test]
fn owned_and_serialized_coverage_match_byte_cells_with_final_callee_abi() {
    let slot = Slot { offset: 8, size: 8 };
    let mut seed = 0x57b230af_u64;
    for _ in 0..1_000 {
        let mut next = |n: usize| { seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17; seed as usize % n };
        let mut p = program(0, &[0]);
        let mut c = Coverage { straight: true, ..Coverage::default() };
        for _ in 0..4 { c.writes.push((next(24),next(9))); }
        for _ in 0..2 { c.reads.push((next(24),next(9))); }
        for _ in 0..3 {
            let offset = next(24);
            let argument = if next(2)==0 { None } else { Some(next(24)) };
            c.calls.push((0,offset,vec![argument]));
        }
        // Capture knows callee identities, not their final result/argument byte
        // sizes. Resolve these only after the complete Program has been lowered.
        p.functions[0].result.size = next(9);
        p.functions[0].args[0].size = next(9);
        let mut cells = [false;32];
        let mut observed = false;
        for &(at,size) in &c.writes {
            for byte in at..at+size { cells[byte] = true; }
        }
        for &(at,size) in &c.reads {
            observed |= (at..at+size).any(|byte| (8..16).contains(&byte));
        }
        for (callee,at,arguments) in &c.calls {
            let f = &p.functions[*callee];
            for byte in *at..*at+f.result.size { cells[byte] = true; }
            for (argument,formal) in arguments.iter().zip(&f.args) {
                if let Some(at) = argument {
                    observed |= (*at..*at+formal.size).any(|byte| (8..16).contains(&byte));
                }
            }
        }
        let expected = !observed && cells[8..16].iter().all(|x| *x);
        let restored: Coverage = bincode::deserialize(&bincode::serialize(&c).unwrap()).unwrap();
        assert_eq!(c.complete(slot,&p),expected,"owned, rng state {seed:x}");
        assert_eq!(restored.complete(slot,&p),expected,"serialized, rng state {seed:x}");
    }
}

#[test]
fn emitted_copy_and_store_coverage_use_derived_local_addresses() {
    let p = program(0,&[]); let slot = Slot { offset: 16, size: 16 };
    let code = [Op::Local {dst:0,offset:16}, Op::Imm {dst:1,value:8},
        Op::Binary {dst:2,overflow:3,op:Binary::Add,a:0,b:1,bits:64,signed:false},
        Op::Store {address:0,src:4,size:8}, Op::Copy {dst:2,src:4,size:8}];
    assert!(coverage(&code,5).complete(slot,&p));
    assert!(!coverage(&code[..4],5).complete(slot,&p));
    let mut aliased = code.to_vec();
    aliased[2] = Op::Binary {dst:2,overflow:2,op:Binary::Add,a:0,b:1,bits:64,signed:false};
    assert!(!coverage(&aliased,5).complete(slot,&p));
}

#[test]
fn hidden_read_modify_write_preserves_incoming_bytes() {
    let slot = Slot { offset: 0, size: 8 }; let p = program(0,&[]);
    let code = [Op::Local {dst:0,offset:0}, Op::Load {dst:1,address:0,size:8}, Op::Store {address:0,src:1,size:8}];
    assert!(!coverage(&code,2).complete(slot,&p));
    let code = [Op::Local {dst:0,offset:0}, Op::Copy {dst:0,src:0,size:8}];
    assert!(!coverage(&code,1).complete(slot,&p));
}

#[test]
fn stale_registers_and_internal_branches_decline_complete_coverage() {
    let slot = Slot { offset: 0, size: 8 }; let p = program(0,&[]);
    let code = [Op::Local {dst:0,offset:0}, Op::Load {dst:0,address:1,size:8}, Op::Store {address:0,src:1,size:8}];
    assert!(!coverage(&code,2).complete(slot,&p));
    let code = [Op::Local {dst:0,offset:0}, Op::Jump {target:3}, Op::Store {address:0,src:1,size:8}];
    assert!(!coverage(&code,2).complete(slot,&p));
    let code = [Op::Local {dst:0,offset:0}, Op::Store {address:0,src:1,size:8}, Op::Jump {target:20}];
    assert!(coverage(&code,2).complete(slot,&p));
}

#[test]
fn call_results_use_actual_callee_layout_and_argument_reads() {
    let slot = Slot { offset: 0, size: 16 };
    let code = [Op::Local {dst:0,offset:0}, Op::Call {function:0,args:vec![],destination:0}, Op::Jump {target:8}];
    assert!(coverage(&code,1).complete(slot,&program(16,&[])));
    assert!(!coverage(&code,1).complete(slot,&program(8,&[])));
    assert!(!coverage(&code,1).complete(slot,&program(16,&[8])));
    let code = [Op::Local {dst:0,offset:0}, Op::Call {function:0,args:vec![0],destination:0}];
    assert!(!coverage(&code,1).complete(slot,&program(16,&[8])));
}

#[test]
fn indirect_results_and_constant_fills_preserve_byte_extents() {
    let slot=Slot{offset:0,size:16}; let p=program(0,&[]);
    let mut code=vec![Op::Local{dst:0,offset:0},Op::CallIndirect{callee:1,args:vec![],arg_sizes:vec![],destination:0,result_size:16}];
    assert!(coverage(&code,2).complete(slot,&p));
    code[1]=Op::CallIndirect{callee:1,args:vec![0],arg_sizes:vec![8],destination:0,result_size:16};
    assert!(!coverage(&code,2).complete(slot,&p));
    let code=[Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:16},Op::FillBytes{address:0,value:2,size:1}];
    assert!(coverage(&code,3).complete(slot,&p));
}

#[test]
fn address_escapes_partial_stores_and_dereferences_have_distinct_events() {
    let mut reasons = vec![None;4];
    let mut uses = ByteUses {reasons:&mut reasons,event:Event::default()};
    uses.access(0,PlaceContext::MutatingUse(MutatingUseContext::Store),true,false);
    uses.access(1,PlaceContext::MutatingUse(MutatingUseContext::Store),true,true);
    uses.access(2,PlaceContext::MutatingUse(MutatingUseContext::Drop),false,false);
    uses.access(3,PlaceContext::MutatingUse(MutatingUseContext::Call),false,false);
    assert_eq!(uses.event.reads,Set::from([0,1,2]));
    assert_eq!(uses.event.writes,Set::from([0]));
    assert_eq!(reasons,[None,None,Some("address_or_unsupported_context"),None]);
}

#[test]
fn normal_result_write_does_not_initialize_cleanup_path_even_at_shared_target() {
    let mut events=vec![vec![Event::default()],vec![Event{reads:Set::from([1]),writes:Set::new()}]];
    let mut successors=vec![vec![1,1],vec![]];
    let edge=result_edge(&mut events,&mut successors,0,1,1,false,Some(1));
    assert_eq!(successors[0],vec![edge,1]);
    assert_eq!(successors[edge],vec![1]);
    let mut eligibility=vec![];
    plan_with_eligibility(&[(8,8);2],vec![false,true],events.clone(),&successors,Some(&mut eligibility)).unwrap();
    assert!(!eligibility[1]); // cleanup can still read the initial bytes
    successors[0]=vec![edge];
    plan_with_eligibility(&[(8,8);2],vec![false,true],events,&successors,Some(&mut eligibility)).unwrap();
    assert!(eligibility[1]);
}

#[test]
fn colored_storage_matches_independent_bytes_for_16807_partial_and_dead_write_sequences() {
    // Operations specify actual byte reads/writes independently of Coverage.
    // Compare every observed byte in dedicated and hypothetically shared slots.
    let choices = [(1,0u8,255u8),(2,0,255),(1,255,15),(2,255,15),(1,255,0),(2,255,0),(1,0,0)];
    let mut shared = 0;
    for mut seed in 0..7usize.pow(5) {
        let mut operations=vec![]; let mut events=vec![];
        for _ in 0..5 {
            let (local,read,write)=choices[seed%7];seed/=7;
            operations.push((local,read,write));
            events.push(Event { reads: if read!=0 {Set::from([local])} else {Set::new()},
                writes: if write!=0 {Set::from([local])} else {Set::new()} });
        }
        let (slots,end)=plan(&[(8,8);3],vec![false,true,true],vec![events],&[vec![]]).unwrap();
        if slots[1].offset==slots[2].offset { shared+=1; }
        let mut original=[[0u8;8];3]; let mut colored=vec![0u8;end];
        for (pc,(local,read,write)) in operations.into_iter().enumerate() {
            for byte in 0..8 {
                if read&(1<<byte)!=0 { assert_eq!(original[local][byte],colored[slots[local].offset+byte]); }
            }
            for byte in 0..8 {
                if write&(1<<byte)!=0 {
                    let value=(pc*8+byte+1) as u8;
                    original[local][byte]=value;colored[slots[local].offset+byte]=value;
                }
            }
        }
    }
    assert!(shared>0);
}
