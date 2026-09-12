//! Eliminate direct calls through wrappers that only forward their arguments.
//! Function IDs, entry points, layouts, and indirect-call handles remain stable.
use crate::{Op, Program, Slot};

#[derive(Debug, Default, PartialEq, Eq)]
pub struct ForwardingReport {
    pub wrappers: usize,
    pub retargeted_calls: usize,
    pub longest_chain: usize,
}

fn disjoint(slots: impl Iterator<Item = Slot>) -> bool {
    let mut ranges: Vec<_> = slots
        .filter(|s| s.size != 0)
        .map(|s| (s.offset, s.offset + s.size))
        .collect();
    ranges.sort_unstable();
    ranges.windows(2).all(|pair| pair[0].1 <= pair[1].0)
}

/// Called after validation, so registers, slots, and direct targets are bounded.
fn forwarded_target(program: &Program, id: usize) -> Option<usize> {
    let wrapper = &program.functions[id];
    let [
        prefix @ ..,
        Op::Call {
            function,
            args,
            destination,
        },
        Op::Return,
    ] = wrapper.code.as_slice()
    else {
        return None;
    };
    if !prefix.iter().all(|op| matches!(op, Op::Local { .. }))
        || !disjoint(wrapper.args.iter().copied().chain([wrapper.result]))
    {
        return None;
    }
    let callee = &program.functions[*function];
    if wrapper.args.len() != args.len()
        || wrapper.args.len() != callee.args.len()
        || wrapper.result.size != callee.result.size
        || wrapper
            .args
            .iter()
            .zip(&callee.args)
            .any(|(a, b)| a.size != b.size)
    {
        return None;
    }
    // Track only actually materialized Local addresses. A register's initial
    // zero value is not an address proof. Last definitions win, even with aliases.
    let mut locals = std::collections::BTreeMap::new();
    for op in prefix {
        if let Op::Local { dst, offset } = op {
            locals.insert(*dst, *offset);
        }
    }
    if locals.get(destination) != Some(&wrapper.result.offset)
        || args
            .iter()
            .zip(&wrapper.args)
            .any(|(reg, slot)| locals.get(reg) != Some(&slot.offset))
    {
        return None;
    }
    Some(*function)
}

/// Retarget direct calls through proven identity-forwarding chains. No bytecode,
/// register or frame is added. As with inlining, budgets count the resulting
/// artifact; removing a call can remove its instruction and frame costs.
pub fn eliminate_direct_forwarders(program: &mut Program) -> Result<ForwardingReport, String> {
    crate::validate(program)?;
    let next: Vec<_> = (0..program.functions.len())
        .map(|id| forwarded_target(program, id))
        .collect();
    let mut report = ForwardingReport {
        wrappers: next.iter().flatten().count(),
        ..Default::default()
    };
    // This is a functional graph. Iterative tri-color traversal handles long
    // chains in linear time without host recursion. Cycles and all paths into
    // them stay unchanged instead of bypassing recursive calls arbitrarily.
    let mut colors = vec![0u8; next.len()];
    let mut resolved = vec![None; next.len()];
    let mut lengths = vec![0usize; next.len()];
    let mut path = Vec::new();
    for start in 0..next.len() {
        if colors[start] != 0 {
            continue;
        }
        path.clear();
        let mut current = start;
        let (target, mut length) = loop {
            if colors[current] == 2 {
                break (resolved[current], lengths[current]);
            }
            if colors[current] == 1 {
                break (None, 0);
            }
            let Some(successor) = next[current] else {
                colors[current] = 2;
                resolved[current] = Some(current);
                break (Some(current), 0);
            };
            colors[current] = 1;
            path.push(current);
            current = successor;
        };
        for id in path.iter().rev().copied() {
            colors[id] = 2;
            resolved[id] = target;
            if target.is_some() {
                length += 1;
                lengths[id] = length;
                report.longest_chain = report.longest_chain.max(length);
            }
        }
    }
    for function in &mut program.functions {
        for op in &mut function.code {
            if let Op::Call { function, .. } = op {
                if let Some(target) = resolved[*function] {
                    if *function != target {
                        *function = target;
                        report.retargeted_calls += 1;
                    }
                }
            }
        }
    }
    Ok(report)
}
