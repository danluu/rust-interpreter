//! Bounded forward-edge credit certificates. No executable code is emitted here.
use super::*;

const MAX_PCS: usize = 65_536;
const MAX_EDGES: usize = 262_144;
const MAX_CREDIT: usize = 4096;

#[derive(Debug)]
struct Region { start: usize, end: usize, successors: Vec<usize>, guarded: bool }

#[derive(Debug)]
pub(super) struct Credit {
    pub steps: usize,
    pub suffix: usize,
    pub fast_successors: Vec<usize>,
}

#[derive(Debug, PartialEq, Eq)]
pub(super) struct Edge {
    pub refund: usize,
    pub fast: bool,
    pub native_target: bool,
}

pub(super) struct Prepared {
    ranges: BTreeMap<usize, Option<range_groups::Plan>>,
    credits: BTreeMap<usize, Credit>,
    transitions: BTreeSet<usize>,
}

impl Prepared {
    pub fn credit(&self, start: usize) -> &Credit {
        self.credits.get(&start).expect("certified ordinary region")
    }
    pub fn take_range(&mut self, start: usize) -> Option<range_groups::Plan> {
        self.ranges.remove(&start).expect("range plan consumed exactly once")
    }
    pub fn edge(&self, source: usize, target: usize) -> Edge {
        let from=self.credit(source);
        let fast=from.fast_successors.contains(&target);
        let retained=if fast { self.credit(target).steps } else { 0 };
        let refund=from.suffix.checked_sub(retained).expect("credit edge certificate");
        assert!(refund<MAX_CREDIT);
        Edge {refund,fast,native_target:self.credits.contains_key(&target)||self.transitions.contains(&target)}
    }
}

/// Mirror ordinary-region discovery, including unsupported/call gaps and size
/// splits. All new shape checks finish before consuming any range proof work.
fn discover(f: &Function, starts: &[bool], native: &impl Fn(usize)->bool) -> Option<Vec<Region>> {
    if f.code.is_empty() || f.code.len()>MAX_PCS || starts.len()!=f.code.len() || !starts[0] {return None;}
    let mut regions=vec![];let mut pc=0;let mut edges=0usize;
    while pc<f.code.len() {
        let start=pc;
        while pc<f.code.len() && pc-start<1024 && (pc==start||!starts[pc]) && native(pc) {pc+=1;}
        if pc==start {pc+=1;continue;}
        let mut successors=match &f.code[pc-1] {
            Op::Jump{target}=>vec![*target],
            Op::Switch{cases,otherwise,..}=>{
                if cases.len()>16 {return None;}
                // Keep first-match semantics for duplicate switch values.
                let mut values=BTreeSet::new();let mut next=vec![*otherwise];
                for &(value,target) in cases {if values.insert(value) {next.push(target);}}
                next.sort_unstable();next.dedup();next
            },
            _=>vec![pc],
        };
        if successors.iter().any(|&target|target>=f.code.len()) {return None;}
        successors.sort_unstable();successors.dedup();
        edges=edges.checked_add(successors.len())?;
        if edges>MAX_EDGES {return None;}
        regions.push(Region{start,end:pc,successors,guarded:false});
    }
    Some(regions)
}

fn certify(regions: &[Region]) -> BTreeMap<usize,Credit> {
    let guarded:BTreeMap<_,_>=regions.iter().map(|r|(r.start,r.guarded)).collect();
    let mut credits=BTreeMap::<usize,Credit>::new();
    for r in regions.iter().rev() {
        let cost=r.end-r.start;
        let mut fast:Vec<_>=r.successors.iter().copied().filter(|&t|t>r.start && guarded.get(&t)==Some(&false)).collect();
        let mut steps=cost+fast.iter().map(|t|credits[t].steps).max().unwrap_or(0);
        if steps>MAX_CREDIT {fast.clear();steps=cost;}
        assert!((1..=MAX_CREDIT).contains(&steps));
        credits.insert(r.start,Credit{steps,suffix:steps-cost,fast_successors:fast});
    }
    for r in regions {
        for &target in &credits[&r.start].fast_successors {
            assert!(target>r.start && !guarded[&target]);
            assert!(credits[&r.start].suffix>=credits[&target].steps);
        }
    }
    credits
}

pub(super) fn prepare(f: &Function, starts: &[bool], native: impl Fn(usize)->bool,
    range_work: &mut usize) -> Option<Prepared> {
    let mut regions=discover(f,starts,&native)?;
    let mut ranges=BTreeMap::new();
    // This order and this single consumption match the original emitter exactly.
    for region in &mut regions {
        let range=range_groups::runtime_plan(f,region.start,region.end,range_work);
        region.guarded=range.is_some();ranges.insert(region.start,range);
    }
    let credits=certify(&regions);
    let transitions=f.code.iter().enumerate().filter_map(|(pc,op)|
        matches!(op,Op::Call{..}|Op::Return).then_some(pc)).collect();
    Some(Prepared{ranges,credits,transitions})
}

