//! Offline entry-value provenance. This does not remove or execute any checks.
use crate::{Binary, Function, Op, Program, Reg};
use std::collections::BTreeMap;
use serde::Serialize;

const MAX_WORK: usize = 32_000_000;
const MAX_FUNCTION_WORK: usize = 4_000_000;
const MAX_ITEMS: usize = 65_536;
const MAX_SPAN: i64 = 4096;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
pub(super) enum Root { Register(Reg), FrameSlot(usize) }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Value { Frame(usize), Imm(u128), Pointer(Root, i64), Opaque }

#[derive(Default)]
struct State {
    registers: BTreeMap<Reg, Value>,
    slots: BTreeMap<usize, Value>,
    dirty: Vec<(usize, usize)>,
    all_dirty: bool,
    disjoint_mode: bool,
    protected_root: Option<Root>,
}

impl State {
    fn get(&self, r: Reg) -> Value {
        self.registers.get(&r).copied().unwrap_or(Value::Pointer(Root::Register(r), 0))
    }
    fn local(&self, r: Reg, size: usize, frame: usize) -> Option<usize> {
        match self.get(r) {
            Value::Frame(offset) if offset.checked_add(size).is_some_and(|end| end <= frame) => Some(offset),
            _ => None,
        }
    }
    fn load_slot(&self, offset: usize) -> Value {
        let value = if let Some(&value) = self.slots.get(&offset) { value }
        else if self.all_dirty || self.dirty.iter().any(|&(lo, hi)| lo < offset + 8 && offset < hi) {
            Value::Opaque
        } else { Value::Pointer(Root::FrameSlot(offset), 0) };
        // Only this root may inherit the frame-disjoint assumption. A different
        // root or a loaded constant must not silently acquire that dependency.
        match self.protected_root {
            Some(root) if !matches!(value,Value::Pointer(r,_) if r == root) => Value::Opaque,
            _ => value,
        }
    }
    fn write_address(&mut self, address: Reg, size: usize, value: Value, frame: usize) {
        let local = self.local(address,size,frame);
        if local.is_none() && self.disjoint_mode && (1..=128).contains(&size) {
            if let Value::Pointer(root,_) = self.get(address) {
                let protected = *self.protected_root.get_or_insert(root);
                if protected == root {
                    // CONDITIONAL: every modeled write through this root is
                    // within the group's range, which a future guard must prove
                    // disjoint from the whole active frame. No execution changes.
                    return;
                }
            }
        }
        self.write(local,size,value);
    }
    fn write(&mut self, offset: Option<usize>, size: usize, value: Value) {
        if size == 0 { return; }
        let Some(offset) = offset else {
            self.slots.clear(); self.all_dirty = true; self.dirty.clear(); return;
        };
        let end = offset.checked_add(size).expect("proved local extent");
        self.slots.retain(|&lo, _| lo >= end || offset >= lo + 8);
        if !self.all_dirty {
            if self.dirty.len() < 256 { self.dirty.push((offset, end)); }
            else { self.all_dirty = true; self.dirty.clear(); }
        }
        if size == 8 {
            if self.slots.len() == 64 { self.slots.clear(); }
            // Frame-pointer propagation through storage is a separate proposal.
            let value = match value { Value::Frame(_) => Value::Opaque,
                Value::Imm(v) => Value::Imm(v as u64 as u128), v => v };
            self.slots.insert(offset, value);
        }
    }
    fn transfer(&mut self, op: &Op, frame: usize) {
        let next = match *op {
            Op::Imm {dst,value} => vec![(dst,Value::Imm(value))],
            Op::Local {dst,offset} => vec![(dst,Value::Frame(offset))],
            Op::Load {dst,address,size} => vec![(dst, if size == 8 {
                self.local(address,8,frame).map_or(Value::Opaque, |offset| self.load_slot(offset))
            } else { Value::Opaque })],
            Op::Binary {dst,overflow,op,a,b,bits,signed} => {
                let result = match (self.get(a), self.get(b)) {
                    (Value::Imm(a),Value::Imm(b)) => crate::binary(op,a,b,bits,signed).ok()
                        .map(|(v,flag)| (Value::Imm(v),Value::Imm(flag as u128))),
                    (Value::Frame(offset),Value::Imm(add)) | (Value::Imm(add),Value::Frame(offset))
                        if matches!(op,Binary::Add) && bits == 64 && !signed => offset.checked_add(add as u64 as usize)
                            .filter(|&end| end <= frame).map(|end| (Value::Frame(end),Value::Imm(0))),
                    (Value::Pointer(root,offset),Value::Imm(add)) if bits == 64 && !signed
                        && matches!(op,Binary::Add|Binary::Sub) => {
                        let delta = add as u64 as i64;
                        let delta = if matches!(op,Binary::Sub) { delta.checked_neg() } else { Some(delta) };
                        delta.and_then(|delta| offset.checked_add(delta))
                            .filter(|offset| (-MAX_SPAN..=MAX_SPAN).contains(offset))
                            .map(|offset| (Value::Pointer(root,offset),Value::Opaque))
                    }
                    (Value::Imm(add),Value::Pointer(root,offset)) if matches!(op,Binary::Add) && bits == 64 && !signed =>
                        offset.checked_add(add as u64 as i64).filter(|offset| (-MAX_SPAN..=MAX_SPAN).contains(offset))
                            .map(|offset| (Value::Pointer(root,offset),Value::Opaque)),
                    _ => None,
                };
                result.map_or_else(Vec::new, |(value,flag)| vec![(dst,value),(overflow,flag)])
            }
            Op::Cast {dst,src,from:64,to:64,..} => vec![(dst, match self.get(src) {
                value @ Value::Pointer(..) => value, Value::Imm(v) => Value::Imm(v as u64 as u128), _ => Value::Opaque })],
            Op::Select {dst,condition,yes,no} => {
                let (a,b) = (self.get(yes),self.get(no));
                let value = match self.get(condition) { Value::Imm(v) => if v == 0 {b} else {a},
                    _ if a == b => a, _ => Value::Opaque };
                vec![(dst, if matches!(value,Value::Frame(_)) {Value::Opaque} else {value})]
            }
            _ => vec![],
        };
        // Read source values before any destination or aliased register changes.
        match *op {
            Op::Store {address,src,size} => self.write_address(address,size.into(),self.get(src),frame),
            Op::Copy {dst,src,size} => {
                let value = if size == 8 { self.local(src,8,frame).map_or(Value::Opaque,|o| self.load_slot(o)) }
                    else {Value::Opaque};
                self.write_address(dst,size,value,frame);
            }
            Op::Imm {..}|Op::Local {..}|Op::Load {..}|Op::Binary {..}|Op::Unary {..}|Op::Cast {..}
            |Op::Select {..}|Op::Jump {..}|Op::Switch {..}|Op::Assert {..}|Op::Return|Op::Trap {..}
            |Op::CompareBytes {..}|Op::FloatBinary {..}|Op::FloatUnary {..}|Op::FloatConvert {..} => {},
            // Unknown memory effects invalidate future slot loads, not values already in registers.
            _ => self.write(None,1,Value::Opaque),
        }
        crate::registers::visit_registers(op, |_| {}, |r| {self.registers.insert(r,Value::Opaque);});
        for (r,value) in next {self.registers.insert(r,value);}
    }
}

