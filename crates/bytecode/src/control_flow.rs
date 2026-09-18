//! Export-time jump threading, unreachable-code removal and deterministic block layout.
use crate::{Op, Program, remove_fallthrough_jumps};
use serde::Serialize;
#[cfg(test)]
#[path = "control_flow_tests.rs"]
mod tests;

#[derive(Debug, Default, Serialize)]
pub struct FunctionControlFlowReport {
    pub function: usize,
    pub old_operations: usize,
    pub new_operations: usize,
    pub redirected_edges: usize,
    pub unreachable_operations: usize,
    pub inserted_jumps: usize,
    pub removed_fallthrough_jumps: usize,
    pub layout_rejected_for_growth: bool,
    pub rejected_register_clearing: bool,
    pub skipped_terminal_fallthrough: bool,
    pub register_zeroes_before: bool,
    pub register_zeroes_proposed: bool,
}

#[derive(Debug, Default, Serialize)]
pub struct ControlFlowReport {
    pub functions: Vec<FunctionControlFlowReport>,
    pub old_operations: usize,
    pub new_operations: usize,
}

/// Simplify control flow without changing function IDs, layouts, registers or
/// data. Jump-only cycles remain loops; switch case precedence and every original
/// fallthrough are preserved. Instruction budgets count the resulting artifact.
/// Layout falls back to threading if code would grow. A transformation that would
/// introduce whole-function register clearing is rejected. The VM never applies
/// this pass implicitly to hand-constructed programs.
pub fn optimize_control_flow(program: &mut Program) -> Result<ControlFlowReport, String> {
    optimize(program, true)
}

/// Run the same validated CFG pass while retaining only operation totals.
/// The returned functions vector is empty. An already straight-line body is
/// unchanged by this pass, so summary mode needs neither reconstruction nor
/// register-initialization proofs for that body. Transformed bodies retain the
/// existing before/after proofs and rollback checks.
pub fn optimize_control_flow_summary(program: &mut Program) -> Result<ControlFlowReport, String> {
    optimize_impl(program, true, false)
}

pub(crate) fn optimize(program: &mut Program, layout: bool) -> Result<ControlFlowReport, String> {
    optimize_impl(program, layout, true)
}

fn optimize_impl(
    program: &mut Program,
    layout: bool,
    retain_details: bool,
) -> Result<ControlFlowReport, String> {
    crate::validate(program)?;
    let mut report = ControlFlowReport::default();
    for (id, function) in program.functions.iter_mut().enumerate() {
        // Complete Program validation has already checked all instructions,
        // including unreachable ones. With no interior terminal and a final
        // Return/Trap, CFG threading, layout and jump removal are the identity.
        if !retain_details && function.code.split_last().is_some_and(|(last, prefix)| {
            matches!(last, Op::Return | Op::Trap { .. })
                && prefix.iter().all(|op| !terminal(op))
        }) {
            report.old_operations += function.code.len();
            report.new_operations += function.code.len();
            continue;
        }
        let before = crate::registers::needs_initial_zeroes(function);
        let (code, mut part) = transform_code(&function.code, layout)?;
        let original = std::mem::replace(&mut function.code, code);
        let after = crate::registers::needs_initial_zeroes(function);
        if !before && after {
            function.code = original;
            part = FunctionControlFlowReport {
                old_operations: function.code.len(),
                new_operations: function.code.len(),
                rejected_register_clearing: true,
                ..Default::default()
            };
        }
        part.function = id;
        part.register_zeroes_before = before;
        part.register_zeroes_proposed = after;
        report.old_operations += part.old_operations;
        report.new_operations += function.code.len();
        if retain_details {
            report.functions.push(part);
        }
    }
    crate::validate(program)?;
    Ok(report)
}

fn terminal(op: &Op) -> bool {
    matches!(
        op,
        Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. }
    )
}

