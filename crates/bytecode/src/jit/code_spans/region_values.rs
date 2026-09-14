//! Bounded, test-only opportunity census. This is not a lowering proof or emitter.
use super::*;
use serde_json::{Value, json};

#[derive(Clone, Copy)]
enum Address { Local(usize), Imm(u128) }

fn local(facts: &BTreeMap<Reg, Address>, reg: Reg, size: usize, frame: usize) -> Option<usize> {
    match facts.get(&reg) {
        Some(Address::Local(offset)) if offset.checked_add(size).is_some_and(|e| e <= frame) => Some(*offset),
        _ => None,
    }
}

#[derive(Default, Debug, serde::Serialize)]
struct Access {
    pc: usize,
    read_bytes: usize,
    available_read_bytes: usize,
    written_bytes: usize,
    superseded_write_bytes: usize,
}

fn analyze(f: &Function, start: usize, end: usize) -> (Vec<Access>, usize) {
    assert!(start < end && end <= f.code.len() && end-start <= 1024);
    let mut facts = BTreeMap::new();
    // Presence means captured within this segment. A writer is retained so a
    // later overwrite can count bytes that need not reach the final frame.
    let mut bytes: BTreeMap<usize, Option<usize>> = BTreeMap::new();
    let mut rows: Vec<Access> = vec![];
    let mut barriers = 0;
    for pc in start..end {
        let op = &f.code[pc];
        let mut next = vec![];
        let mut reads = None;
        let mut writes = None;
        let mut barrier = false;
        match *op {
            Op::Local {dst,offset} => next.push((dst,Address::Local(offset))),
            Op::Imm {dst,value} => next.push((dst,Address::Imm(value))),
            Op::Binary {dst,overflow,op,a,b,bits,signed} => {
                let value = match (facts.get(&a).copied(),facts.get(&b).copied()) {
                    (Some(Address::Imm(a)),Some(Address::Imm(b))) => crate::binary(op,a,b,bits,signed)
                        .ok().map(|(v,o)|(Address::Imm(v),o)),
                    (Some(Address::Local(offset)),Some(Address::Imm(add))) |
                    (Some(Address::Imm(add)),Some(Address::Local(offset)))
                        if matches!(op,crate::Binary::Add) && bits==64 && !signed =>
                        offset.checked_add(add as u64 as usize).filter(|&e|e<=f.frame_size)
                            .map(|e|(Address::Local(e),false)),
                    _ => None,
                };
                if let Some((v,o))=value {next.extend([(dst,v),(overflow,Address::Imm(o as u128))]);}
                // A possibly failing op requires prior frame publication.
                barrier = matches!(op,crate::Binary::Div|crate::Binary::Rem);
            }
            Op::Unary {..} | Op::Cast {..} | Op::Select {..} => {},
            Op::Load {address,size,..} => {
                reads=local(&facts,address,size.into(),f.frame_size).map(|o|(o,usize::from(size)));
                barrier=reads.is_none();
            }
            Op::Store {address,size,..} => {
                writes=local(&facts,address,size.into(),f.frame_size).map(|o|(o,usize::from(size)));
                barrier=writes.is_none();
            }
            Op::Copy {dst,src,size} if size<=16 => {
                reads=local(&facts,src,size,f.frame_size).map(|o|(o,size));
                writes=local(&facts,dst,size,f.frame_size).map(|o|(o,size));
                barrier=reads.is_none() || writes.is_none();
            }
            // Unknown memory, assertions, transfers and every unreviewed opcode
            // end the segment. No alias/disjointness or failure guess is made.
            _ => barrier=true,
        }
        crate::registers::visit_registers(op, |_|{}, |r| {facts.remove(&r);});
        for (r,v) in next {facts.insert(r,v);}
        if barrier {bytes.clear();barriers+=1;continue;}
        if reads.is_none() && writes.is_none() {continue;}
        let mut row=Access {pc,..Access::default()};
        // Read before write, including overlapping copies.
        if let Some((offset,size))=reads {
            row.read_bytes=size;
            for byte in offset..offset+size {
                if bytes.contains_key(&byte) {row.available_read_bytes+=1;}
                else {bytes.insert(byte,None);}
            }
        }
        if let Some((offset,size))=writes {
            row.written_bytes=size;
            for byte in offset..offset+size {
                if let Some(Some(writer))=bytes.insert(byte,Some(rows.len())) {
                    rows[writer].superseded_write_bytes+=1;
                }
            }
        }
        rows.push(row);
        assert!(bytes.len()<=16*1024 && rows.len()<=1024);
    }
    (rows,barriers)
}

