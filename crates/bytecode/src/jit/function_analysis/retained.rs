//! Bounded immutable plan ownership. Demand execution is not enabled yet.
use super::*;

pub(in crate::jit) const MAX_RETAINED_BYTES: usize = 16 * 1024 * 1024;

pub(in crate::jit) struct Plans {
    owned: Vec<Option<Box<FunctionAnalysis>>>,
    used: usize,
    limit: usize,
}

impl Plans {
    pub fn new(functions: usize, limit: usize) -> Option<Self> {
        if limit > MAX_RETAINED_BYTES { return None; }
        let inline = std::mem::size_of::<Self>();
        let size = std::mem::size_of::<Option<Box<FunctionAnalysis>>>();
        if inline.checked_add(functions.checked_mul(size)?)? > limit { return None; }
        let mut owned = vec![];
        owned.try_reserve_exact(functions).ok()?;
        let used = inline.checked_add(owned.capacity().checked_mul(size)?)?;
        if used > limit { return None; }
        owned.resize_with(functions, || None);
        Some(Self { owned, used, limit })
    }

    // Refusal returns the untouched analysis for immediate eager emission.
    // No entry is replaced, evicted or partially admitted on failure.
    pub fn insert(&mut self, id: usize, plan: FunctionAnalysis) -> Result<(), FunctionAnalysis> {
        let next = plan.retained_bytes().and_then(|bytes| self.used.checked_add(bytes));
        if id >= self.owned.len() || self.owned[id].is_some() || next.is_none_or(|n| n > self.limit) {
            return Err(plan);
        }
        self.owned[id] = Some(Box::new(plan));
        self.used = next.unwrap();
        Ok(())
    }

    pub fn get(&self, id: usize) -> Option<&FunctionAnalysis> { self.owned.get(id)?.as_deref() }

    pub fn remove(&mut self, id: usize) -> Option<Box<FunctionAnalysis>> {
        let plan = self.owned.get_mut(id)?.take()?;
        self.used -= plan.retained_bytes().expect("admitted charge remains immutable");
        Some(plan)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn input() -> Program {
        Program { version: crate::VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
            data: vec![0; 16], statics: vec![], thread_locals: vec![], functions: vec![Function {
                name: "retained plans".into(), frame_size: 32, frame_align: 16, registers: 4,
                args: vec![], result: crate::Slot { offset: 0, size: 0 }, code: vec![
                    Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 7 },
                    Op::Store { address: 0, src: 1, size: 8 }, Op::Return,
                ],
            }] }
    }

    #[test]
    fn retention_admission_release_and_refusal_preserve_eager_fallback() {
        let p = input(); crate::validate(&p).unwrap();
        let jit = Jit::new_resumable(&p, false, MAX_CODE_BYTES, true).unwrap();
        let f = &p.functions[0];
        let original = jit.emit_function(f, MAX_CODE_BYTES / 4).unwrap().unwrap();
        let charge = jit.analyze_function(f).retained_bytes().unwrap();
        let base = Plans::new(2, MAX_RETAINED_BYTES).unwrap().used;
        for extra in [0, charge - 1, charge, 2 * charge] {
            let mut plans = Plans::new(2, base + extra).unwrap();
            let first = plans.insert(0, jit.analyze_function(f));
            if extra < charge {
                let refused = first.err().unwrap();
                let eager = jit.emit_analyzed_function(f, MAX_CODE_BYTES / 4, 0, None, &refused, None).unwrap().unwrap();
                assert_eq!(eager.words, original.words);
                assert_eq!(plans.used, base);
            } else {
                assert!(first.is_ok());
                let retained = plans.get(0).unwrap() as *const FunctionAnalysis;
                assert!(plans.insert(0, jit.analyze_function(f)).is_err());
                assert_eq!(plans.get(0).unwrap() as *const FunctionAnalysis, retained);
                let second = plans.insert(1, jit.analyze_function(f));
                assert_eq!(second.is_ok(), extra == 2 * charge);
                assert_eq!(plans.used, base + charge + usize::from(second.is_ok()) * charge);
                drop(plans.remove(0).unwrap());
                assert!(plans.get(0).is_none());
                assert!(plans.remove(0).is_none());
                assert_eq!(plans.used, base + usize::from(second.is_ok()) * charge);
            }
            let before = plans.used;
            assert!(plans.insert(usize::MAX, jit.analyze_function(f)).is_err());
            assert!(plans.remove(usize::MAX).is_none());
            assert_eq!(plans.used, before);
        }
        assert!(Plans::new(usize::MAX, MAX_RETAINED_BYTES).is_none());
        assert!(Plans::new(0, 0).is_none());
        assert!(Plans::new(0, MAX_RETAINED_BYTES + 1).is_none());
        assert!(jit.code.is_none());
    }

    #[test]
    fn sorted_hint_lookup_preserves_sparse_keys_and_absence() {
        let hints = [(0, 2), (5, 7), (usize::MAX, 11)];
        for (key, value) in hints { assert_eq!(hint(&hints, key), Some(&value)); }
        for key in [1, 4, 6, usize::MAX - 1] { assert!(hint(&hints, key).is_none()); }
        assert!(hint::<usize>(&[], 0).is_none());
    }
}
