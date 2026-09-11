use crate::{ForwardingReport, LeafInlineOptions, Op, Program};

#[derive(Debug)]
pub struct CallOptimizationReport {
    pub forwarding_before_inline: Option<ForwardingReport>,
    pub inlining: Option<serde_json::Value>,
    /// Time spent in the leaf pass only, excluding both forwarding passes.
    pub inline_time: std::time::Duration,
    pub final_forwarding: ForwardingReport,
}

/// Bypass identity wrappers before leaf expansion can hide their structure.
/// Keep the final forwarding pass for wrappers that survive expansion. With
/// inlining disabled this is exactly the existing single forwarding pass.
/// This export-time pipeline retains function IDs and uses the existing leaf
/// eligibility, frame, initialization, and code-growth limits unchanged.
pub fn optimize_calls(
    mut program: Program,
    inline: Option<LeafInlineOptions>,
) -> Result<(Program, CallOptimizationReport), String> {
    let mut report = CallOptimizationReport {
        forwarding_before_inline: None,
        inlining: None,
        inline_time: std::time::Duration::ZERO,
        final_forwarding: ForwardingReport::default(),
    };
    if let Some(options) = inline {
        report.forwarding_before_inline = Some(crate::eliminate_direct_forwarders(&mut program)?);
        let started = std::time::Instant::now();
        let (expanded, details) = crate::inline_leaves(&program, options)?;
        report.inline_time = started.elapsed();
        report.inlining = Some(details);
        program = expanded;
    }
    report.final_forwarding = crate::eliminate_direct_forwarders(&mut program)?;
    Ok((program, report))
}

/// Remove unconditional jumps to the following retained instruction and remap every
/// branch target, including targets that name a removed instruction. This is
/// an export-time transformation: execution limits continue to count the actual
/// instructions in the resulting artifact, which may now contain fewer steps.
/// Hand-constructed VM programs are never implicitly transformed on execution.
pub fn remove_fallthrough_jumps(code: &mut Vec<Op>) -> Result<usize, String> {
    if code.is_empty() { return Err("cannot optimize empty bytecode".into()); }
    let check = |target: usize| {
        if target < code.len() { Ok(()) } else { Err("invalid branch during optimization".to_owned()) }
    };
    // Validate first so an invalid target cannot leave a partially changed body.
    for op in code.iter() {
        match op {
            Op::Jump {target} => check(*target)?,
            Op::Switch {cases,otherwise,..} => {
                check(*otherwise)?;
                for (_,target) in cases { check(*target)?; }
            }
            _ => {}
        }
    }
    // Walk backwards so chains disappear in one linear pass. A forward jump
    // can become fall-through after the instructions it skips were removed.
    // Backedges and self-loops always remain.
    let mut remap = vec![0;code.len()+1];
    remap[code.len()]=code.len();
    let mut remove = vec![false;code.len()];
    for pc in (0..code.len()).rev() {
        remove[pc]=matches!(&code[pc],Op::Jump {target}
            if *target>pc && remap[*target]==remap[pc+1]);
        remap[pc]=if remove[pc] {remap[pc+1]} else {pc};
    }
    let mut removed = 0;
    for pc in 0..code.len() {
        remap[pc]=pc-removed;
        removed+=usize::from(remove[pc]);
    }
    if removed == 0 { return Ok(0); }
    // A valid final instruction cannot be a jump to its nonexistent successor.
    // Consequently every removed chain maps to an instruction that remains.
    let mut kept = Vec::with_capacity(code.len()-removed);
    for (pc,mut op) in code.drain(..).enumerate() {
        if remove[pc] { continue; }
        match &mut op {
            Op::Jump {target} => *target=remap[*target],
            Op::Switch {cases,otherwise,..} => {
                *otherwise=remap[*otherwise];
                for (_,target) in cases { *target=remap[*target]; }
            }
            _ => {}
        }
        kept.push(op);
    }
    *code=kept;
    Ok(removed)
}