pub(super) fn observe(f: &Function, spans: &[super::super::memory_parts::Span]) -> Value {
    let regions: BTreeSet<_>=spans.iter().map(|s|(s.region_start,s.region_end)).collect();
    let mut output=vec![];
    for (start,end) in regions {
        let (rows,barriers)=analyze(f,start,end);
        output.push(json!({"start":start,"end":end,"barriers":barriers,"accesses":rows}));
    }
    json!(output)
}

#[cfg(test)]
fn fixture(code:Vec<Op>) -> Function {
    Function {name:"region census".into(),frame_size:64,frame_align:16,registers:8,
        args:vec![],result:crate::Slot {offset:0,size:0},code}
}

#[test]
fn byte_accounting_covers_partial_reads_overwrites_and_copy_overlap() {
    let f=fixture(vec![Op::Local {dst:0,offset:0},Op::Local {dst:1,offset:4},
        Op::Store {address:0,src:2,size:8},Op::Load {dst:3,address:1,size:8},
        Op::Copy {dst:1,src:0,size:8},Op::Store {address:0,src:2,size:8}]);
    let (r,b)=analyze(&f,0,f.code.len());assert_eq!(b,0);
    assert_eq!(r.iter().map(|r|r.available_read_bytes).collect::<Vec<_>>(),[0,4,8,0]);
    assert_eq!(r.iter().map(|r|r.superseded_write_bytes).collect::<Vec<_>>(),[8,0,4,0]);
    assert_eq!(r.iter().map(|r|r.written_bytes-r.superseded_write_bytes).sum::<usize>(),12);
}

#[test]
fn unknown_memory_faults_and_region_entries_end_value_availability() {
    for barrier in [Op::Store {address:7,src:2,size:8},Op::Load {dst:2,address:7,size:8},
        Op::Assert {value:2,expected:true,message:"fault".into()},
        Op::Binary {dst:2,overflow:3,op:crate::Binary::Div,a:2,b:3,bits:64,signed:false}] {
        let f=fixture(vec![Op::Local {dst:0,offset:0},Op::Store {address:0,src:2,size:8},
            barrier,Op::Load {dst:3,address:0,size:8},Op::Store {address:0,src:2,size:8}]);
        let (r,b)=analyze(&f,0,5);assert_eq!(b,1);
        assert_eq!(r[0].superseded_write_bytes,0);assert_eq!(r[1].available_read_bytes,0);
        let (r,b)=analyze(&f,3,5);assert!(r.is_empty());assert_eq!(b,2);
    }
}

#[test]
fn aliased_outputs_offsets_and_frame_extents_are_conservative() {
    let f=fixture(vec![Op::Local {dst:0,offset:56},Op::Imm {dst:1,value:8},
        Op::Store {address:0,src:2,size:8},
        Op::Binary {dst:0,overflow:0,op:crate::Binary::Add,a:0,b:1,bits:64,signed:false},
        Op::Load {dst:3,address:0,size:8},Op::Local {dst:0,offset:60},
        Op::Load {dst:3,address:0,size:8}]);
    let (r,b)=analyze(&f,0,7);assert_eq!(r.len(),1);assert_eq!(b,2);
    let f=fixture(vec![Op::Local {dst:0,offset:0},Op::Store {address:0,src:2,size:8},
        Op::Load {dst:0,address:0,size:8},Op::Load {dst:3,address:0,size:8}]);
    let (r,b)=analyze(&f,0,4);assert_eq!(r[1].available_read_bytes,8);assert_eq!(b,1);
}
