//! Scalar artifact execution through the existing custom VM loop.
use super::*;
use crate::{Engine, Execution, ExecutionProfile, Limits};

impl Artifact {
    pub fn execute(&self, arguments: &[u128], limits: Limits) -> Result<Execution, String> {
        self.execute_with_engine(arguments, limits, Engine::Interpreter)
    }

    pub fn execute_with_engine(&self, arguments: &[u128], limits: Limits, engine: Engine) -> Result<Execution, String> {
        self.validate()?;
        if self.program.version != SCALAR_VERSION {
            return crate::execute_with_engine(&self.program, arguments, limits, engine);
        }
        self.execute_scalar::<false>(arguments, limits, engine, None)
    }

    pub fn execute_profiled(&self, arguments: &[u128], limits: Limits, engine: Engine)
        -> Result<(Execution, ExecutionProfile), String> {
        self.validate()?;
        if self.program.version != SCALAR_VERSION {
            return crate::execute_profiled(&self.program, arguments, limits, engine);
        }
        let mut profile = ExecutionProfile::new(&self.program);
        let execution = self.execute_scalar::<true>(arguments, limits, engine, Some(&mut profile))?;
        Ok((execution, profile))
    }

    // Only called after complete Artifact validation. The old public Program
    // execution API still rejects version 6, which requires this ABI table.
    fn execute_scalar<const PROFILE: bool>(&self, arguments: &[u128], limits: Limits,
        engine: Engine, profile: Option<&mut ExecutionProfile>) -> Result<Execution, String> {
        if limits.jit_native_call_stubs && !limits.jit_native_calls {
            return Err("native Call stubs require native calls".into());
        }
        if engine == Engine::Interpreter && limits.jit_code_dump.is_some() {
            return Err("native code dumps require the JIT engine".into());
        }
        if engine == Engine::Interpreter && limits.jit_persistent_registers {
            return Err("persistent registers require the JIT engine".into());
        }
        if limits.jit_resumable_calls {
            if engine != Engine::Jit { return Err("resumable calls require the JIT engine".into()); }
            if limits.jit_native_calls || limits.jit_native_call_stubs {
                return Err("resumable calls cannot be combined with native tree/stub calls".into());
            }
        }
        if engine == Engine::Interpreter && limits.jit_native_calls {
            return Err("native calls require the JIT engine".into());
        }
        if engine == Engine::Jit {
            if limits.jit_native_calls || limits.jit_native_call_stubs {
                return Err("scalar ABI does not support native tree/stub calls".into());
            }
            return if limits.jit_resumable_calls {
                crate::execute_core::<PROFILE, true, false, false, true, true>(
                    &self.program, arguments, limits, profile, &self.scalar_abi)
            } else {
                crate::execute_core::<PROFILE, true, false, false, false, true>(
                    &self.program, arguments, limits, profile, &self.scalar_abi)
            };
        }
        crate::execute_core::<PROFILE, false, false, false, false, true>(
            &self.program, arguments, limits, profile, &self.scalar_abi)
    }
}

#[cfg(test)]
#[path="scalar_abi_runtime_tests.rs"]
mod tests;