/// Resolve jump-only paths without arbitrarily choosing a representative of a
/// cycle. Input branches are already validated by transform_code.
fn jump_targets(code: &[Op]) -> Vec<Option<usize>> {
    let mut color = vec![0u8; code.len()];
    let mut resolved = vec![None; code.len()];
    let mut lengths = vec![0usize; code.len()];
    let mut path = Vec::new();
    for start in 0..code.len() {
        if color[start] != 0 {
            continue;
        }
        path.clear();
        let mut pc = start;
        let (target, mut length) = loop {
            if color[pc] == 2 {
                break (resolved[pc], lengths[pc]);
            }
            if color[pc] == 1 {
                break (None, 0);
            }
            let Op::Jump { target } = code[pc] else {
                color[pc] = 2;
                resolved[pc] = Some(pc);
                break (Some(pc), 0);
            };
            color[pc] = 1;
            path.push(pc);
            pc = target;
        };
        for pc in path.iter().rev().copied() {
            resolved[pc] = target;
            if target.is_some() {
                length += 1;
                lengths[pc] = length;
            }
            color[pc] = 2;
        }
    }
    // A decreasing distance certifies that every redirected path reaches its
    // terminal through jumps only. Cycles cannot satisfy these local equations.
    for (pc, target) in resolved.iter().enumerate() {
        if let Some(target) = target {
            assert!(!matches!(code[*target], Op::Jump { .. }));
            if let Op::Jump { target: next } = code[pc] {
                assert_eq!(resolved[next], Some(*target));
                assert_eq!(lengths[next].checked_add(1), Some(lengths[pc]));
            } else {
                assert_eq!((*target, lengths[pc]), (pc, 0));
            }
        }
    }
    resolved
}