#[derive(Default)]
struct Group { sites: Vec<serde_json::Value>, accesses: usize, low: i64, high: i64, writes: usize }

const KEYS: [&str; 7] = ["fixed_addresses","local_addresses","unknown_addresses",
    "entry_pointer_addresses","all_group_addresses","best_group_addresses","best_group_redundant_checks"];

mod plan;
pub(super) use plan::{Plan, runtime_plan};
#[cfg(test)]
pub(super) use plan::Site;

fn function(f: &Function, intervals: &[(usize,usize,u64)], budget: &mut usize) -> Option<serde_json::Value> {
    function_with_mode(f,intervals,budget,false)
}

fn function_with_mode(f: &Function, intervals: &[(usize,usize,u64)], budget: &mut usize,
    disjoint: bool) -> Option<serde_json::Value> {
    if f.code.len() > MAX_ITEMS || f.registers > MAX_ITEMS {return None;}
    let mut totals=[0u64;7];let mut conditional=[0u64;2];let mut groups=vec![];
    for &(start,end,hits) in intervals {
        let mut state=State {disjoint_mode:disjoint,..State::default()};let mut by_root=BTreeMap::<Root,Group>::new();
        for pc in start..end {
            let op=&f.code[pc];
            let mut operands=1usize;
            crate::registers::visit_registers(op, |_| operands+=1, |_| {});
            *budget=budget.checked_sub(operands + state.dirty.len() + state.slots.len() + 1)?;
            let accesses=match *op {
                Op::Load {address,size,..} if size != 0 => vec![(address,size as usize,false)],
                Op::Store {address,size,..} if size != 0 => vec![(address,size as usize,true)],
                Op::Copy {dst,src,size} if size != 0 && size <= 128 => vec![(src,size,false),(dst,size,true)],
                _ => vec![],
            };
            for (r,size,write) in accesses {
                totals[0]=totals[0].checked_add(hits)?;
                if state.local(r,size,f.frame_size).is_some() {totals[1]=totals[1].checked_add(hits)?;continue;}
                totals[2]=totals[2].checked_add(hits)?;
                if let Value::Pointer(root,offset)=state.get(r) {
                    totals[3]=totals[3].checked_add(hits)?;
                    let group=by_root.entry(root).or_default();
                    let high=offset.checked_add(size as i64)?;
                    if group.accesses == 0 {group.low=offset;group.high=high;}
                    else {group.low=group.low.min(offset);group.high=group.high.max(high);}
                    group.writes+=usize::from(write);
                    group.accesses+=1;
                    if group.sites.len() < 64 {
                        group.sites.push(serde_json::json!({"pc":pc,"register":r,"offset":offset,"size":size,"write":write}));
                    }
                }
            }
            state.transfer(op,f.frame_size);
        }
        let mut eligible:Vec<_>=by_root.into_iter().filter(|(_,g)|g.accesses>=3 && g.high-g.low<=MAX_SPAN).collect();
        eligible.sort_by_key(|(root,g)|(std::cmp::Reverse(g.accesses),g.high-g.low,*root));
        for (_,g) in &eligible {totals[4]=totals[4].checked_add(hits.checked_mul(g.accesses as u64)?)?;}
        if let Some((root,g))=eligible.first() {
            let count=g.accesses as u64;
            totals[5]=totals[5].checked_add(hits.checked_mul(count)?)?;
            totals[6]=totals[6].checked_add(hits.checked_mul(count-1)?)?;
            let mut group=serde_json::json!({"start":start,"end":end,"hits":hits,"root":root,
                "minimum_offset":g.low,"maximum_end":g.high,"span":g.high-g.low,"writes":g.writes,
                "accesses":count,"conditional_redundant_checks":hits.checked_mul(count-1)?,"sites":g.sites,
                "sites_truncated":g.accesses>g.sites.len()});
            if disjoint {
                let needed=state.protected_root==Some(*root);
                group["requires_frame_disjoint"]=needed.into();
                if needed {
                    conditional[0]=conditional[0].checked_add(hits.checked_mul(count)?)?;
                    conditional[1]=conditional[1].checked_add(hits.checked_mul(count-1)?)?;
                }
            }
            groups.push(group);
        }
    }
    groups.sort_by_key(|g|std::cmp::Reverse(g["conditional_redundant_checks"].as_u64().unwrap()));groups.truncate(10);
    let mut counts:serde_json::Map<_,_>=KEYS.into_iter().zip(totals.map(serde_json::Value::from)).map(|(k,v)|(k.into(),v)).collect();
    if disjoint {
        counts.insert("frame_disjoint_group_addresses".into(),conditional[0].into());
        counts.insert("frame_disjoint_redundant_checks".into(),conditional[1].into());
    }
    Some(serde_json::json!({"counts":counts,"top_groups":groups}))
}

