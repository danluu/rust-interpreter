//! A development-oriented, standalone bytecode machine. No compiler, JIT
//! library, or external interpreter participates in execution.
use serde::{Deserialize, Serialize};
#[cfg(test)]
extern crate self as rust_interp_bytecode;
mod heap;
mod linear_memory;
mod frames;
mod native_execution;
mod native_continuation;
mod jit;
mod float;
mod profile;
mod prepared;
mod entry_catalog;
mod optimize;
mod control_flow;
mod inline;
#[cfg(test)]
mod inline_tests;
mod registers;
mod calls;
mod cpu;
mod c_allocator;
mod tls;
mod forwarding;
#[cfg(test)]
mod memory_tests;
pub use float::{FloatBinary, FloatUnary, FloatConversion};
pub use profile::{ExecutionProfile, FunctionProfile};
pub use prepared::PreparedJit;
pub use jit::{register_width_census, register_width_profile_census, register_lifetime_census, constant_call_argument_census, fold_constants};
pub use entry_catalog::{EntryCatalog, SelectedEntry};
pub use optimize::{remove_fallthrough_jumps, optimize_calls, CallOptimizationReport};
pub use control_flow::{optimize_control_flow, ControlFlowReport, FunctionControlFlowReport};
pub use inline::{transform as inline_leaves, Options as LeafInlineOptions};
pub use forwarding::{eliminate_direct_forwarders, ForwardingReport};
use frames::{Frame, Frames};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Engine {
    Interpreter,
    Jit,
}