fn transform_code(
    original: &[Op],
    layout: bool,
) -> Result<(Vec<Op>, FunctionControlFlowReport), String> {
    if original.is_empty() {
        return Err("empty body".into());
    }
    for op in original {
        let check = |pc: usize| {
            if pc < original.len() {
                Ok(())
            } else {
                Err("invalid CFG target".to_owned())
            }
        };
        match op {
            Op::Jump { target } => check(*target)?,
            Op::Switch {
                cases, otherwise, ..
            } => {
                check(*otherwise)?;
                for (_, target) in cases {
                    check(*target)?;
                }
            }
            _ => {}
        }
    }
    if !terminal(original.last().expect("nonempty")) {
        return Ok((
            original.to_vec(),
            FunctionControlFlowReport {
                old_operations: original.len(),
                new_operations: original.len(),
                skipped_terminal_fallthrough: true,
                ..Default::default()
            },
        ));
    }
    let targets = jump_targets(original);
    // Resolve edges while inspecting the original body. Clone only the final
    // retained instructions, after reachability and layout have been decided.
    let code = original;
    let resolve = |pc: usize| targets[pc].unwrap_or(pc);
    let mut redirected = 0;
    for op in code {
        let mut count = |pc: usize| {
            redirected += usize::from(resolve(pc) != pc);
        };
        match op {
            Op::Jump { target } => count(*target),
            Op::Switch {
                cases, otherwise, ..
            } => {
                count(*otherwise);
                for (_, target) in cases {
                    count(*target);
                }
            }
            _ => {}
        }
    }
    let mut live = vec![false; code.len()];
    let mut pending = vec![0];
    while let Some(pc) = pending.pop() {
        if live[pc] {
            continue;
        }
        live[pc] = true;
        match &code[pc] {
            Op::Jump { target } => pending.push(resolve(*target)),
            Op::Switch {
                cases, otherwise, ..
            } => {
                pending.push(resolve(*otherwise));
                pending.extend(cases.iter().map(|(_, target)| resolve(*target)));
            }
            Op::Return | Op::Trap { .. } => {}
            _ => pending.push(pc + 1), // A terminal final instruction was required above.
        }
    }
    let mut starts = vec![false; code.len()];
    starts[0] = true;
    for (pc, op) in code.iter().enumerate() {
        match op {
            Op::Jump { target } => starts[resolve(*target)] = true,
            Op::Switch {
                cases, otherwise, ..
            } => {
                starts[resolve(*otherwise)] = true;
                for (_, target) in cases {
                    starts[resolve(*target)] = true;
                }
            }
            _ => {}
        }
        if terminal(op) && pc + 1 < code.len() {
            starts[pc + 1] = true;
        }
    }
    let mut boundaries: Vec<_> = (0..code.len()).filter(|pc| starts[*pc]).collect();
    boundaries.push(code.len());
    let blocks: Vec<_> = boundaries.windows(2).map(|x| x[0]..x[1]).collect();
    let mut block_at = vec![0; code.len()];
    for (id, block) in blocks.iter().enumerate() {
        for pc in block.clone() {
            block_at[pc] = id;
        }
    }
    let mut order = Vec::new();
    let mut visited = vec![false; blocks.len()];
    for seed in 0..blocks.len() {
        let mut current = Some(seed);
        while let Some(id) = current {
            let block = &blocks[id];
            if visited[id] || !live[block.start] {
                break;
            }
            visited[id] = true;
            order.push(id);
            if !layout {
                break;
            }
            let candidates: Vec<_> = match &code[block.end - 1] {
                Op::Jump { target } => vec![resolve(*target)],
                Op::Switch {
                    cases, otherwise, ..
                } => std::iter::once(resolve(*otherwise))
                    .chain(cases.iter().map(|(_, target)| resolve(*target)))
                    .collect(),
                Op::Return | Op::Trap { .. } => vec![],
                _ => vec![block.end],
            };
            current = candidates
                .into_iter()
                .map(|pc| block_at[pc])
                .find(|next| !visited[*next]);
        }
    }
    let mut remap = vec![None; code.len()];
    let mut output = Vec::new();
    let mut inserted = 0;
    for (index, id) in order.iter().copied().enumerate() {
        let block = &blocks[id];
        for pc in block.clone() {
            assert!(live[pc]);
            remap[pc] = Some(output.len());
            let mut op = code[pc].clone();
            match &mut op {
                Op::Jump { target } => *target = resolve(*target),
                Op::Switch { cases, otherwise, .. } => {
                    *otherwise = resolve(*otherwise);
                    for (_, target) in cases {
                        *target = resolve(*target);
                    }
                }
                _ => {}
            }
            output.push(op);
        }
        if !terminal(&code[block.end - 1])
            && order.get(index + 1).map(|next| blocks[*next].start) != Some(block.end)
        {
            // This new edge must reach the original fallthrough instruction.
            // It was not present during jump threading, so do not resolve it.
            output.push(Op::Jump { target: block.end });
            inserted += 1;
        }
    }
    for op in &mut output {
        let map = |pc: &mut usize| -> Result<(), String> {
            *pc = remap[*pc].ok_or("reachable edge points to a removed instruction")?;
            Ok(())
        };
        match op {
            Op::Jump { target } => map(target)?,
            Op::Switch {
                cases, otherwise, ..
            } => {
                map(otherwise)?;
                for (_, target) in cases {
                    map(target)?;
                }
            }
            _ => {}
        }
    }
    let removed = remove_fallthrough_jumps(&mut output)?;
    if layout && output.len() > original.len() {
        let (fallback, mut report) = transform_code(original, false)?;
        report.layout_rejected_for_growth = true;
        return Ok((fallback, report));
    }
    #[cfg(test)]
    {
        // Independently check the multiset of observable operations. Only Jump
        // instructions can be inserted/removed, and only unreachable non-branches
        // can disappear. Switch values and case ordering were retained by cloning.
        let observable = |op: &Op| !matches!(op, Op::Jump { .. } | Op::Switch { .. });
        let mut before: Vec<_> = original
            .iter()
            .enumerate()
            .filter(|(pc, op)| live[*pc] && observable(op))
            .map(|(_, op)| bincode::serialize(op).expect("serialize operation"))
            .collect();
        let mut after: Vec<_> = output
            .iter()
            .filter(|op| observable(op))
            .map(|op| bincode::serialize(op).expect("serialize operation"))
            .collect();
        before.sort();
        after.sort();
        assert_eq!(before, after);
    }
    let report = FunctionControlFlowReport {
        old_operations: original.len(),
        new_operations: output.len(),
        redirected_edges: redirected,
        unreachable_operations: live.iter().filter(|x| !**x).count(),
        inserted_jumps: inserted,
        removed_fallthrough_jumps: removed,
        ..Default::default()
    };
    Ok((output, report))
}
