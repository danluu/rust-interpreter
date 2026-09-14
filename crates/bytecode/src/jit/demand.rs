//! Explicit region-at-a-time preparation under bounded retained ownership.
use super::*;
use function_analysis::{FunctionAnalysis, retained::{Plans, MAX_RETAINED_BYTES}};
use demand_links::{Links, MAX_METADATA_BYTES};

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
mod tests;

pub(super) struct Publication {
    pub pc: usize,
    pub offset: usize,
    pub bytes: usize,
    pub assertion_base: usize,
    pub assertions: usize,
}

struct FunctionState {
    frontier: Vec<u8>, // 0: nonleader; 1: unattempted; 2: attempted
    links: Box<Links>,
    publications: Vec<Publication>,
}

impl FunctionState {
    fn new(id: usize, code_len: usize, plan: &FunctionAnalysis, available: usize) -> Result<Box<Self>, String> {
        let requested = code_len.checked_add(std::mem::size_of::<Self>())
            .and_then(|n| n.checked_add(plan.regions.len().checked_mul(std::mem::size_of::<Publication>())?))
            .ok_or("demand function metadata size overflow")?;
        if requested > available { return Err("demand function metadata budget exhausted".into()); }
        let mut frontier = vec![];
        frontier.try_reserve_exact(code_len).map_err(|_| "demand frontier allocation failed")?;
        frontier.resize(code_len, 0);
        let mut publications = vec![];
        publications.try_reserve_exact(plan.regions.len()).map_err(|_| "demand publication allocation failed")?;
        let base = std::mem::size_of::<Self>() + frontier.capacity()
            + publications.capacity() * std::mem::size_of::<Publication>();
        let remaining = available.checked_sub(base).ok_or("demand function metadata capacity exceeds budget")?;
        let pcs: Vec<_> = plan.regions.iter().map(|r| r.start).collect();
        let links = Box::new(Links::new(id, &pcs, remaining)?);
        for pc in pcs { frontier[pc] = 1; }
        Ok(Box::new(Self { frontier, links, publications }))
    }

    fn charge(&self) -> usize {
        std::mem::size_of::<Self>() + self.frontier.capacity() + self.links.charge()
            + self.publications.capacity() * std::mem::size_of::<Publication>()
    }
}

pub(super) struct State {
    plans: Box<Plans>,
    functions: Vec<Option<Box<FunctionState>>>,
    metadata_used: usize,
    pub declined_regions: usize,
    pub eager_fallbacks: usize,
}

impl State {
    fn new(functions: usize) -> Result<Self, String> {
        let plans = Box::new(Plans::new(functions, MAX_RETAINED_BYTES).ok_or("demand plan pool allocation refused")?);
        let bytes = functions.checked_mul(std::mem::size_of::<Option<Box<FunctionState>>>())
            .and_then(|n| n.checked_add(std::mem::size_of::<Self>())).ok_or("demand function index overflow")?;
        if bytes > MAX_METADATA_BYTES { return Err("demand function index budget exhausted".into()); }
        let mut owned = vec![];
        owned.try_reserve_exact(functions).map_err(|_| "demand function index allocation failed")?;
        let metadata_used = std::mem::size_of::<Self>() + owned.capacity() * std::mem::size_of::<Option<Box<FunctionState>>>();
        if metadata_used > MAX_METADATA_BYTES { return Err("demand function index capacity exceeds budget".into()); }
        owned.resize_with(functions, || None);
        Ok(Self { plans, functions: owned, metadata_used, declined_regions: 0, eager_fallbacks: 0 })
    }

    fn wants(&self, id: usize, pc: usize) -> bool {
        self.functions.get(id).and_then(Option::as_deref).and_then(|f| f.frontier.get(pc)) == Some(&1)
    }

    pub fn publications(&self, id: usize) -> Option<&[Publication]> {
        Some(&self.functions.get(id)?.as_deref()?.publications)
    }

    pub fn internal(&self, id: usize, pc: usize) -> Option<usize> {
        self.functions.get(id)?.as_deref()?.links.internal(pc)
    }
}

impl<'a> Jit<'a> {
    pub(super) fn prepare_demand_function(&mut self, id: usize) -> Result<bool, String> {
        if self.scalar.is_some() { self.prepare_scalar_callees(id)?; }
        let f = &self.program.functions[id];
        if !self.resumable.as_ref().unwrap().fits(f.code.len()) {
            return self.finish_preparation(id, Ok(None));
        }
        let plan = self.analyze_function(f);
        let available = MAX_METADATA_BYTES - self.demand.as_ref().unwrap().metadata_used;
        let state = match FunctionState::new(id, f.code.len(), &plan, available) {
            Ok(state) => state,
            Err(_) => return self.demand_eager_fallback(id, plan),
        };
        let mut blocks = vec![];
        if blocks.try_reserve_exact(f.code.len()).is_err() {
            return self.finish_preparation(id, Ok(None));
        }
        blocks.resize(f.code.len(), None);
        if let Err(plan) = self.demand.as_mut().unwrap().plans.insert(id, plan) {
            return self.demand_eager_fallback(id, plan);
        }
        // Every other initial allocation/admission is complete. Once this
        // table is published, later region refusals keep its stable VM slots.
        let reserved = self.resumable.as_mut().unwrap().reserve_empty(id, f.code.len());
        if !matches!(reserved, Ok(true)) {
            drop(self.demand.as_mut().unwrap().plans.remove(id));
            return match reserved { Ok(false) => self.finish_preparation(id, Ok(None)),
                Err(error) => Err(error), Ok(true) => unreachable!() };
        }
        let demand = self.demand.as_mut().unwrap();
        demand.metadata_used += state.charge();
        demand.functions[id] = Some(state);
        self.blocks[id] = blocks;
        self.prepared[id] = true;
        self.prepare_demand_region(id, 0)?;
        Ok(true)
    }

