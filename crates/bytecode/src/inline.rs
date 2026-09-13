use crate::{Function, Op, Program, Reg};
use serde_json::{Value, json};

#[derive(Clone, Copy)]
pub struct Options {
    pub leaf_operations: usize,
    pub caller_growth: usize,
    pub program_growth_percent: usize,
}
impl Default for Options {
    fn default() -> Self {
        Self {
            leaf_operations: 192,
            caller_growth: 4096,
            program_growth_percent: 50,
        }
    }
}

// Body, argument and result copies share the fixed-copy emitter bound.
// Frame and total code-growth budgets remain independent of this limit.
const MAX_COPY_BYTES: usize = 128;

fn scalar_leaf(f: &Function) -> bool {
    f.code.len() > 1
        && f.code.iter().any(|op| matches!(op, Op::Return))
        && matches!(
            f.code.last(),
            Some(Op::Return | Op::Trap { .. } | Op::Jump { .. } | Op::Switch { .. })
        )
        && f.code.iter().all(|op| match op {
            Op::Imm { .. }
            | Op::Local { .. }
            | Op::Load { .. }
            | Op::Store { .. }
            | Op::Cast { .. }
            | Op::Select { .. }
            | Op::Assert { .. }
            | Op::Jump { .. }
            | Op::Return
            | Op::Trap { .. } => true,
            Op::Call { .. } | Op::CompareBytes { .. } => true,
            Op::Copy { size, .. } => *size <= MAX_COPY_BYTES,
            Op::Binary { bits, .. } | Op::Unary { bits, .. } => *bits <= 64,
            Op::Switch { cases, .. } => cases.len() <= 16,
            _ => false,
        })
}

// Compiler-only Local analysis. Facts are discarded at every semantic block
// boundary. All register writers are enumerated so adding an opcode requires
// reviewing this proof. Calls and stores write memory, never caller registers.
struct Site {
    pc: usize,
    arguments: Vec<usize>,
    destination: usize,
}
fn local_sites(program: &Program, caller: &Function) -> Vec<Site> {
    let mut starts = vec![false; caller.code.len()];
    starts[0] = true;
    for (pc, op) in caller.code.iter().enumerate() {
        match op {
            Op::Jump { target } => starts[*target] = true,
            Op::Switch {
                cases, otherwise, ..
            } => {
                starts[*otherwise] = true;
                for (_, target) in cases {
                    starts[*target] = true;
                }
            }
            _ => {}
        }
        if matches!(
            op,
            Op::Jump { .. } | Op::Switch { .. } | Op::Return | Op::Trap { .. }
        ) && pc + 1 < starts.len()
        {
            starts[pc + 1] = true;
        }
    }
    let mut locals = vec![(0usize, 0usize); caller.registers];
    let mut epoch = 1;
    let mut sites = Vec::new();
    for (pc, op) in caller.code.iter().enumerate() {
        if starts[pc] {
            epoch = pc + 1;
        }
        if let Op::Call {
            function,
            args,
            destination,
        } = op
        {
            let leaf = &program.functions[*function];
            let extent = |reg: Reg, size: usize| {
                let (defined, offset) = locals[reg as usize];
                (defined == epoch
                    && offset
                        .checked_add(size)
                        .is_some_and(|end| end <= caller.frame_size))
                .then_some(offset)
            };
            if let Some(destination) = extent(*destination, leaf.result.size) {
                if let Some(arguments) = args
                    .iter()
                    .zip(&leaf.args)
                    .map(|(reg, slot)| extent(*reg, slot.size))
                    .collect::<Option<Vec<_>>>()
                {
                    sites.push(Site {
                        pc,
                        arguments,
                        destination,
                    });
                }
            }
        }
        match op {
            Op::Local { dst, offset } => locals[*dst as usize] = (epoch, *offset),
            Op::Binary { dst, overflow, .. } => {
                locals[*dst as usize].0 = 0;
                locals[*overflow as usize].0 = 0;
            }
            Op::Imm { dst, .. }
            | Op::Load { dst, .. }
            | Op::Unary { dst, .. }
            | Op::Cast { dst, .. }
            | Op::Select { dst, .. }
            | Op::CompareBytes { dst, .. }
            | Op::Allocate { dst, .. }
            | Op::Reallocate { dst, .. }
            | Op::RandomBytes { dst, .. }
            | Op::DescriptorOpen { dst, .. } | Op::DescriptorWrite { dst, .. }
            | Op::DescriptorClose { dst, .. } | Op::DescriptorGetFd { dst, .. }
            | Op::CurrentDirectory { dst, .. } | Op::DescriptorStat { dst, .. }
            | Op::EnvironmentGet { dst, .. }
            | Op::CpuFeatureQuery { dst, .. }
            | Op::CAllocate { dst, .. } | Op::CReallocate { dst, .. } | Op::CAlignedAllocate { dst, .. }
            | Op::FloatBinary { dst, .. }
            | Op::FloatUnary { dst, .. }
            | Op::FloatConvert { dst, .. } => {
                locals[*dst as usize].0 = 0;
            }
            Op::Store { .. }
            | Op::Copy { .. }
            | Op::CopyDynamic { .. }
            | Op::Jump { .. }
            | Op::Switch { .. }
            | Op::Assert { .. }
            | Op::Call { .. }
            | Op::CallIndirect { .. }
            | Op::Return
            | Op::Trap { .. }
            | Op::Deallocate { .. }
            | Op::CDeallocate { .. } | Op::RegisterTlsDestructor { .. }
            | Op::FillBytes { .. }
            | Op::ResetThreadLocals => {}
        }
    }
    sites
}