#[cfg(test)]
mod tests {
    use super::*;
    fn region(start:usize,cost:usize,next:&[usize],guarded:bool)->Region {
        Region{start,end:start+cost,successors:next.to_vec(),guarded}
    }
    fn prepared(regions:Vec<Region>)->Prepared {
        Prepared{ranges:BTreeMap::new(),credits:certify(&regions),transitions:BTreeSet::from([99])}
    }
    fn function(code:Vec<Op>)->Function {
        Function{name:"budget credit".into(),frame_size:64,frame_align:16,registers:4,
            args:vec![],result:crate::Slot{offset:0,size:8},code}
    }
    #[test]
    fn unequal_paths_have_exact_edge_refunds_and_cut_targets() {
        let p=prepared(vec![region(0,1,&[1,5],false),region(1,2,&[10],false),
            region(5,4,&[10],false),region(10,2,&[99],false)]);
        assert_eq!(p.credit(0).steps,7);
        assert_eq!(p.edge(0,1),Edge{refund:2,fast:true,native_target:true});
        assert_eq!(p.edge(0,5),Edge{refund:0,fast:true,native_target:true});
        assert_eq!(p.edge(0,99),Edge{refund:6,fast:false,native_target:true});
        assert_eq!(p.edge(0,98),Edge{refund:6,fast:false,native_target:false});
    }
    #[test]
    fn backward_and_guarded_edges_never_receive_credit() {
        let p=prepared(vec![region(0,2,&[0,2,4],false),region(2,2,&[4],true),region(4,2,&[0],false)]);
        assert_eq!(p.credit(0).fast_successors,vec![4]);
        assert_eq!(p.edge(0,0),Edge{refund:2,fast:false,native_target:true});
        assert_eq!(p.edge(0,2),Edge{refund:2,fast:false,native_target:true});
        assert_eq!(p.credit(4).suffix,0);
    }
    #[test]
    fn cap_cuts_a_chain_without_changing_region_cost() {
        let rows:Vec<_>=(0..7).map(|i|region(i*1024,1024,&[if i==6 {99} else {(i+1)*1024}],false)).collect();
        let p=prepared(rows);assert_eq!(p.credit(2048).steps,1024);assert_eq!(p.credit(3072).steps,4096);
        assert!(p.credit(2048).fast_successors.is_empty());
    }
    #[test]
    fn discovery_keeps_splits_calls_and_switch_first_match() {
        let mut code=vec![Op::Imm{dst:0,value:1};1026];
        code.extend([Op::Call{function:0,args:vec![],destination:0},
            Op::Switch{value:0,cases:vec![(1,0),(1,1026)],otherwise:0},Op::Return]);
        let f=function(code);let mut starts=vec![false;f.code.len()];starts[0]=true;starts[1027]=true;starts[1028]=true;
        let rows=discover(&f,&starts,&|pc|!matches!(f.code[pc],Op::Call{..}|Op::Return)).unwrap();
        assert_eq!(rows.iter().map(|r|(r.start,r.end)).collect::<Vec<_>>(),vec![(0,1024),(1024,1026),(1027,1028)]);
        assert_eq!(rows[2].successors,vec![0]);
    }
    #[test]
    fn discovery_decline_does_not_consume_range_budget() {
        let f=function(vec![Op::Return]);let mut budget=17;
        assert!(prepare(&f,&[],|_|false,&mut budget).is_none());assert_eq!(budget,17);
        let f=function(vec![Op::Imm{dst:0,value:0};MAX_PCS+1]);
        assert!(prepare(&f,&vec![true;f.code.len()],|_|true,&mut budget).is_none());assert_eq!(budget,17);
    }
    #[test]
    fn range_plans_are_computed_in_the_original_order_once() {
        let f=function(vec![Op::Imm{dst:0,value:0},Op::Jump{target:2},Op::Local{dst:1,offset:0},Op::Return]);
        let starts=[true,false,true,true];let native=|pc|pc!=3;
        let mut expected=4_000_000;let a=range_groups::runtime_plan(&f,0,2,&mut expected);let b=range_groups::runtime_plan(&f,2,3,&mut expected);
        let mut actual=4_000_000;let mut p=prepare(&f,&starts,native,&mut actual).unwrap();
        assert_eq!(actual,expected);assert_eq!(format!("{:?}",p.take_range(0)),format!("{a:?}"));
        assert_eq!(format!("{:?}",p.take_range(2)),format!("{b:?}"));assert!(p.ranges.is_empty());
    }
}
