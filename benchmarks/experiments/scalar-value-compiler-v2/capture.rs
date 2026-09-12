//! Typed MIR selection and transport through the validated frame relocation.
use super::*;
use rustc_middle::mir::visit::{MutatingUseContext, NonMutatingUseContext, PlaceContext, Visitor};
#[path = "scalar_value_transform.rs"]
mod transform;
use transform::{Binding, MAX_FUNCTIONS, MAX_LOCALS};
const MAX_TOTAL_LOCALS: usize = 1_000_000;

pub(crate) fn enabled() -> bool {
    std::env::var("RUST_INTERP_SCALAR_VALUES").as_deref() == Ok("1")
}
#[derive(Default)]
pub(crate) struct Collector {
    pub enabled: bool,
    bindings: BTreeMap<usize, Binding>,
    locals: usize,
    declined: usize,
    relocated: usize,
}
impl Collector {
    pub fn new(enabled: bool) -> Self {
        Self {
            enabled,
            ..Default::default()
        }
    }
    pub fn remaining(&self) -> usize {
        MAX_TOTAL_LOCALS - self.locals
    }
    pub fn push(&mut self, b: Option<Binding>) -> Result<()> {
        let Some(b) = b else {
            self.declined += 1;
            return Ok(());
        };
        if self.bindings.len() >= MAX_FUNCTIONS || b.slots.len() > self.remaining() {
            self.declined += 1;
            return Ok(());
        }
        self.locals += b.slots.len();
        if self.bindings.insert(b.function, b).is_some() {
            return Err("duplicate scalar MIR binding".into());
        }
        Ok(())
    }
    pub fn relocate(&mut self, id: usize, old: &[Slot], new: &[Slot]) -> Result<()> {
        if let Some(b) = self.bindings.get_mut(&id) {
            if b.slots.len() != old.len()
                || old.len() != new.len()
                || !b
                    .slots
                    .iter()
                    .zip(old)
                    .all(|(a, b)| a.offset == b.offset && a.size == b.size)
                || !old.iter().zip(new).all(|(a, b)| a.size == b.size)
            {
                return Err("scalar MIR relocation binding changed".into());
            }
            b.slots = new.to_vec();
            self.relocated += 1;
        }
        Ok(())
    }
    pub fn finish(self, program: Program) -> Result<rust_interp_bytecode::scalar_abi::Artifact> {
        if !self.enabled {
            return rust_interp_bytecode::scalar_abi::Artifact::legacy(program);
        }
        let started = std::time::Instant::now();
        let (artifact, report) = transform::apply(program, self.bindings.into_values().collect())?;
        eprintln!(
            "rust-interp-scalar-values: {}",
            serde_json::json!({"schema_version":1,"report":report,
            "typed_locals":self.locals,"capture_declines":self.declined,"relocated_bindings":self.relocated,
            "finalize_seconds":started.elapsed().as_secs_f64(),"max_total_locals":MAX_TOTAL_LOCALS})
        );
        Ok(artifact)
    }
}

struct Uses<'a> {
    eligible: &'a mut [bool],
}
impl Uses<'_> {
    fn access(&mut self, i: usize, context: PlaceContext) {
        match context {
            PlaceContext::NonUse(..)
            | PlaceContext::MutatingUse(MutatingUseContext::Store | MutatingUseContext::Call)
            | PlaceContext::NonMutatingUse(
                NonMutatingUseContext::Copy
                | NonMutatingUseContext::Move
                | NonMutatingUseContext::Inspect,
            ) => {}
            _ => self.eligible[i] = false,
        }
    }
}
impl<'tcx> Visitor<'tcx> for Uses<'_> {
    fn visit_place(&mut self, place: &Place<'tcx>, context: PlaceContext, _: mir::Location) {
        // Access through a pointer reads its value; it does not expose the
        // storage holding that pointer. Indices likewise read their values.
        if matches!(place.projection.first(), Some(mir::ProjectionElem::Deref)) {
            return;
        }
        if place.projection.is_empty() {
            self.access(place.local.as_usize(), context);
        } else {
            self.eligible[place.local.as_usize()] = false;
        }
    }
    fn visit_local(&mut self, local: mir::Local, context: PlaceContext, _: mir::Location) {
        self.access(local.as_usize(), context);
    }
}

pub(super) fn capture(
    lower: &Lower<'_, '_>,
    arguments: &[Slot],
    remaining: usize,
) -> Result<Option<Binding>> {
    if lower.locals.is_empty()
        || lower.locals.len() > MAX_LOCALS
        || lower.locals.len() > remaining
        || lower.code.len() > 100_000
    {
        return Ok(None);
    }
    let mut eligible = vec![true; lower.locals.len()];
    for (bb, block) in lower.body.basic_blocks.iter_enumerated() {
        for (statement_index, statement) in block.statements.iter().enumerate() {
            Uses {
                eligible: &mut eligible,
            }
            .visit_statement(
                statement,
                mir::Location {
                    block: bb,
                    statement_index,
                },
            );
            // Aggregate construction keeps the established conservative rule;
            // new Call consumers have their own final-bytecode width proof.
            if let StatementKind::Assign(pair) = &statement.kind {
                if let Rvalue::Aggregate(_, ops) = &pair.1 {
                    for op in ops {
                        if let Operand::Copy(p) | Operand::Move(p) = op {
                            eligible[p.local.as_usize()] = false;
                        }
                    }
                }
            }
        }
        Uses {
            eligible: &mut eligible,
        }
        .visit_terminator(
            block.terminator(),
            mir::Location {
                block: bb,
                statement_index: block.statements.len(),
            },
        );
    }
    for (local, decl) in lower.body.local_decls.iter_enumerated() {
        let i = local.as_usize();
        let layout = lower.layout(lower.mono(decl.ty))?;
        eligible[i] &= matches!(layout.backend_repr, rustc_abi::BackendRepr::Scalar(_))
            && matches!(lower.locals[i].size, 1 | 2 | 4 | 8 | 16)
            && Some(local) != lower.body.spread_arg;
    }
    let mut args = vec![];
    for arg in arguments {
        let matches: Vec<_> = (1..=lower.body.arg_count)
            .filter(|&i| {
                lower.locals[i].offset == arg.offset
                    && lower.locals[i].size == arg.size
                    && arg.size != 0
            })
            .collect();
        args.push(if matches.len() == 1 {
            Some(matches[0])
        } else {
            None
        });
    }
    Ok(Some(Binding {
        function: *lower
            .exporter
            .ids
            .get(&lower.instance)
            .ok_or("missing scalar MIR function")?,
        name: format!(
            "{}{:?}",
            lower.tcx().def_path_str(lower.instance.def_id()),
            lower.instance.args
        ),
        slots: lower.locals.clone(),
        eligible,
        arguments: args,
    }))
}