fn relocated(
    op: &Op,
    reg_base: Reg,
    frame_base: usize,
    pc_base: usize,
    epilogue: usize,
    origin: &str,
) -> Op {
    let r = |reg: Reg| reg + reg_base;
    match op {
        Op::Imm { dst, value } => Op::Imm {
            dst: r(*dst),
            value: *value,
        },
        Op::Local { dst, offset } => Op::Local {
            dst: r(*dst),
            offset: frame_base + offset,
        },
        Op::Load { dst, address, size } => Op::Load {
            dst: r(*dst),
            address: r(*address),
            size: *size,
        },
        Op::Store { address, src, size } => Op::Store {
            address: r(*address),
            src: r(*src),
            size: *size,
        },
        Op::Copy { dst, src, size } => Op::Copy {
            dst: r(*dst),
            src: r(*src),
            size: *size,
        },
        Op::Call { function, args, destination } => Op::Call {
            function: *function, args: args.iter().map(|reg| r(*reg)).collect(), destination: r(*destination),
        },
        Op::CompareBytes { dst, left, right, size } => Op::CompareBytes {
            dst: r(*dst), left: r(*left), right: r(*right), size: r(*size),
        },
        Op::Binary {
            dst,
            overflow,
            op,
            a,
            b,
            bits,
            signed,
        } => Op::Binary {
            dst: r(*dst),
            overflow: r(*overflow),
            op: *op,
            a: r(*a),
            b: r(*b),
            bits: *bits,
            signed: *signed,
        },
        Op::Unary { dst, op, src, bits } => Op::Unary {
            dst: r(*dst),
            op: *op,
            src: r(*src),
            bits: *bits,
        },
        Op::Cast {
            dst,
            src,
            from,
            to,
            signed,
        } => Op::Cast {
            dst: r(*dst),
            src: r(*src),
            from: *from,
            to: *to,
            signed: *signed,
        },
        Op::Select {
            dst,
            condition,
            yes,
            no,
        } => Op::Select {
            dst: r(*dst),
            condition: r(*condition),
            yes: r(*yes),
            no: r(*no),
        },
        Op::Jump { target } => Op::Jump {
            target: pc_base + target,
        },
        Op::Switch {
            value,
            cases,
            otherwise,
        } => Op::Switch {
            value: r(*value),
            cases: cases
                .iter()
                .map(|(value, target)| (*value, pc_base + target))
                .collect(),
            otherwise: pc_base + otherwise,
        },
        Op::Assert {
            value,
            expected,
            message,
        } => Op::Assert {
            value: r(*value),
            expected: *expected,
            message: format!("{message} [inlined from {origin}]"),
        },
        Op::Trap { message } => Op::Trap {
            message: format!("{message} [inlined from {origin}]"),
        },
        Op::Return => Op::Jump { target: epilogue },
        _ => unreachable!("selection excludes unsupported body operations"),
    }
}

/// Bounded, opt-in export-time leaf inlining. The VM never applies this pass
/// implicitly. It changes the resulting artifact's instruction/storage costs
/// and frame addresses, as compiler inlining does. Limits count the new IR.
/// Cold branches, ordered argument copies, function handles and checks remain.
/// Selection is static and does not consume runtime profiles.
pub fn transform(original: &Program, options: Options) -> Result<(Program, Value), String> {
    let prepared = prepare(original, options)?;
    prepared.apply(original.clone())
}

/// Reuse the export pipeline's owned program after all decisions have been
/// made against its unchanged graph. Unmodified functions never need cloning.
pub(crate) fn transform_owned(original: Program, options: Options) -> Result<(Program, Value), String> {
    let prepared = prepare(&original, options)?;
    prepared.apply(original)
}