pub const VERSION: u32 = 5;
pub const MAX_ALIGNMENT: usize = 4096;
/// The upper header bit records partial validation; the wire format is the same.
pub const PARTIAL_VALIDATION: u32 = 1 << 16;
pub type Reg = u32;
/// Function pointers are opaque guest handles, never executable host addresses.
pub const FUNCTION_POINTER_TAG: u64 = 1 << 63;
pub const HEAP_POINTER_TAG: u64 = 1 << 62;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Program {
    pub version: u32,
    pub target: String,
    pub entry: usize,
    pub functions: Vec<Function>,
    pub data: Vec<u8>,
    /// Mutable static initializers, copied into a permanent heap prefix for
    /// each machine. They are never owned by the guest allocation API.
    pub statics: Vec<u8>,
    /// Mutable TLS ranges within statics. One guest thread is active at a time;
    /// the selected-test root restores these initializers between tests.
    pub thread_locals: Vec<Slot>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Function {
    pub name: String,
    pub frame_size: usize,
    pub frame_align: usize,
    pub registers: usize,
    pub args: Vec<Slot>,
    pub result: Slot,
    pub code: Vec<Op>,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct Slot {
    pub offset: usize,
    pub size: usize,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub enum Binary {
    Add,
    Sub,
    Mul,
    Div,
    Rem,
    And,
    Or,
    Xor,
    Shl,
    Shr,
    Eq,
    Ne,
    Lt,
    Le,
    Gt,
    Ge,
    Cmp,
    RotateLeft,
    RotateRight,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub enum Unary {
    Not,
    Neg,
    CountOnes,
    LeadingZeros,
    TrailingZeros,
    SwapBytes,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum Op {
    Imm {
        dst: Reg,
        value: u128,
    },
    Local {
        dst: Reg,
        offset: usize,
    },
    Load {
        dst: Reg,
        address: Reg,
        size: u8,
    },
    Store {
        address: Reg,
        src: Reg,
        size: u8,
    },
    Copy {
        dst: Reg,
        src: Reg,
        size: usize,
    },
    Binary {
        dst: Reg,
        overflow: Reg,
        op: Binary,
        a: Reg,
        b: Reg,
        bits: u8,
        signed: bool,
    },
    Unary {
        dst: Reg,
        op: Unary,
        src: Reg,
        bits: u8,
    },
    Cast {
        dst: Reg,
        src: Reg,
        from: u8,
        to: u8,
        signed: bool,
    },
    Select {
        dst: Reg,
        condition: Reg,
        yes: Reg,
        no: Reg,
    },
    Jump {
        target: usize,
    },
    Switch {
        value: Reg,
        cases: Vec<(u128, usize)>,
        otherwise: usize,
    },
    Assert {
        value: Reg,
        expected: bool,
        message: String,
    },
    Call {
        function: usize,
        args: Vec<Reg>,
        destination: Reg,
    },
    Return,
    Trap {
        message: String,
    },
    CopyDynamic {
        dst: Reg,
        src: Reg,
        size: Reg,
    },
    CompareBytes {
        dst: Reg,
        left: Reg,
        right: Reg,
        size: Reg,
    },
    CallIndirect {
        callee: Reg,
        args: Vec<Reg>,
        arg_sizes: Vec<usize>,
        destination: Reg,
        result_size: usize,
    },
    Allocate {
        dst: Reg,
        size: Reg,
        align: Reg,
        zeroed: bool,
    },
    Deallocate {
        pointer: Reg,
        size: Reg,
        align: Reg,
    },
    Reallocate {
        dst: Reg,
        pointer: Reg,
        old_size: Reg,
        align: Reg,
        new_size: Reg,
    },
    FillBytes {
        address: Reg,
        value: Reg,
        size: Reg,
    },
    FloatBinary { dst: Reg, op: FloatBinary, a: Reg, b: Reg, bits: u8 },
    FloatUnary { dst: Reg, op: FloatUnary, src: Reg, bits: u8 },
    FloatConvert { dst: Reg, kind: FloatConversion, src: Reg, from: u8, to: u8 },
    ResetThreadLocals,
    RandomBytes { dst: Reg, address: Reg, size: Reg },
    // Append new variants to preserve existing V5 opcode discriminants. Older
    // VMs reject this variant while existing programs keep their exact encoding.
    CpuFeatureQuery { dst: Reg, name: Reg, output: Reg, output_len: Reg, new_data: Reg, new_len: Reg },
    /// Darwin C allocation contracts. errno is a writable four-byte guest TLS slot.
    CAllocate { dst: Reg, count: Reg, size: Reg, errno: Reg, zeroed: bool },
    CDeallocate { pointer: Reg },
    CReallocate { dst: Reg, pointer: Reg, size: Reg, errno: Reg },
    CAlignedAllocate { dst: Reg, output: Reg, align: Reg, size: Reg },
    RegisterTlsDestructor { callback: Reg, argument: Reg },
}

fn mask(bits: u8) -> u128 {
    if bits == 128 {
        u128::MAX
    } else {
        (1u128 << bits) - 1
    }
}
fn signed(value: u128, bits: u8) -> i128 {
    ((value << (128 - bits)) as i128) >> (128 - bits)
}

/// Integer semantics are explicit in the bytecode, including overflow results.
#[inline(always)]
pub fn binary(
    op: Binary,
    a: u128,
    b: u128,
    bits: u8,
    is_signed: bool,
) -> Result<(u128, bool), String> {
    if ![8, 16, 32, 64, 128].contains(&bits) {
        return Err("invalid integer width".into());
    }
    let m = mask(bits);
    let a = a & m;
    let b_value = b & m;
    // Validated integer widths are powers of two. Mask the full shift operand
    // instead of performing a software 128-bit remainder on narrower hosts.
    let shift = (b & u128::from(bits - 1)) as u32;
    let (v, overflow) = match op {
        Binary::Add | Binary::Sub | Binary::Mul => {
            let (v, unsigned_overflow) = match op {
                Binary::Add => a.overflowing_add(b_value),
                Binary::Sub => a.overflowing_sub(b_value),
                _ => a.overflowing_mul(b_value),
            };
            let overflow = if is_signed {
                let sa = signed(a, bits);
                let sb = signed(b_value, bits);
                let (n, overflow128) = match op {
                    Binary::Add => sa.overflowing_add(sb),
                    Binary::Sub => sa.overflowing_sub(sb),
                    _ => sa.overflowing_mul(sb),
                };
                overflow128 || signed(n as u128 & m, bits) != n
            } else {
                unsigned_overflow || v & !m != 0
            };
            (v, overflow)
        }
        Binary::Div | Binary::Rem => {
            if b_value == 0 {
                return Err("integer division by zero".into());
            }
            if is_signed {
                let sa = signed(a, bits);
                let sb = signed(b_value, bits);
                if sa == signed(1u128 << (bits - 1), bits) && sb == -1 {
                    return Err("signed division overflow".into());
                }
                (
                    if matches!(op, Binary::Div) {
                        sa / sb
                    } else {
                        sa % sb
                    } as u128,
                    false,
                )
            } else {
                (
                    if matches!(op, Binary::Div) {
                        a / b_value
                    } else {
                        a % b_value
                    },
                    false,
                )
            }
        }
        Binary::And => (a & b_value, false),
        Binary::Or => (a | b_value, false),
        Binary::Xor => (a ^ b_value, false),
        Binary::Shl => (a << shift, false),
        Binary::Shr => (
            if is_signed {
                (signed(a, bits) >> shift) as u128
            } else {
                a >> shift
            },
            false,
        ),
        Binary::Eq => (u128::from(a == b_value), false),
        Binary::Ne => (u128::from(a != b_value), false),
        Binary::Lt | Binary::Le | Binary::Gt | Binary::Ge | Binary::Cmp => {
            // Keep comparison and sign-extension work off arithmetic and
            // bitwise paths, where these values are never consumed.
            let (less, greater) = if is_signed {
                let sa = signed(a, bits);
                let sb = signed(b_value, bits);
                (sa < sb, sa > sb)
            } else {
                (a < b_value, a > b_value)
            };
            let value = match op {
                Binary::Lt => u128::from(less),
                Binary::Le => u128::from(!greater),
                Binary::Gt => u128::from(greater),
                Binary::Ge => u128::from(!less),
                Binary::Cmp => if less { 255 } else { u128::from(greater) },
                _ => unreachable!(),
            };
            (value, false)
        }
        Binary::RotateLeft => (
            if shift == 0 {
                a
            } else {
                (a << shift) | (a >> (u32::from(bits) - shift))
            },
            false,
        ),
        Binary::RotateRight => (
            if shift == 0 {
                a
            } else {
                (a >> shift) | (a << (u32::from(bits) - shift))
            },
            false,
        ),
    };
    Ok((v & m, overflow))
}

/// Default live guest allocation count, independent of guest byte storage.
pub const DEFAULT_ALLOCATION_LIMIT: usize = 100_000;
/// Bound allocator bookkeeping even when the caller requests a larger budget.
pub const MAX_ALLOCATION_LIMIT: usize = 1_000_000;

#[derive(Clone)]
pub struct Limits {
    pub memory: usize,
    /// Live guest allocations, including temporary replacements during realloc.
    /// Zero prohibits allocation; values above MAX_ALLOCATION_LIMIT are rejected.
    pub allocations: usize,
    pub instructions: u64,
    pub frames: usize,
    /// Native code budget, at most 16 MiB. Declined functions use our interpreter.
    pub jit_code_bytes: usize,
    /// Experimental complete acyclic native call trees; requires Engine::Jit.
    pub jit_native_calls: bool,
    /// Also link outer direct Calls with ordinary regions. Requires native calls.
    pub jit_native_call_stubs: bool,
    /// Experimental full-width register pairs retained across native edges.
    pub jit_persistent_registers: bool,
    /// Experimental native Calls/Returns with exact guest-frame continuations.
    /// Requires JIT and cannot be combined with the tree/stub experiment.
    pub jit_resumable_calls: bool,
    /// Diagnostic only: create a new directory containing published JIT bytes
    /// and address ranges after successful execution. Requires Engine::Jit.
    pub jit_code_dump: Option<std::path::PathBuf>,
}
impl Default for Limits {
    fn default() -> Self {
        Self {
            memory: 64 * 1024 * 1024,
            allocations: DEFAULT_ALLOCATION_LIMIT,
            instructions: 100_000_000,
            frames: 4096,
            jit_code_bytes: jit::MAX_CODE_BYTES,
            jit_native_calls: false,
            jit_native_call_stubs: false,
            jit_persistent_registers: false,
            jit_resumable_calls: false,
            jit_code_dump: None,
        }
    }
}

#[derive(Debug)]
pub struct Execution {
    pub value: u128,
    pub instructions: u64,
    pub peak_memory: usize,
    pub jit_bytes: usize,
    pub jit_operations: usize,
    pub jit_compiled_functions: usize,
    pub jit_declined_functions: usize,
    pub jit_compile_nanos: u128,
    pub jit_instructions: u64,
    /// Host-to-generated-code calls; one call can execute several linked blocks.
    pub jit_entries: u64,
    pub jit_tree_entries: u64,
    pub jit_tree_calls: u64,
    pub jit_tree_instructions: u64,
    pub jit_tree_bytes: usize,
    pub jit_tree_operations: usize,
    pub jit_tree_compiled_functions: usize,
    pub jit_tree_declined_functions: usize,
    pub jit_tree_compile_nanos: u128,
    pub jit_call_stubs: usize,
    pub jit_stub_calls: u64,
    /// Published ordinary/tree functions with persistent native assignments.
    pub jit_register_functions: usize,
    pub jit_register_pairs: usize,
    pub jit_liveness_declines: usize,
    pub jit_resumable_calls: u64,
    pub jit_resumable_returns: u64,
}

struct Memory {
    bytes: linear_memory::LinearMemory,
    heap: heap::Heap,
    limit: usize,
    readonly_end: usize,
    peak: usize,
    auxiliary_bytes: usize,
}
impl Memory {
    fn reserve_frame(&mut self, size: usize, align: usize) -> Result<usize, String> {
        let base = self
            .bytes
            .len()
            .checked_add(align - 1)
            .ok_or("frame alignment overflow")?
            & !(align - 1);
        let end = base
            .checked_add(size.max(1))
            .ok_or("memory size overflow")?;
        if end
            .checked_add(self.heap.bytes.len())
            .and_then(|n| n.checked_add(self.auxiliary_bytes))
            .is_none_or(|n| n > self.limit)
        {
            return Err("interpreter memory limit exceeded".into());
        }
        self.bytes.resize(end, 0);
        self.peak = self.peak.max(self.total_len());
        Ok(base)
    }
    fn total_len(&self) -> usize {
        self.bytes.len() + self.heap.bytes.len() + self.auxiliary_bytes
    }
    fn heap_budget(&self, registers: usize) -> usize {
        self.limit
            .saturating_sub(self.bytes.len())
            .saturating_sub(registers)
            .saturating_sub(self.auxiliary_bytes)
    }
    #[inline(always)]
    fn range(&self, address: usize, size: usize) -> Result<(bool, std::ops::Range<usize>), String> {
        // Empty Rust slices may use aligned dangling pointers. No bytes are
        // read or written, so do not require such a pointer to name an arena.
        if size == 0 {
            return Ok((false, 0..0));
        }
        let is_heap = address >= heap::TAG;
        let address = if is_heap {
            address - heap::TAG
        } else {
            address
        };
        let len = if is_heap {
            self.heap.bytes.len()
        } else {
            self.bytes.len()
        };
        let end = address.checked_add(size).ok_or("address overflow")?;
        if address == 0 || end > len {
            return Err("invalid guest memory access".into());
        }
        Ok((is_heap, address..end))
    }
    // Keep arena selection and its range check in the scalar-load caller.
    // An extra helper call here is measurable in long interpreted tests.
    #[inline(always)]
    fn read(&self, address: usize, size: usize) -> Result<&[u8], String> {
        let (is_heap, range) = self.range(address, size)?;
        Ok(if is_heap {
            &self.heap.bytes[range]
        } else {
            &self.bytes[range]
        })
    }
    #[inline(always)]
    fn load(&self, address: usize, size: usize) -> Result<u128, String> {
        if size > 16 {
            return Err("scalar exceeds 128 bits".into());
        }
        let source = self.read(address, size)?;
        // Constant-width copies lower to unaligned scalar loads. Keep the
        // byte-assembly fallback for the other supported aggregate widths.
        Ok(match size {
            1 => u128::from(source[0]),
            2 => u128::from(u16::from_le_bytes(source.try_into().unwrap())),
            4 => u128::from(u32::from_le_bytes(source.try_into().unwrap())),
            8 => u128::from(u64::from_le_bytes(source.try_into().unwrap())),
            16 => u128::from_le_bytes(source.try_into().unwrap()),
            _ => {
                let mut value = [0u8; 16];
                value[..size].copy_from_slice(source);
                u128::from_le_bytes(value)
            }
        })
    }
    #[inline(always)]
    fn store(&mut self, address: usize, size: usize, value: u128) -> Result<(), String> {
        if size > 16 {
            return Err("scalar exceeds 128 bits".into());
        }
        let (is_heap, range) = self.range(address, size)?;
        if !is_heap && size != 0 && address < self.readonly_end {
            return Err("write to read-only guest memory".into());
        }
        let destination = if is_heap {
            &mut self.heap.bytes[range]
        } else {
            &mut self.bytes[range]
        };
        match size {
            1 => destination[0] = value as u8,
            2 => destination.copy_from_slice(&(value as u16).to_le_bytes()),
            4 => destination.copy_from_slice(&(value as u32).to_le_bytes()),
            8 => destination.copy_from_slice(&(value as u64).to_le_bytes()),
            16 => destination.copy_from_slice(&value.to_le_bytes()),
            _ => destination.copy_from_slice(&value.to_le_bytes()[..size]),
        }
        Ok(())
    }
    fn copy(&mut self, src: usize, dst: usize, size: usize) -> Result<(), String> {
        let (src_heap, from) = self.range(src, size)?;
        let (dst_heap, to) = self.range(dst, size)?;
        if !dst_heap && size != 0 && dst < self.readonly_end {
            return Err("write to read-only guest memory".into());
        }
        match (src_heap, dst_heap) {
            (false, false) => self.bytes.copy_within(from, to.start),
            (true, true) => self.heap.bytes.copy_within(from, to.start),
            (false, true) => self.heap.bytes[to].copy_from_slice(&self.bytes[from]),
            (true, false) => self.bytes[to].copy_from_slice(&self.heap.bytes[from]),
        }
        Ok(())
    }
    fn fill(&mut self, address: usize, value: u8, size: usize) -> Result<(), String> {
        let (is_heap, range) = self.range(address, size)?;
        if !is_heap && size != 0 && address < self.readonly_end {
            return Err("write to read-only guest memory".into());
        }
        if is_heap {
            self.heap.bytes[range].fill(value);
        } else {
            self.bytes[range].fill(value);
        }
        Ok(())
    }
    fn random_bytes(&mut self, address: usize, size: usize) -> Result<u128, String> {
        let (is_heap, range) = self.range(address, size)?;
        if !is_heap && size != 0 && address < self.readonly_end {
            return Err("write to read-only guest memory".into());
        }
        let destination = if is_heap { &mut self.heap.bytes[range] } else { &mut self.bytes[range] };
        #[cfg(target_os = "macos")]
        {
            unsafe extern "C" {
                fn CCRandomGenerateBytes(bytes: *mut std::ffi::c_void, count: usize) -> i32;
            }
            // The entire guest range has been validated. Only a borrowed host
            // slice reaches CommonCrypto; it neither escapes nor resizes here.
            let status = unsafe { CCRandomGenerateBytes(destination.as_mut_ptr().cast(), destination.len()) };
            Ok(status as u32 as u128)
        }
        #[cfg(not(target_os = "macos"))]
        {
            let _ = destination;
            Err("CommonCrypto randomness requires macOS".into())
        }
    }
}

/// Every call starts a fresh machine. Guest addresses are offsets into this
/// machine's memory; they can never be dereferenced as host pointers.
pub fn execute(program: &Program, arguments: &[u128], limits: Limits) -> Result<Execution, String> {
    execute_with_engine(program, arguments, limits, Engine::Interpreter)
}

pub fn execute_with_engine(
    program: &Program,
    arguments: &[u128],
    limits: Limits,
    engine: Engine,
) -> Result<Execution, String> {
    execute_observed::<false>(program, arguments, limits, engine, None)
}

/// Diagnostic execution counts. Instrumented timings are not benchmark results.
/// The ordinary entry point uses a separate, uninstrumented specialization.
pub fn execute_profiled(
    program: &Program,
    arguments: &[u128],
    limits: Limits,
    engine: Engine,
) -> Result<(Execution, ExecutionProfile), String> {
    validate(program)?;
    let mut profile = ExecutionProfile::new(program);
    let execution = execute_observed::<true>(program, arguments, limits, engine, Some(&mut profile))?;
    Ok((execution, profile))
}

fn execute_observed<const PROFILE: bool>(
    program: &Program,
    arguments: &[u128],
    limits: Limits,
    engine: Engine,
    profile: Option<&mut ExecutionProfile>,
) -> Result<Execution, String> {
    // Select once at entry. Each loop specialization can omit the other
    // engine's transition path and its temporaries completely.
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
        return execute_impl::<PROFILE, true, false, false, true>(program, arguments, limits, profile);
    }
    match engine {
        Engine::Interpreter if limits.jit_native_calls => Err("native calls require the JIT engine".into()),
        Engine::Interpreter => execute_impl::<PROFILE, false, false, false, false>(program, arguments, limits, profile),
        Engine::Jit if limits.jit_native_call_stubs => execute_impl::<PROFILE, true, true, true, false>(program, arguments, limits, profile),
        Engine::Jit if limits.jit_native_calls => execute_impl::<PROFILE, true, true, false, false>(program, arguments, limits, profile),
        Engine::Jit => execute_impl::<PROFILE, true, false, false, false>(program, arguments, limits, profile),
    }
}

fn execute_impl<const PROFILE: bool, const USE_JIT: bool, const NATIVE_CALLS: bool, const CALL_STUBS: bool, const RESUMABLE: bool>(
    program: &Program,
    arguments: &[u128],
    limits: Limits,
    profile: Option<&mut ExecutionProfile>,
) -> Result<Execution, String> {
    validate(program)?;
    if limits.allocations > MAX_ALLOCATION_LIMIT {
        return Err(format!("live allocation limit exceeds supported maximum of {MAX_ALLOCATION_LIMIT}"));
    }
    let mut jit = create_jit::<PROFILE, USE_JIT, CALL_STUBS, RESUMABLE>(program, &limits)?;
    let metadata = ExecutionMetadata::new(program, jit.as_ref(), RESUMABLE);
    execute_prepared_impl::<PROFILE, USE_JIT, NATIVE_CALLS, CALL_STUBS, RESUMABLE>(
        program, program.entry, arguments, limits, profile, &mut jit, &metadata)
}

fn create_jit<'program, const PROFILE: bool, const USE_JIT: bool, const CALL_STUBS: bool, const RESUMABLE: bool>(
    program: &'program Program, limits: &Limits,
) -> Result<Option<jit::Jit<'program>>, String> {
    let started = std::time::Instant::now();
    let mut jit = if USE_JIT {
        Some(if RESUMABLE {
            jit::Jit::new_resumable(program, PROFILE, limits.jit_code_bytes, limits.jit_persistent_registers)?
        } else if limits.jit_persistent_registers {
            jit::Jit::new_with_options(program, PROFILE, limits.jit_code_bytes, CALL_STUBS, true)?
        } else if CALL_STUBS {
            jit::Jit::new_with_call_stubs(program, PROFILE, limits.jit_code_bytes, true)?
        } else {
            jit::Jit::new(program, PROFILE, limits.jit_code_bytes)?
        })
    } else { None };
    if let Some(jit) = &mut jit { jit.compile_nanos = started.elapsed().as_nanos(); }
    Ok(jit)
}

struct ExecutionMetadata {
    needs_register_zeroes: Vec<bool>,
    local_call_arguments: Vec<Vec<bool>>,
}
impl ExecutionMetadata {
    fn new(program: &Program, jit: Option<&jit::Jit<'_>>, resumable: bool) -> Self {
        Self {
            needs_register_zeroes: if resumable {
                jit.unwrap().resumable_register_zeroes().to_vec()
            } else { program.functions.iter().map(registers::needs_initial_zeroes).collect() },
            local_call_arguments: calls::local_arguments(program),
        }
    }
}

fn execute_prepared_impl<'program, const PROFILE: bool, const USE_JIT: bool, const NATIVE_CALLS: bool, const CALL_STUBS: bool, const RESUMABLE: bool>(
    program: &'program Program,
    entry_id: usize,
    arguments: &[u128],
    limits: Limits,
    mut profile: Option<&mut ExecutionProfile>,
    jit: &mut Option<jit::Jit<'program>>,
    metadata: &ExecutionMetadata,
) -> Result<Execution, String> {
    if limits.allocations > MAX_ALLOCATION_LIMIT {
        return Err(format!("live allocation limit exceeds supported maximum of {MAX_ALLOCATION_LIMIT}"));
    }
    let mut jit_instructions = 0;
    let mut jit_entries = 0;
    let mut resumable_calls = 0;
    let mut resumable_returns = 0;
    let resumable_profiles: Vec<_> = if RESUMABLE && PROFILE {
        profile.as_deref_mut().unwrap().functions.iter_mut().map(|f| f.jit_blocks.as_mut_ptr()).collect()
    } else { vec![] };
    let mut native = if NATIVE_CALLS { Some(native_execution::Context::new(profile.as_deref_mut())) } else { None };
    if limits.frames == 0 {
        return Err("interpreter call-depth limit exceeded".into());
    }
    if program.version & !PARTIAL_VALIDATION != VERSION {
        return Err("bytecode version mismatch".into());
    }
    let entry = program
        .functions
        .get(entry_id)
        .ok_or("missing entry function")?;
    if arguments.len() != entry.args.len() {
        return Err("wrong entry argument count".into());
    }
    if program.data.len().checked_add(program.statics.len()).is_none_or(|n| n > limits.memory) {
        return Err("initial guest data exceeds memory limit".into());
    }
    let mut memory = Memory {
        bytes: program.data.clone().into(),
        heap: heap::Heap::with_statics(&program.statics, limits.allocations),
        limit: limits.memory,
        readonly_end: program.data.len(),
        peak: 0,
        auxiliary_bytes: 0,
    };
    memory.bytes.resize(memory.bytes.len().max(16), 0);
    let base = memory.reserve_frame(entry.frame_size, entry.frame_align)?;
    let mut register_bytes = entry
        .registers
        .checked_mul(16)
        .ok_or("register size overflow")?;
    if register_bytes
        .checked_add(memory.total_len())
        .is_none_or(|n| n > limits.memory)
    {
        return Err("interpreter working-memory limit exceeded".into());
    }
    for (slot, value) in entry.args.iter().zip(arguments) {
        if slot.size < 16 && *value >> (slot.size * 8) != 0 {
            return Err("entry argument exceeds its integer width".into());
        }
        memory.store(base + slot.offset, slot.size, *value)?;
    }
    // One reusable stack avoids allocating/freeing a register vector at every
    // guest call. Registers remain separate from addressable guest memory.
    // Host elements always stay initialized. On reuse, functions proven to
    // overwrite every register before reading it need no repeated clearing.
    // Other functions retain the bytecode's initial-zero semantics.
    let needs_register_zeroes = &metadata.needs_register_zeroes;
    let local_call_arguments = &metadata.local_call_arguments;
    let mut registers = vec![0; entry.registers];
    let mut frames = Frames::from(Frame {
        function: entry_id,
        pc: 0,
        base,
        register_base: 0,
        return_address: 0,
        tls_callback: false,
    });
    prepare_jit::<PROFILE>(jit, entry_id, &mut profile)?;
    let mut steps = 0;
    let mut tls = tls::Tls::default();
    let value = 'execution: loop {
        if steps >= limits.instructions {
            return Err("interpreter instruction limit exceeded".into());
        }
        if RESUMABLE {
            let entry = *frames.last().ok_or("missing frame")?;
            let jit = jit.as_ref().unwrap();
            if let Some(block) = jit.blocks[entry.function].get(entry.pc).copied().flatten() {
                if (block.end - entry.pc) as u64 <= limits.instructions - steps {
                    // SAFETY: this program is validated and all guest backing,
                    // descriptors, profile arrays and native metadata are owned
                    // exclusively by this synchronous VM. No borrowed top Frame
                    // survives the call; descendants may become the new top.
                    let run = unsafe { jit.run_resumable(block, limits.instructions - steps,
                        &limits, &mut memory, &mut registers, &mut frames, &mut register_bytes,
                        &resumable_profiles) }?;
                    steps += run.instructions;
                    jit_instructions += run.instructions;
                    jit_entries += 1;
                    resumable_calls += run.calls;
                    resumable_returns += run.returns;
                    if steps >= limits.instructions { return Err("interpreter instruction limit exceeded".into()); }
                }
            }
        }
        let active_frames = frames.len();
        let frame = frames.last_mut().ok_or("missing frame")?;
        if !RESUMABLE { if let Some(jit) = jit.as_mut() {
            if let Some(block) = jit.blocks[frame.function].get(frame.pc).copied().flatten() {
                let count = (block.end - frame.pc) as u64;
                // Interpret the tail when the budget is smaller than a block,
                // preserving exactly which instruction may execute next.
                if count <= limits.instructions - steps {
                    let profile_hits = if PROFILE {
                        profile.as_deref_mut().unwrap().functions[frame.function].jit_blocks.as_mut_ptr()
                    } else {
                        std::ptr::null_mut()
                    };
                    // SAFETY: the validated current function owns this emitted
                    // entry and register/frame ranges. Guest arenas, registers
                    // and optional profile counters remain live and exclusive;
                    // no VM allocation, frame change or code append occurs
                    // while generated code runs. Jit is confined to this thread.
                    let (next, executed) = if CALL_STUBS && jit.region_plans[frame.function].depth != 0 {
                        native.as_mut().unwrap().run_regions::<PROFILE>(jit, block,
                            frame.function, frame.pc, frame.base, frame.register_base,
                            register_bytes / 16, active_frames, limits.instructions - steps,
                            &limits, &mut memory, &mut registers, &mut profile)?
                    } else { unsafe {
                        jit.run(
                            block,
                            jit.blocks[frame.function].len(),
                            limits.instructions - steps,
                            profile_hits,
                            registers[frame.register_base..].as_mut_ptr(),
                            frame.base,
                            memory.bytes.as_mut_ptr(),
                            memory.bytes.len(),
                            memory.readonly_end,
                            memory.heap.bytes.as_mut_ptr(),
                            memory.heap.bytes.len(),
                        )
                    }? };
                    frame.pc = next;
                    steps += executed;
                    jit_instructions += executed;
                    jit_entries += 1;
                    // Compiled successors are linked inside generated code.
                    // A successful return therefore leaves an unsupported or
                    // short region, or a block that cannot fit the remaining
                    // budget. An unready Call stub can also return its own PC
                    // with zero progress. Dispatch that operation once, without
                    // repeating the loop header and JIT-eligibility lookup.
                    // Exhaustion must still win over a following return/fault.
                    if steps >= limits.instructions {
                        return Err("interpreter instruction limit exceeded".into());
                    }
                }
            }
        } }
        let function = &program.functions[frame.function];
        let r = &mut registers[frame.register_base..frame.register_base + function.registers];
        // Keep these views until a frame transition. JIT specializations still
        // execute exactly one fallback instruction before the next native entry.
        'dispatch: loop {
            steps += 1;
            let instruction = function.code.get(frame.pc).ok_or("invalid bytecode PC")?;
            if PROFILE {
                profile.as_deref_mut().unwrap().functions[frame.function].interpreted[frame.pc] += 1;
            }
            frame.pc += 1;
            // The entry validation also covers callers using in-memory programs.
            match instruction {
                Op::ResetThreadLocals => {
                    if frames.len() != 1 || tls.completion.is_some() {
                        return Err("thread-local reset requires the root frame".into());
                    }
                    tls.completion = Some(tls::Completion::Reset);
                    tls.advance(program, &mut memory, &mut frames, &mut registers,
                        &mut register_bytes, &needs_register_zeroes, &limits)?;
                    if let Some(frame) = frames.last() { prepare_jit::<PROFILE>(jit, frame.function, &mut profile)?; }
                    break 'dispatch;
                }
                Op::RegisterTlsDestructor { callback, argument } => {
                    tls.register(program, &mut memory, register_bytes,
                        r[*callback as usize], r[*argument as usize])?;
                }
                Op::RandomBytes { dst, address, size } => {
                    r[*dst as usize] = memory.random_bytes(r[*address as usize] as usize, r[*size as usize] as usize)?;
                }
                Op::CpuFeatureQuery { dst, name, output, output_len, new_data, new_len } => {
                    r[*dst as usize] = memory.cpu_feature_query(r[*name as usize] as usize,
                        r[*output as usize] as usize, r[*output_len as usize] as usize,
                        r[*new_data as usize] as usize, r[*new_len as usize] as usize)?;
                }
                Op::CAllocate { dst, count, size, errno, zeroed } => {
                    r[*dst as usize] = memory.c_allocate(r[*count as usize], r[*size as usize],
                        r[*errno as usize], *zeroed, register_bytes)?;
                }
                Op::CDeallocate { pointer } => memory.c_deallocate(r[*pointer as usize])?,
                Op::CReallocate { dst, pointer, size, errno } => {
                    r[*dst as usize] = memory.c_reallocate(r[*pointer as usize], r[*size as usize],
                        r[*errno as usize], register_bytes)?;
                }
                Op::CAlignedAllocate { dst, output, align, size } => {
                    r[*dst as usize] = memory.c_aligned_allocate(r[*output as usize], r[*align as usize],
                        r[*size as usize], register_bytes)?;
                }
                Op::Imm { dst, value } => r[*dst as usize] = *value,
                Op::Local { dst, offset } => r[*dst as usize] = (frame.base + offset) as u128,
                Op::Load { dst, address, size } => {
                    r[*dst as usize] = memory.load(r[*address as usize] as usize, *size as usize)?
                }
                Op::Store { address, src, size } => memory.store(
                    r[*address as usize] as usize,
                    *size as usize,
                    r[*src as usize],
                )?,
                Op::Copy { dst, src, size } => {
                    memory.copy(r[*src as usize] as usize, r[*dst as usize] as usize, *size)?
                }
                Op::CopyDynamic { dst, src, size } => memory.copy(
                    r[*src as usize] as usize,
                    r[*dst as usize] as usize,
                    r[*size as usize] as usize,
                )?,
                Op::FillBytes {
                    address,
                    value,
                    size,
                } => memory.fill(
                    r[*address as usize] as usize,
                    r[*value as usize] as u8,
                    r[*size as usize] as usize,
                )?,
                Op::CompareBytes {
                    dst,
                    left,
                    right,
                    size,
                } => {
                    let count = r[*size as usize] as usize;
                    let left = memory.read(r[*left as usize] as usize, count)?;
                    let right = memory.read(r[*right as usize] as usize, count)?;
                    // The Rust intrinsic specifies the sign, not the magnitude.
                    // Check both complete ranges before examining any bytes.
                    let ordering = left.cmp(right);
                    r[*dst as usize] = match ordering {
                        std::cmp::Ordering::Less => u32::MAX as u128,
                        std::cmp::Ordering::Equal => 0,
                        std::cmp::Ordering::Greater => 1,
                    };
                }
                Op::FloatBinary { dst, op, a, b, bits } => {
                    r[*dst as usize] = float::binary(*op, r[*a as usize], r[*b as usize], *bits)?;
                }
                Op::FloatUnary { dst, op, src, bits } => {
                    r[*dst as usize] = float::unary(*op, r[*src as usize], *bits)?;
                }
                Op::FloatConvert { dst, kind, src, from, to } => {
                    r[*dst as usize] = float::convert(*kind, r[*src as usize], *from, *to)?;
                }
                Op::Allocate {
                    dst,
                    size,
                    align,
                    zeroed,
                } => {
                    let budget = memory.heap_budget(register_bytes);
                    r[*dst as usize] = memory.heap.allocate(
                        r[*size as usize] as usize,
                        r[*align as usize] as usize,
                        budget,
                        *zeroed,
                    )? as u128;
                    memory.peak = memory.peak.max(memory.total_len());
                }
                Op::Deallocate {
                    pointer,
                    size,
                    align,
                } => {
                    memory.heap.deallocate(
                        r[*pointer as usize] as usize,
                        r[*size as usize] as usize,
                        r[*align as usize] as usize,
                    )?;
                }
                Op::Reallocate {
                    dst,
                    pointer,
                    old_size,
                    align,
                    new_size,
                } => {
                    let budget = memory.heap_budget(register_bytes);
                    r[*dst as usize] = memory.heap.reallocate(
                        r[*pointer as usize] as usize,
                        r[*old_size as usize] as usize,
                        r[*align as usize] as usize,
                        r[*new_size as usize] as usize,
                        budget,
                    )? as u128;
                    memory.peak = memory.peak.max(memory.total_len());
                }
                Op::Binary {
                    dst,
                    overflow,
                    op,
                    a,
                    b,
                    bits,
                    signed,
                } => {
                    let (value, over) = binary(*op, r[*a as usize], r[*b as usize], *bits, *signed)?;
                    r[*dst as usize] = value;
                    r[*overflow as usize] = u128::from(over);
                }
                Op::Unary { dst, op, src, bits } => {
                    let value = r[*src as usize] & mask(*bits);
                    r[*dst as usize] = match op {
                        Unary::Not => !value & mask(*bits),
                        Unary::Neg => value.wrapping_neg() & mask(*bits),
                        Unary::CountOnes => value.count_ones() as u128,
                        Unary::LeadingZeros => {
                            (value.leading_zeros() - (128 - u32::from(*bits))) as u128
                        }
                        Unary::TrailingZeros => value.trailing_zeros().min(u32::from(*bits)) as u128,
                        Unary::SwapBytes => value.swap_bytes() >> (128 - *bits),
                    };
                }
                Op::Cast {
                    dst,
                    src,
                    from,
                    to,
                    signed: is_signed,
                } => {
                    let value = r[*src as usize];
                    r[*dst as usize] = if *is_signed {
                        signed(value, *from) as u128
                    } else {
                        value & mask(*from)
                    } & mask(*to);
                }
                Op::Jump { target } => frame.pc = *target,
                Op::Select {
                    dst,
                    condition,
                    yes,
                    no,
                } => {
                    r[*dst as usize] = r[if r[*condition as usize] != 0 {
                        *yes
                    } else {
                        *no
                    } as usize]
                }
                Op::Switch {
                    value,
                    cases,
                    otherwise,
                } => {
                    frame.pc = cases
                        .iter()
                        .find(|(n, _)| *n == r[*value as usize])
                        .map_or(*otherwise, |(_, t)| *t)
                }
                Op::Assert {
                    value,
                    expected,
                    message,
                } => {
                    if (r[*value as usize] != 0) != *expected {
                        return Err(format!("guest assertion: {message} in {}", function.name));
                    }
                }
                Op::Trap { message } => {
                    return Err(format!("guest trap: {message} in {}", function.name));
                }
                Op::Call {
                    args, destination, ..
                }
                | Op::CallIndirect {
                    args, destination, ..
                } => {
                    let callee_id = match instruction {
                        Op::Call { function, .. } => *function,
                        Op::CallIndirect {
                            callee,
                            arg_sizes,
                            result_size,
                            ..
                        } => {
                            let pointer = r[*callee as usize];
                            if pointer > u64::MAX as u128 || pointer as u64 & FUNCTION_POINTER_TAG == 0
                            {
                                return Err("invalid guest function pointer".into());
                            }
                            let id = ((pointer as u64 & !FUNCTION_POINTER_TAG) as usize)
                                .checked_sub(1)
                                .ok_or("null guest function handle")?;
                            let function = program
                                .functions
                                .get(id)
                                .ok_or("invalid guest function handle")?;
                            if function.args.len() != arg_sizes.len()
                                || function
                                    .args
                                    .iter()
                                    .zip(arg_sizes)
                                    .any(|(slot, size)| slot.size != *size)
                                || function.result.size != *result_size
                            {
                                return Err("guest function pointer signature mismatch".into());
                            }
                            id
                        }
                        _ => unreachable!(),
                    };
                    let callee = &program.functions[callee_id];
                    let return_address = r[*destination as usize] as usize;
                    let base = memory.reserve_frame(callee.frame_size, callee.frame_align)?;
                    let added = callee
                        .registers
                        .checked_mul(16)
                        .ok_or("register size overflow")?;
                    register_bytes = register_bytes
                        .checked_add(added)
                        .ok_or("register size overflow")?;
                    if register_bytes
                        .checked_add(memory.total_len())
                        .is_none_or(|n| n > limits.memory)
                    {
                        return Err("interpreter working-memory limit exceeded".into());
                    }
                    if local_call_arguments[frame.function][frame.pc - 1] {
                        // Validation and the per-block proof establish that these
                        // sources lie inside the live caller frame. Callee slots
                        // lie inside the frame just reserved above. Keep argument
                        // order even when callee slots overlap.
                        for (src, slot) in args.iter().zip(&callee.args) {
                            let source = r[*src as usize] as usize;
                            memory.bytes.copy_within(source..source + slot.size, base + slot.offset);
                        }
                    } else {
                        for (src, slot) in args.iter().zip(&callee.args) {
                            memory.copy(r[*src as usize] as usize, base + slot.offset, slot.size)?;
                        }
                    }
                    if frames.len() >= limits.frames {
                        return Err("interpreter call-depth limit exceeded".into());
                    }
                    let register_base = register_bytes / 16 - callee.registers;
                    // register_bytes has already been checked against the live
                    // working-memory budget. No pointer survives a guest call;
                    // the JIT receives fresh storage pointers on its next entry.
                    let register_end = register_bytes / 16;
                    if register_end > registers.len() {
                        registers.resize(register_end, 0);
                    }
                    if needs_register_zeroes[callee_id] {
                        registers[register_base..register_end].fill(0);
                    }
                    if NATIVE_CALLS {
                        // The ordinary root Call has already reserved/initialized
                        // its frame, copied arguments and checked depth in VM order.
                        // A declined tree continues through the existing push path.
                        if let Some(run) = native.as_mut().unwrap().run::<PROFILE>(
                            jit.as_mut().unwrap(), callee_id, return_address, base, register_base,
                            frames.len(), limits.instructions - steps, &limits,
                            &mut memory, &mut registers, &mut profile)? {
                            steps += run;
                            jit_instructions += run;
                            jit_entries += 1;
                            register_bytes = register_base * 16;
                            continue 'execution;
                        }
                    }
                    frames.push(Frame {
                        function: callee_id,
                        pc: 0,
                        base,
                        register_base,
                        return_address,
                        tls_callback: false,
                    });
                    prepare_jit::<PROFILE>(jit, callee_id, &mut profile)?;
                    break 'dispatch;
                }
                Op::Return => {
                    let result = function.result;
                    let source = frame.base + result.offset;
                    let callback = frame.tls_callback;
                    if frames.len() == 1 && !callback {
                        let value = memory.load(source, result.size)?;
                        if tls.is_empty() { break 'execution value; }
                        tls.completion = Some(tls::Completion::Entry(value));
                        let frame = frames.pop().ok_or("missing entry frame")?;
                        register_bytes = 0;
                        memory.bytes.truncate(frame.base);
                        tls.advance(program, &mut memory, &mut frames, &mut registers,
                            &mut register_bytes, &needs_register_zeroes, &limits)?;
                        if let Some(frame) = frames.last() { prepare_jit::<PROFILE>(jit, frame.function, &mut profile)?; }
                        continue 'execution;
                    }
                    let frame = frames.pop().ok_or("missing return frame")?;
                    // Retain initialized backing elements for the next call.
                    // The active prefix, rather than retained length/capacity,
                    // remains subject to the live working-memory budget.
                    register_bytes = frame.register_base * 16;
                    if !callback { memory.copy(source, frame.return_address, result.size)?; }
                    memory.bytes.truncate(frame.base);
                    if callback {
                        if let Some(value) = tls.advance(program, &mut memory, &mut frames, &mut registers,
                            &mut register_bytes, &needs_register_zeroes, &limits)? { break 'execution value; }
                        if let Some(frame) = frames.last() { prepare_jit::<PROFILE>(jit, frame.function, &mut profile)?; }
                    }
                    break 'dispatch;
                }
            }
            if USE_JIT { break 'dispatch; }
            if steps >= limits.instructions {
                return Err("interpreter instruction limit exceeded".into());
            }
        }
    };
    if let Some(path) = &limits.jit_code_dump {
        jit.as_ref().ok_or("missing JIT for native code dump")?.dump_code(path)?;
    }
    let tree_stats = jit.as_ref().map_or((0, 0, 0, 0, 0), |j| j.tree_stats());
    Ok(Execution { value, instructions: steps, peak_memory: memory.peak,
        jit_bytes: jit.as_ref().map_or(0, |j| j.bytes),
        jit_operations: jit.as_ref().map_or(0, |j| j.operations),
        jit_compiled_functions: jit.as_ref().map_or(0, |j| j.compiled_functions),
        jit_declined_functions: jit.as_ref().map_or(0, |j| j.declined_functions),
        jit_compile_nanos: jit.as_ref().map_or(0, |j| j.compile_nanos), jit_instructions, jit_entries,
        jit_tree_entries: native.as_ref().map_or(0, |n| n.entries),
        jit_tree_calls: native.as_ref().map_or(0, |n| n.calls),
        jit_tree_instructions: native.as_ref().map_or(0, |n| n.instructions),
        jit_tree_bytes: tree_stats.0, jit_tree_operations: tree_stats.1,
        jit_tree_compiled_functions: tree_stats.2, jit_tree_declined_functions: tree_stats.3,
        jit_tree_compile_nanos: tree_stats.4,
        jit_call_stubs: jit.as_ref().map_or(0, |j| j.call_stubs),
        jit_stub_calls: native.as_ref().map_or(0, |n| n.stub_calls),
        jit_register_functions: jit.as_ref().map_or(0, |j| j.register_functions),
        jit_register_pairs: jit.as_ref().map_or(0, |j| j.register_pairs),
        jit_liveness_declines: jit.as_ref().map_or(0, |j| j.liveness_declines),
        jit_resumable_calls: resumable_calls, jit_resumable_returns: resumable_returns })
}

#[inline(always)]
fn prepare_jit<const PROFILE: bool>(jit: &mut Option<jit::Jit<'_>>, function: usize,
    profile: &mut Option<&mut ExecutionProfile>) -> Result<(), String> {
    if let Some(jit) = jit {
        if jit.ensure_function(function)? && PROFILE {
            let row = &mut profile.as_deref_mut().unwrap().functions[function];
            for (end, block) in row.jit_block_ends.iter_mut().zip(&jit.blocks[function]) {
                *end = block.map_or(0, |block| block.end);
            }
        }
    }
    Ok(())
}

/// Artifacts are local build products, but malformed files must be errors, not
/// arbitrary indexing panics or allocations. This is not a hostile-code sandbox.
pub fn validate(program: &Program) -> Result<(), String> {
    if program.version & !PARTIAL_VALIDATION != VERSION
        || program.functions.len() > 100_000
        || program.thread_locals.len() > 100_000
        || program.entry >= program.functions.len()
        || (!program.statics.is_empty() && program.statics.len() < 16)
    {
        return Err("invalid bytecode header".into());
    }
    let mut ranges = program.thread_locals.clone();
    ranges.sort_unstable_by_key(|slot| slot.offset);
    let mut end = 16;
    for slot in ranges {
        if slot.size == 0 || slot.offset < end {
            return Err("invalid or overlapping thread-local initializer".into());
        }
        end = slot.offset.checked_add(slot.size).ok_or("thread-local range overflow")?;
        if end > program.statics.len() {
            return Err("thread-local initializer outside static storage".into());
        }
    }
    for f in &program.functions {
        if f.frame_size > 16 * 1024 * 1024
            || f.registers > 1_000_000
            || f.code.is_empty()
            || !f.frame_align.is_power_of_two()
            || f.frame_align > MAX_ALIGNMENT
        {
            return Err("invalid function limits".into());
        }
        for slot in f.args.iter().chain(std::iter::once(&f.result)) {
            if slot
                .offset
                .checked_add(slot.size)
                .is_none_or(|end| end > f.frame_size)
            {
                return Err("invalid frame slot".into());
            }
        }
        let reg = |r: Reg| -> Result<(), String> {
            if (r as usize) < f.registers {
                Ok(())
            } else {
                Err("invalid register".into())
            }
        };
        let jump = |t: usize| -> Result<(), String> {
            if t < f.code.len() {
                Ok(())
            } else {
                Err("invalid branch".into())
            }
        };
        let width = |b: u8| -> Result<(), String> {
            if [8, 16, 32, 64, 128].contains(&b) {
                Ok(())
            } else {
                Err("invalid width".into())
            }
        };
        for op in &f.code {
            if matches!(op, Op::CAllocate { .. } | Op::CDeallocate { .. }
                | Op::CReallocate { .. } | Op::CAlignedAllocate { .. })
                && program.target != "aarch64-apple-darwin" {
                return Err("C allocator operations require the Darwin guest contract".into());
            }
            match op {
                Op::RegisterTlsDestructor { callback, argument } => {
                    if program.target != "aarch64-apple-darwin" {
                        return Err("TLS destructor registration requires the Darwin guest contract".into());
                    }
                    reg(*callback)?; reg(*argument)?;
                }
                Op::CAllocate { dst, count, size, errno, .. } => {
                    for r in [dst, count, size, errno] { reg(*r)?; }
                }
                Op::CDeallocate { pointer } => reg(*pointer)?,
                Op::CReallocate { dst, pointer, size, errno } => {
                    for r in [dst, pointer, size, errno] { reg(*r)?; }
                }
                Op::CAlignedAllocate { dst, output, align, size } => {
                    for r in [dst, output, align, size] { reg(*r)?; }
                }
                Op::RandomBytes { dst, address, size } => { reg(*dst)?; reg(*address)?; reg(*size)?; }
                Op::CpuFeatureQuery { dst, name, output, output_len, new_data, new_len } => {
                    for r in [dst, name, output, output_len, new_data, new_len] { reg(*r)?; }
                }
                Op::ResetThreadLocals => {}
                Op::Imm { dst, .. } => reg(*dst)?,
                Op::Local { dst, offset } => {
                    reg(*dst)?;
                    if *offset > f.frame_size {
                        return Err("invalid local offset".into());
                    }
                }
                Op::Load { dst, address, size } => {
                    reg(*dst)?;
                    reg(*address)?;
                    if *size > 16 {
                        return Err("invalid load size".into());
                    }
                }
                Op::Store { address, src, size } => {
                    reg(*address)?;
                    reg(*src)?;
                    if *size > 16 {
                        return Err("invalid store size".into());
                    }
                }
                Op::Copy { dst, src, .. } => {
                    reg(*dst)?;
                    reg(*src)?;
                }
                Op::CopyDynamic { dst, src, size } => {
                    reg(*dst)?;
                    reg(*src)?;
                    reg(*size)?;
                }
                Op::FillBytes {
                    address,
                    value,
                    size,
                } => {
                    reg(*address)?;
                    reg(*value)?;
                    reg(*size)?;
                }
                Op::CompareBytes {
                    dst,
                    left,
                    right,
                    size,
                } => {
                    reg(*dst)?;
                    reg(*left)?;
                    reg(*right)?;
                    reg(*size)?;
                }
                Op::CallIndirect {
                    callee,
                    args,
                    arg_sizes,
                    destination,
                    ..
                } => {
                    reg(*callee)?;
                    reg(*destination)?;
                    if args.len() != arg_sizes.len() {
                        return Err("invalid indirect call arity".into());
                    }
                    for r in args {
                        reg(*r)?;
                    }
                }
                Op::Allocate {
                    dst, size, align, ..
                } => {
                    reg(*dst)?;
                    reg(*size)?;
                    reg(*align)?;
                }
                Op::Deallocate {
                    pointer,
                    size,
                    align,
                } => {
                    reg(*pointer)?;
                    reg(*size)?;
                    reg(*align)?;
                }
                Op::Reallocate {
                    dst,
                    pointer,
                    old_size,
                    align,
                    new_size,
                } => {
                    reg(*dst)?;
                    reg(*pointer)?;
                    reg(*old_size)?;
                    reg(*align)?;
                    reg(*new_size)?;
                }
                Op::Binary {
                    dst,
                    overflow,
                    a,
                    b,
                    bits,
                    ..
                } => {
                    reg(*dst)?;
                    reg(*overflow)?;
                    reg(*a)?;
                    reg(*b)?;
                    width(*bits)?;
                }
                Op::FloatBinary { dst, a, b, bits, .. } => {
                    reg(*dst)?; reg(*a)?; reg(*b)?; float::width(*bits)?;
                }
                Op::FloatUnary { dst, src, bits, .. } => {
                    reg(*dst)?; reg(*src)?; float::width(*bits)?;
                }
                Op::FloatConvert { dst, kind, src, from, to } => {
                    reg(*dst)?; reg(*src)?; float::conversion_widths(*kind, *from, *to)?;
                }
                Op::Unary { dst, src, bits, .. } => {
                    reg(*dst)?;
                    reg(*src)?;
                    width(*bits)?;
                }
                Op::Cast {
                    dst, src, from, to, ..
                } => {
                    reg(*dst)?;
                    reg(*src)?;
                    width(*from)?;
                    width(*to)?;
                }
                Op::Jump { target } => jump(*target)?,
                Op::Select {
                    dst,
                    condition,
                    yes,
                    no,
                } => {
                    reg(*dst)?;
                    reg(*condition)?;
                    reg(*yes)?;
                    reg(*no)?;
                }
                Op::Switch {
                    value,
                    cases,
                    otherwise,
                } => {
                    reg(*value)?;
                    jump(*otherwise)?;
                    for (_, t) in cases {
                        jump(*t)?;
                    }
                }
                Op::Assert { value, .. } => reg(*value)?,
                Op::Call {
                    function,
                    args,
                    destination,
                } => {
                    reg(*destination)?;
                    let callee = program.functions.get(*function).ok_or("invalid callee")?;
                    if args.len() != callee.args.len() {
                        return Err(format!(
                            "invalid call arity: {} calls {} with {} arguments, expected {}",
                            f.name, callee.name, args.len(), callee.args.len()
                        ));
                    }
                    for r in args {
                        reg(*r)?;
                    }
                }
                Op::Return | Op::Trap { .. } => {}
            }
        }
    }
    Ok(())
}

/// Diagnostic snapshot only; share the retained exhaustive operand visitor.
pub fn diagnostic_visit_registers(op: &Op, read: impl FnMut(Reg), write: impl FnMut(Reg)) { registers::visit_registers(op, read, write); }
