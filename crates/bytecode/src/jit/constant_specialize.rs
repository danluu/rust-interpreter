//! Experimental shared direct-call specializations. Original ABIs stay intact.
use crate::{Op,Program};
use std::collections::BTreeMap;

type Constant=(usize,usize,u128); // argument index, byte width, exact value
struct Site {caller:usize,pc:usize,known:Vec<Constant>}
const MAX_SCAN_OPERATIONS:usize=2_000_000;
const MAX_SITES:usize=65_536;
const MAX_CONSTANTS:usize=262_144;
const MAX_SIGNATURES:usize=65_536;
const MAX_SIGNATURE_WORK:usize=2_000_000;
const MAX_FOLD_WORK:usize=8_000_000;
const MAX_CLONES:usize=64;
const MAX_ADDED_OPERATIONS:usize=16_384;

#[derive(Default,serde::Serialize)]
struct Report {
    original_functions:usize,original_operations:usize,new_operations:usize,
    scanned_sites:usize,declined_functions:usize,signature_work:usize,signatures:usize,
    fold_work:usize,rewritten_calls:usize,added_operations:usize,
    clones:Vec<serde_json::Value>,decline:Option<&'static str>,
}
fn done(program:Program,report:Report)->Result<(Program,serde_json::Value),String> {
    crate::validate(&program)?;
    Ok((program,serde_json::to_value(report).map_err(|e|e.to_string())?))
}

fn signatures(known:&[Constant],mut visit:impl FnMut(Vec<Constant>)->Option<()>)->Option<()> {
    for (a,&first) in known.iter().enumerate() {
        visit(vec![first])?;
        for (b,&second) in known.iter().enumerate().skip(a+1) {
            visit(vec![first,second])?;
            for &third in known.iter().skip(b+1) {visit(vec![first,second,third])?;}
        }
    }
    Some(())
}

pub(super) fn specialize(mut program:Program)->Result<(Program,serde_json::Value),String> {
    crate::validate(&program)?;
    let original_functions=program.functions.len();
    let original_operations=program.functions.iter().map(|f|f.code.len()).sum::<usize>();
    let mut report=Report{original_functions,original_operations,new_operations:original_operations,..Report::default()};
    if original_operations>MAX_SCAN_OPERATIONS {
        report.decline=Some("program scan bound");return done(program,report);
    }
    let mut sites=Vec::new();let mut groups:BTreeMap<usize,Vec<usize>>=BTreeMap::new();let mut constants=0;
    for caller in 0..original_functions {
        let Some((calls,_))=super::constant_arguments::analyze(&program,caller,None) else {report.declined_functions+=1;continue;};
        for site in calls {
            report.scanned_sites+=1;
            constants+=site.arguments.len();
            if report.scanned_sites>MAX_SITES || constants>MAX_CONSTANTS {
                report.decline=Some("call fact bound");return done(program,report);
            }
            if site.arguments.is_empty() || site.arguments.len()>8 {continue;}
            let callee=&program.functions[site.callee];
            if callee.code.len()>512 || callee.args.len()>32 {continue;}
            let known=site.arguments.iter().map(|a|(a.index,a.bytes,a.value_bits)).collect();
            groups.entry(site.callee).or_default().push(sites.len());
            sites.push(Site{caller,pc:site.pc,known});
        }
    }
    let mut order:Vec<_>=groups.into_iter().collect();
    order.sort_unstable_by_key(|&(callee,ref members)|(std::cmp::Reverse(members.len()),program.functions[callee].code.len(),callee));
    let mut redirects=vec![None;sites.len()];let mut generated=Vec::new();let mut global=MAX_FOLD_WORK;
    let growth_limit=MAX_ADDED_OPERATIONS.min(original_operations/20);
    // No original body is rewritten until all clones are built. A generated
    // body therefore retains its original direct and indirect call targets.
    for (callee,members) in order {
        if members.len()<2 || generated.len()==MAX_CLONES || global==0 {continue;}
        let mut keys:BTreeMap<Vec<Constant>,Vec<usize>>=BTreeMap::new();
        let mut bounded=true;
        for &site in &members {
            if signatures(&sites[site].known,|key| {
                if report.signature_work==MAX_SIGNATURE_WORK {return None;}
                report.signature_work+=1;
                if !keys.contains_key(&key) {
                    if report.signatures==MAX_SIGNATURES {return None;}
                    report.signatures+=1;
                }
                keys.entry(key).or_default().push(site);Some(())
            }).is_none() {bounded=false;break;}
        }
        // Partial signature tables are not optimization evidence. Keep any
        // previously completed independent clones, but stop new candidates.
        if !bounded {report.decline=Some("signature work/storage bound");break;}
        let mut candidates:Vec<_>=keys.into_iter().filter(|(_,sites)|sites.len()>=2).collect();
        candidates.sort_unstable_by(|(a,asites),(b,bsites)|
            (bsites.len()*b.len()).cmp(&(asites.len()*a.len())).then_with(||a.cmp(b)));
        let mut accepted=0;let mut attempted=0;
        for (known,members) in candidates {
            if accepted==4 || attempted==8 || generated.len()==MAX_CLONES || global==0 {break;}
            let members:Vec<_>=members.into_iter().filter(|&site|redirects[site].is_none()).collect();
            if members.len()<2 {continue;}
            attempted+=1;
            let original=&program.functions[callee];
            let Some((mut body,fold))=super::constant_fold::seeded_function(&program,original,&known,&mut global) else {continue;};
            crate::control_flow::optimize_function(&mut body,true)?;
            let removed=original.code.len().saturating_sub(body.code.len());
            if removed<8 || removed*4<original.code.len() {continue;}
            if report.added_operations+body.code.len()>growth_limit {continue;}
            let clone=original_functions+generated.len();
            for &site in &members {redirects[site]=Some(clone);}
            report.clones.push(serde_json::json!({"original":callee,"clone":clone,"direct_sites":members.len(),
                "known_arguments":known.iter().map(|&(index,bytes,value)|serde_json::json!({"index":index,"bytes":bytes,"value":format!("0x{value:x}")})).collect::<Vec<_>>(),
                "old_operations":original.code.len(),"new_operations":body.code.len(),"fold":fold}));
            report.added_operations+=body.code.len();report.rewritten_calls+=members.len();
            generated.push(body);accepted+=1;
        }
    }
    report.fold_work=MAX_FOLD_WORK-global;
    program.functions.extend(generated);
    for (site,redirect) in sites.iter().zip(redirects) {
        let Some(target)=redirect else {continue;};
        let Op::Call{function,..}=&mut program.functions[site.caller].code[site.pc] else {return Err("specialization call site changed before publication".into());};
        *function=target;
    }
    report.new_operations+=report.added_operations;
    done(program,report)
}

#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
#[path="constant_specialize_tests.rs"]
mod tests;
