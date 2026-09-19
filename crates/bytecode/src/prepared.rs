//! Reuse immutable code and analyses, with fresh guest state per invocation.
use crate::{Execution, ExecutionMetadata, Limits, Program, jit};

/// An owned, fully validated immutable Program that can be shared by workers.
/// No mutable access or unchecked constructor is exposed. Each worker still
/// performs current runtime admission and creates its own native/guest state.
#[cfg(feature = "jit-template-session")]
pub struct ValidatedProgram {
    program: Program,
    #[cfg(feature = "jit-shared-literal-keys")]
    template_keys: std::sync::OnceLock<Option<jit::cross_program_templates::shared_keys::FunctionKeys>>,
}
#[cfg(feature = "jit-template-session")]
impl ValidatedProgram {
    pub fn new(program: Program) -> Result<Self, String> {
        if program.version & crate::PARTIAL_VALIDATION != 0 {
            return Err("session inputs require fully checked bytecode".into());
        }
        crate::validate(&program)?;
        Ok(Self { program,
            #[cfg(feature = "jit-shared-literal-keys")]
            template_keys: std::sync::OnceLock::new(),
        })
    }

    pub fn program(&self) -> &Program { &self.program }

    #[cfg(feature = "jit-shared-literal-keys")]
    pub(crate) fn template_keys(&self) -> Option<&jit::cross_program_templates::shared_keys::FunctionKeys> {
        self.template_keys.get_or_init(||
            jit::cross_program_templates::shared_keys::FunctionKeys::new(self.program.functions.len())).as_ref()
    }
}

/// A validated immutable program and its lazily compiled custom JIT code.
///
/// This owner stays on its creating thread. Every invocation gets fresh data,
/// statics, heap, registers, frames, TLS and continuation state, even after a
/// preceding invocation failed. Code, immutable analyses and any environment
/// input snapshot are retained. Environment values are copied into fresh
/// readonly guest storage on each invocation; later host changes are not seen.
/// Resumable calls are required; diagnostic profiling uses the one-shot API.
pub struct PreparedJit<'program> {
    program: &'program Program,
    jit: Option<jit::Jit<'program>>,
    metadata: ExecutionMetadata,
    code_bytes: usize,
    persistent_registers: bool,
    scalar_calls: bool,
    indirect_calls: bool,
    preparation_nanos: u128,
    #[cfg(feature = "jit-preparation-observer")]
    session_setup_ns: Option<(u128,u128)>,
}

impl<'program> PreparedJit<'program> {
    /// Validate once and prepare code metadata. Functions compile lazily.
    /// `jit_resumable_calls` must be enabled and tree/stub modes disabled.
    /// The code budget and persistent-register option are fixed for this owner.
    pub fn new(program: &'program Program, limits: &Limits) -> Result<Self, String> {
        let started = std::time::Instant::now();
        Self::check_mode(limits)?;
        crate::validate(program)?;
        Self::new_validated(program, limits, started)
    }

    /// Prepare a fresh owner using an explicitly retained, thread-local staging
    /// history. Validation and scalar admission run for this Program; published
    /// code and every guest invocation remain private to this new owner.
    #[cfg(feature = "jit-template-session")]
    pub fn with_template_history(program: &'program Program, limits: &Limits,
        history: &crate::TemplateHistory) -> Result<Self, String> {
        let started = std::time::Instant::now();
        Self::check_mode(limits)?;
        // context() validates and rejects partial headers before construction.
        let context = history.context(program)?;
        let mut owner = Self::new_validated(program, limits, started)?;
        owner.jit.as_mut().unwrap().attach_templates(context);
        owner.preparation_nanos = started.elapsed().as_nanos();
        Ok(owner)
    }

    #[cfg(feature = "jit-template-session")]
    pub fn template_statistics(&self) -> Option<crate::TemplateStatistics> {
        self.jit.as_ref().unwrap().template_statistics()
    }

    /// Diagnostic elapsed intervals and bounded exact decline sites. These
    /// include observation overhead and must not be used as acceptance timings.
    #[cfg(feature = "jit-preparation-observer")]
    pub fn preparation_observation(&self) -> serde_json::Value {
        let mut value=self.jit.as_ref().unwrap().preparation_observation();
        if let Some((before_metadata_ns,execution_metadata_ns))=self.session_setup_ns {
            value["constructor"]=serde_json::json!({"before_metadata_ns":before_metadata_ns,
                "execution_metadata_ns":execution_metadata_ns,"total_ns":self.preparation_nanos});
        }
        value
    }

    /// Explicit per-request environment without changing host process globals.
    /// Raw names/values use the ordinary bounded guest snapshot contract. The
    /// input is copied into this owner and then into fresh readonly guest storage
    /// per invocation. An absent history selects ordinary fresh emission.
    #[cfg(feature = "jit-template-session")]
    pub fn with_session_inputs(program: &'program Program, limits: &Limits,
        history: Option<&crate::TemplateHistory>, environment: &[(Vec<u8>,Vec<u8>)]) -> Result<Self,String> {
        let started = std::time::Instant::now();
        Self::check_mode(limits)?;
        if program.version & crate::PARTIAL_VALIDATION != 0 {
            return Err("session inputs require fully checked bytecode".into());
        }
        let context = if let Some(history) = history {Some(history.context(program)?)}
            else {crate::validate(program)?;None};
        Self::session_validated(program, limits, context, environment, started)
    }