pub(super) fn census(program:&Program,bytes:&[u8])->Result<serde_json::Value,String> {
    census_with_mode(program,bytes,false)
}

pub(super) fn disjoint_census(program:&Program,bytes:&[u8])->Result<serde_json::Value,String> {
    census_with_mode(program,bytes,true)
}

fn census_with_mode(program:&Program,bytes:&[u8],disjoint:bool)->Result<serde_json::Value,String> {
    crate::validate(program)?;
    let profile=super::register_width_profile::parse(program,bytes)?;
    let mut remaining=MAX_WORK;let mut rows=vec![];let mut declined=vec![];
    for (id,(f,p)) in program.functions.iter().zip(&profile.functions).enumerate() {
        let intervals:Vec<_>=p.intervals().collect();if intervals.is_empty(){continue;}
        let allowance=remaining.min(MAX_FUNCTION_WORK);let mut budget=allowance;
        let result=if disjoint {function_with_mode(f,&intervals,&mut budget,true)} else {function(f,&intervals,&mut budget)};
        remaining-=allowance-budget;
        if let Some(mut row)=result {row["function"]=id.into();row["name"]=f.name.clone().into();rows.push(row);}
        else {declined.push(serde_json::json!({"function":id,"reason":"analysis or counter bound","opportunities":null}));}
    }
    let mut totals=serde_json::Map::new();
    let mut keys=KEYS.to_vec();
    if disjoint {keys.extend(["frame_disjoint_group_addresses","frame_disjoint_redundant_checks"]);}
    for key in keys {
        let total=rows.iter().try_fold(0u64,|sum,r|sum.checked_add(r["counts"][key].as_u64().unwrap())).ok_or("range-group count overflow")?;
        totals.insert(key.into(),total.into());
    }
    rows.sort_by_key(|r|std::cmp::Reverse(r["counts"]["best_group_redundant_checks"].as_u64().unwrap()));
    let mut result=serde_json::json!({"schema_version":1,"status":"counted","counts":totals,"functions":rows,
        "declined_functions":declined,"analysis_work":MAX_WORK-remaining,"guest_instructions_executed":0,"emitter_changed":false,
        "scope":"Conditional entry-root groups in exact native intervals, at least three fixed accesses and at most4KiB extent. Best one group per interval reported separately. Not an implemented guard, measured guard hit rate, emitted saving or latency estimate."});
    if disjoint {
        result["frame_disjoint_assumption"]="At most one entry root per interval may preserve its frame-slot identity across its modeled writes, only if the entire guarded range is disjoint from the active frame. Other roots and unmodeled effects invalidate slots. This is a conditional census, not a proof the guard passes.".into();
    }
    Ok(result)
}

#[cfg(test)]
mod tests;