struct Prepared {
    replacements: Vec<(usize, Function)>,
    sites: usize,
    original_operations: usize,
    growth: usize,
    changed: Vec<Value>,
    options: Options,
    diagnostics: usize,
}

impl Prepared {
    fn apply(self, mut result: Program) -> Result<(Program, Value), String> {
        for (id, function) in self.replacements {
            result.functions[id] = function;
        }
        crate::validate(&result)?;
        let new_operations: usize = result.functions.iter().map(|f| f.code.len()).sum();
        Ok((
            result,
            json!({"selected_sites":self.sites,"original_operations":self.original_operations,"new_operations":new_operations,
            "added_operations_upper_bound":self.growth,"changed_callers":self.changed,"max_leaf_operations":self.options.leaf_operations,
            "max_program_growth_percent":self.options.program_growth_percent,"cloned_diagnostic_bytes":self.diagnostics}),
        ))
    }
}

fn prepare(original: &Program, options: Options) -> Result<Prepared, String> {
    crate::validate(original)?;
    if options.leaf_operations > 192
        || options.program_growth_percent > 100
        || options.caller_growth > 4096
    {
        return Err("leaf inlining options exceed bounded limits".into());
    }
    let nonrecursive = crate::inline_graph::nonrecursive(original);
    let eligible: Vec<_> = original
        .functions
        .iter()
        .enumerate()
        .map(|(id, f)| {
            let calls = f.code.iter().filter(|op| matches!(op, Op::Call { .. })).count();
            scalar_leaf(f) && calls <= 1 && (calls == 0 || nonrecursive[id])
                && f.code.len() <= options.leaf_operations
                && f.frame_size <= 512
                && f.registers <= 256
                && f.result.size <= MAX_COPY_BYTES
                && f.args.iter().all(|slot| slot.size <= MAX_COPY_BYTES)
                && !crate::registers::needs_initial_zeroes(f)
        })
        .collect();
    let original_operations: usize = original.functions.iter().map(|f| f.code.len()).sum();
    let growth_limit = original_operations * options.program_growth_percent / 100;
    // Bound cloned diagnostics separately: instruction counts alone do not
    // bound strings in Trap/Assert or repeated callee identity suffixes.
    let diagnostic_cost: Vec<usize> = original
        .functions
        .iter()
        .map(|f| {
            f.code
                .iter()
                .map(|op| match op {
                    Op::Trap { message } | Op::Assert { message, .. } => message
                        .len()
                        .saturating_add(f.name.len())
                        .saturating_add(16),
                    _ => 0,
                })
                .fold(0usize, usize::saturating_add)
        })
        .collect();
    let mut diagnostics = 0usize;
    let mut growth = 0usize;
    let mut sites = 0usize;
    let mut changed = vec![];
    let mut replacements = Vec::new();
    for (id, caller) in original.functions.iter().enumerate() {
        let bank_offset = (caller.frame_size + caller.frame_align - 1) & !(caller.frame_align - 1);
        let mut selected = Vec::new();
        let mut bank_frame = 0usize;
        let mut bank_registers = 0usize;
        let mut caller_growth = 0usize;
        let mut caller_diagnostics = 0usize;
        for site in local_sites(original, caller) {
            let op = &caller.code[site.pc];
            let Op::Call { function, args, .. } = op else {
                continue;
            };
            let leaf = &original.functions[*function];
            let extra = leaf.code.len() + 4 + 3 * args.len() + 3 - 1;
            if !eligible[*function]
                // The bank is reserved even when this call's branch is not
                // executed. Bound new aggregate-leaf growth, including padding,
                // while retaining the existing small-copy eligibility policy.
                || (bank_offset - caller.frame_size + leaf.frame_size.max(1)
                    > caller.frame_size / 2
                    && (leaf.result.size > 32
                        || leaf.args.iter().any(|slot| slot.size > 32)
                        || leaf.code.iter().any(|op| {
                            matches!(op, Op::Copy { size, .. } if *size > 32)
                        })))
                || leaf.frame_align > caller.frame_align
                || caller_growth + extra > options.caller_growth
                || growth + extra > growth_limit
                || bank_offset + leaf.frame_size.max(1) > 16 * 1024 * 1024
                || caller.registers + leaf.registers + 3 > 1_000_000
                || diagnostics.saturating_add(diagnostic_cost[*function]) > 1024 * 1024
            {
                continue;
            }
            selected.push(site);
            sites += 1;
            growth += extra;
            caller_growth += extra;
            diagnostics += diagnostic_cost[*function];
            caller_diagnostics += diagnostic_cost[*function];
            bank_frame = bank_frame.max(leaf.frame_size.max(1));
            bank_registers = bank_registers.max(leaf.registers);
        }
        if bank_frame == 0 {
            continue;
        }
        let reg_base = caller.registers as Reg;
        let zero = reg_base + bank_registers as Reg;
        let length = zero + 1;
        let address = zero + 2;
        let mut code = Vec::with_capacity(caller.code.len() + caller_growth);
        let mut remap = vec![0; caller.code.len()];
        let mut original_branches = vec![];
        let selected_count = selected.len();
        let mut selected = selected.into_iter().peekable();
        for (pc, op) in caller.code.iter().enumerate() {
            remap[pc] = code.len();
            if selected.peek().is_none_or(|site| site.pc != pc) {
                if matches!(op, Op::Jump { .. } | Op::Switch { .. }) {
                    original_branches.push(code.len());
                }
                code.push(op.clone());
                continue;
            }
            let site = selected.next().expect("selected call site");
            let Op::Call {
                function,
                args,
                destination,
            } = op
            else {
                unreachable!()
            };
            let leaf = &original.functions[*function];
            code.extend([
                Op::Local {
                    dst: address,
                    offset: bank_offset,
                },
                Op::Imm {
                    dst: zero,
                    value: 0,
                },
                Op::Imm {
                    dst: length,
                    value: leaf.frame_size.max(1) as u128,
                },
                Op::FillBytes {
                    address,
                    value: zero,
                    size: length,
                },
            ]);
            // Proven caller-local argument bytes cannot overlap the disjoint
            // inline bank. Preserve argument order when callee slots overlap.
            for ((src, slot), offset) in args.iter().zip(&leaf.args).zip(&site.arguments) {
                // Repeat the proven address, not a load from mutable data.
                // FillBytes ends the preceding native block; this gives the
                // following Copy exact caller/inline Local extents again.
                code.push(Op::Local {
                    dst: *src,
                    offset: *offset,
                });
                code.push(Op::Local {
                    dst: address,
                    offset: bank_offset + slot.offset,
                });
                code.push(Op::Copy {
                    dst: address,
                    src: *src,
                    size: slot.size,
                });
            }
            let body = code.len();
            let epilogue = body + leaf.code.len();
            for op in &leaf.code {
                code.push(relocated(
                    op,
                    reg_base,
                    bank_offset,
                    body,
                    epilogue,
                    &leaf.name,
                ));
            }
            code.push(Op::Local {
                dst: address,
                offset: bank_offset + leaf.result.offset,
            });
            // The original destination register still denotes the same Local.
            // Restate that definition at the return join, both for the emitter
            // and for the conservative register-initialization proof.
            code.push(Op::Local {
                dst: *destination,
                offset: site.destination,
            });
            code.push(Op::Copy {
                dst: *destination,
                src: address,
                size: leaf.result.size,
            });
        }
        // Only original caller branches still contain old caller PCs. Leaf
        // backedges already target their relocated bodies after initialization.
        for pc in original_branches {
            match &mut code[pc] {
                Op::Jump { target } => *target = remap[*target],
                Op::Switch {
                    cases, otherwise, ..
                } => {
                    *otherwise = remap[*otherwise];
                    for (_, target) in cases {
                        *target = remap[*target];
                    }
                }
                _ => unreachable!(),
            }
        }
        let removed = crate::remove_fallthrough_jumps(&mut code)?;
        let output = Function {
            name: caller.name.clone(),
            frame_size: bank_offset + bank_frame,
            frame_align: caller.frame_align,
            registers: caller.registers + bank_registers + 3,
            args: caller.args.clone(),
            result: caller.result,
            code,
        };
        // Reject an expansion that introduces whole-caller register clearing.
        // This is a performance guard, never a trusted semantic annotation.
        if !crate::registers::needs_initial_zeroes(caller)
            && crate::registers::needs_initial_zeroes(&output)
        {
            growth -= caller_growth;
            sites -= selected_count;
            diagnostics -= caller_diagnostics;
            continue;
        }
        changed.push(json!({"function":id,"name":caller.name,"sites":selected_count,
            "old_operations":caller.code.len(),"new_operations":output.code.len(),"removed_jumps":removed,
            "old_frame_size":caller.frame_size,"new_frame_size":output.frame_size,"old_registers":caller.registers,"new_registers":output.registers,
            "needed_register_zeroes_before":crate::registers::needs_initial_zeroes(caller),"needed_register_zeroes_after":crate::registers::needs_initial_zeroes(&output)}));
        replacements.push((id, output));
    }
    Ok(Prepared { replacements, sites, original_operations, growth, changed, options, diagnostics })
}