    /// Share one immutable validation proof across current-request workers.
    /// The caller must include ValidatedProgram construction in request costs.
    #[cfg(feature = "jit-template-session")]
    pub fn with_validated_session_inputs(program: &'program ValidatedProgram, limits: &Limits,
        history: Option<&crate::TemplateHistory>, environment: &[(Vec<u8>,Vec<u8>)]) -> Result<Self,String> {
        let started = std::time::Instant::now();
        Self::check_mode(limits)?;
        let context = history.map(|history|history.context_validated(program));
        Self::session_validated(program.program(), limits, context, environment, started)
    }

    #[cfg(feature = "jit-template-session")]
    fn session_validated(program: &'program Program, limits: &Limits,
        context: Option<std::rc::Rc<jit::cross_program_templates::Context<'program>>>,
        environment: &[(Vec<u8>,Vec<u8>)], started: std::time::Instant) -> Result<Self,String> {
        let mut jit = crate::create_jit::<false, true, false, true>(program, limits)?;
        #[cfg(feature = "jit-preparation-observer")]
        let metadata_started=std::time::Instant::now();
        let metadata = ExecutionMetadata::with_environment(program, jit.as_ref(), limits.memory, environment)?;
        #[cfg(feature = "jit-preparation-observer")]
        let session_setup_ns=Some((metadata_started.duration_since(started).as_nanos(),metadata_started.elapsed().as_nanos()));
        if let Some(context) = context {jit.as_mut().unwrap().attach_templates(context);}
        Ok(Self {program,jit,metadata,code_bytes:limits.jit_code_bytes,
            persistent_registers:limits.jit_persistent_registers,scalar_calls:limits.jit_scalar_calls,
            indirect_calls:limits.jit_indirect_calls,
            #[cfg(feature = "jit-preparation-observer")] session_setup_ns,
            preparation_nanos:started.elapsed().as_nanos()})
    }

    // Both callers above have validated this immutable Program. Keep this
    // helper private so no caller can bypass validation through the public API.
    fn new_validated(program: &'program Program, limits: &Limits,
        started: std::time::Instant) -> Result<Self, String> {
        let jit = crate::create_jit::<false, true, false, true>(program, limits)?;
        let metadata = ExecutionMetadata::new(program, jit.as_ref(), true, limits.memory)?;
        Ok(Self { program, jit, metadata, code_bytes: limits.jit_code_bytes,
            persistent_registers: limits.jit_persistent_registers,
            scalar_calls: limits.jit_scalar_calls,
            #[cfg(feature = "jit-preparation-observer")] session_setup_ns:None,
            indirect_calls: limits.jit_indirect_calls,
            preparation_nanos: started.elapsed().as_nanos() })
    }

    fn check_mode(limits: &Limits) -> Result<(), String> {
        if !limits.jit_resumable_calls || limits.jit_native_calls || limits.jit_native_call_stubs {
            return Err("prepared JIT requires resumable calls without native tree/stub modes".into());
        }
        Ok(())
    }

    /// Constructor cost, including validation and immutable analysis metadata.
    /// Include this cost when measuring the complete test-suite command.
    pub fn preparation_nanos(&self) -> u128 { self.preparation_nanos }

    /// Run the program's original entry with fresh guest state.
    pub fn execute(&mut self, arguments: &[u128], limits: Limits) -> Result<Execution, String> {
        self.execute_entry(self.program.entry, arguments, limits)
    }

    /// Run a checked entry with fresh guest state. This permits distinct tests
    /// to share compiled callees without sharing mutable globals or TLS.
    ///
    /// `jit_compile_nanos` reports new compilation during this invocation;
    /// code bytes/functions describe the complete retained code cache. Guest
    /// instruction counts, memory peaks and transition counts are per run.
    /// Runtime limits may change; code-generation options must match `new`.
    pub fn execute_entry(&mut self, entry: usize, arguments: &[u128], limits: Limits) -> Result<Execution, String> {
        Self::check_mode(&limits)?;
        if limits.jit_code_bytes != self.code_bytes || limits.jit_persistent_registers != self.persistent_registers
            || limits.jit_scalar_calls != self.scalar_calls
            || limits.jit_indirect_calls != self.indirect_calls {
            return Err("prepared JIT code-generation options changed".into());
        }
        let before = self.jit.as_ref().unwrap().compile_nanos;
        // Guest state lives entirely inside this call. Its ordinary Result
        // cleanup also handles failure; compiled code never owns that state.
        let mut execution = crate::execute_prepared_impl::<false, true, false, false, true>(
            self.program, entry, arguments, limits, None, &mut self.jit, &self.metadata)?;
        execution.jit_compile_nanos = self.jit.as_ref().unwrap().compile_nanos - before;
        Ok(execution)
    }
}