    fn demand_eager_fallback(&mut self, id: usize, plan: FunctionAnalysis) -> Result<bool, String> {
        self.demand.as_mut().unwrap().eager_fallbacks += 1;
        let staged = self.emit_analyzed_function(&self.program.functions[id], (self.capacity - self.bytes) / 4,
            self.assertions.len(), None, &plan, None);
        self.finish_preparation(id, staged)
    }

    fn decline_demand_region(&mut self, id: usize, pc: usize) -> bool {
        let state = self.demand.as_mut().unwrap();
        state.functions[id].as_mut().unwrap().frontier[pc] = 2;
        state.declined_regions += 1;
        false
    }

    fn prepare_demand_region(&mut self, id: usize, pc: usize) -> Result<bool, String> {
        let plan = self.demand.as_ref().unwrap().plans.get(id).ok_or("missing retained demand plan")?;
        let staged = self.emit_analyzed_function(&self.program.functions[id], (self.capacity - self.bytes) / 4,
            self.assertions.len(), None, plan, Some(pc));
        let mut staged = match staged {
            Ok(Some(staged)) => staged,
            Ok(None) | Err(EmitError::Limit(_)) => return Ok(self.decline_demand_region(id, pc)),
            Err(EmitError::InvalidRelocation(error)) => return Err(error.into()),
        };
        if staged.selected != Some(pc) || staged.entries.len() != 1 || staged.resumes.len() != 1
            || staged.internal_entries.len() != 1 {
            return Err("invalid staged demand metadata".into());
        }
        let block = staged.entries[0].ok_or("missing demand external entry")?;
        let resume = staged.resumes[0].ok_or("missing demand resume entry")?;
        let internal = staged.internal_entries[0].ok_or("missing demand internal entry")?;
        if block.offset != 0 || resume >= staged.words.len() { return Err("invalid demand entry offset".into()); }
        let bytes = staged.words.len() * 4;
        let assertion_base = self.assertions.len();
        let assertion_count = staged.assertions.len();
        self.assertions.try_reserve(assertion_count).map_err(|_| "JIT assertion table allocation failed")?;
        if self.code.is_none() { self.code = Some(platform::Code::reserve(self.capacity)?); }
        let arena = self.code.as_ref().unwrap().published().0;
        let demand = self.demand.as_mut().unwrap();
        let state = demand.functions[id].as_mut().unwrap();
        let first = state.publications.is_empty();
        let available = MAX_METADATA_BYTES - demand.metadata_used;
        let transaction = state.links.prepare(id, pc, self.bytes / 4, internal,
            std::mem::take(&mut staged.words), &staged.region_links, available);
        let transaction = match transaction {
            Ok(transaction) => transaction,
            Err(error) if error.contains("budget exhausted") || error.contains("allocation failed")
                || error.contains("capacity exceeds budget") => {
                state.frontier[pc] = 2;
                demand.declined_regions += 1;
                return Ok(false);
            }
            Err(error) => return Err(error),
        };
        let charge = transaction.additional_charge();
        let slot = self.resumable.as_mut().unwrap().vacant_entry(id, pc)?;
        let offset = transaction.publish(self.code.as_mut().unwrap())?;
        // All fallible work finished before code commit. The table slot and
        // fixed publication capacity were reserved, and the program is owned.
        demand.metadata_used += charge;
        state.frontier[pc] = 2;
        state.publications.push(Publication { pc, offset, bytes, assertion_base, assertions: assertion_count });
        *slot = arena + offset + resume * 4;
        self.blocks[id][pc] = Some(Block { offset, end: block.end });
        self.assertions.extend(staged.assertions);
        self.bytes += bytes;
        self.operations += staged.operations;
        if first {
            self.compiled_functions += 1;
            self.register_functions += usize::from(staged.register_pairs != 0);
            self.register_pairs += staged.register_pairs;
            self.liveness_declines += usize::from(staged.liveness_declined);
        }
        Ok(true)
    }

    pub(crate) fn enable_demand_regions(&mut self) -> Result<(), String> {
        if self.resumable.is_none() || self.demand.is_some() || self.prepared.iter().any(|p| *p) {
            return Err("demand regions require a fresh resumable JIT".into());
        }
        self.demand = Some(State::new(self.program.functions.len())?);
        Ok(())
    }

    pub(crate) fn wants_region(&self, id: usize, pc: usize) -> bool {
        self.demand.as_ref().is_some_and(|state| state.wants(id, pc))
    }

    pub(crate) fn ensure_region(&mut self, id: usize, pc: usize) -> Result<bool, String> {
        if !self.wants_region(id, pc) { return Ok(false); }
        let start = std::time::Instant::now();
        let before = self.compile_nanos;
        let result = self.prepare_demand_region(id, pc);
        self.compile_nanos = before + start.elapsed().as_nanos();
        result
    }
}
