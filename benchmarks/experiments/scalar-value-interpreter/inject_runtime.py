"""Extend the qualified artifact source with the interpreter specialization."""
import importlib.util
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent
ARTIFACT=HERE.parent/'scalar-value-abi'
spec=importlib.util.spec_from_file_location('qualified_scalar_artifact_inject',ARTIFACT/'inject.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
replace=base.replace


def inject(source):
    base.inject(source)
    directory=source/'crates/bytecode/src'
    shutil.copy2(HERE/'runtime.rs',directory/'scalar_abi_runtime.rs')
    shutil.copy2(HERE/'tests.rs',directory/'scalar_abi_runtime_tests.rs')
    with (directory/'scalar_abi.rs').open('a') as out:
        out.write('\n#[path="scalar_abi_runtime.rs"]\nmod runtime;\n')
    with (directory/'registers.rs').open('a') as out:
        out.write('\n'+(HERE/'register_inputs.rs').read_text())
    lib=directory/'lib.rs'
    header='fn execute_impl<const PROFILE: bool, const USE_JIT: bool, const NATIVE_CALLS: bool, const CALL_STUBS: bool, const RESUMABLE: bool>('
    replace(lib,header,'''fn execute_impl<const PROFILE: bool, const USE_JIT: bool, const NATIVE_CALLS: bool, const CALL_STUBS: bool, const RESUMABLE: bool>(
    program: &Program, arguments: &[u128], limits: Limits, profile: Option<&mut ExecutionProfile>,
) -> Result<Execution, String> {
    execute_core::<PROFILE, USE_JIT, NATIVE_CALLS, CALL_STUBS, RESUMABLE, false>(program, arguments, limits, profile, &[])
}

fn execute_core<const PROFILE: bool, const USE_JIT: bool, const NATIVE_CALLS: bool, const CALL_STUBS: bool, const RESUMABLE: bool, const SCALAR: bool>(''')
    replace(lib,'''    mut profile: Option<&mut ExecutionProfile>,
) -> Result<Execution, String> {
    validate(program)?;''','''    mut profile: Option<&mut ExecutionProfile>,
    scalar_abi: &[scalar_abi::FunctionAbi],
) -> Result<Execution, String> {
    // Scalar callers are private Artifact methods that already validated the
    // entire program and ABI. Legacy callers keep their original validation.
    if !SCALAR { validate(program)?; }
    debug_assert!(!SCALAR || (program.version == scalar_abi::SCALAR_VERSION && scalar_abi.len() == program.functions.len()));''')
    replace(lib,'''    if program.version & !PARTIAL_VALIDATION != VERSION {
        return Err("bytecode version mismatch".into());
    }''','''    let expected_version = if SCALAR { scalar_abi::SCALAR_VERSION } else { VERSION };
    if program.version & !PARTIAL_VALIDATION != expected_version {
        return Err("bytecode version mismatch".into());
    }''')
    replace(lib,'    for (slot, value) in entry.args.iter().zip(arguments) {',
        '    for (index, (slot, value)) in entry.args.iter().zip(arguments).enumerate() {')
    replace(lib,'        memory.store(base + slot.offset, slot.size, *value)?;',
        '''        if !SCALAR || scalar_abi[program.entry].arguments[index].is_none() {
            memory.store(base + slot.offset, slot.size, *value)?;
        }''')
    replace(lib,'    let needs_register_zeroes: Vec<_> = if RESUMABLE {',
        '''    let needs_register_zeroes: Vec<_> = if SCALAR {
        program.functions.iter().zip(scalar_abi).map(|(f, abi)| {
            let mut initialized: Vec<_> = abi.arguments.iter().filter_map(|r| *r).collect();
            initialized.extend(abi.result);
            registers::needs_initial_zeroes_with_inputs(f, &initialized)
        }).collect()
    } else if RESUMABLE {''')
    replace(lib,'    let mut registers = vec![0; entry.registers];',
        '''    let mut registers = vec![0; entry.registers];
    if SCALAR {
        for (register, value) in scalar_abi[program.entry].arguments.iter().zip(arguments) {
            if let Some(register) = register { registers[*register as usize] = *value; }
        }
    }''')
    replace(lib,'                if local_call_arguments[frame.function][frame.pc - 1] {',
        '''                if SCALAR {
                    let caller_register_base = frame.register_base;
                    let callee_register_base = register_bytes / 16 - callee.registers;
                    let register_end = register_bytes / 16;
                    if register_end > registers.len() { registers.resize(register_end, 0); }
                    if needs_register_zeroes[callee_id] { registers[callee_register_base..register_end].fill(0); }
                    if let Some(result) = scalar_abi[callee_id].result {
                        registers[callee_register_base + result as usize] = 0;
                    }
                    // The old caller slice is no longer used in this branch;
                    // resizing backing above cannot invalidate a retained borrow.
                    for ((src, slot), register) in args.iter().zip(&callee.args).zip(&scalar_abi[callee_id].arguments) {
                        let address = registers[caller_register_base + *src as usize] as usize;
                        if let Some(register) = register {
                            let value = memory.load(address, slot.size)?;
                            registers[callee_register_base + *register as usize] = value;
                        } else { memory.copy(address, base + slot.offset, slot.size)?; }
                    }
                } else if local_call_arguments[frame.function][frame.pc - 1] {''')
    replace(lib,'''                if needs_register_zeroes[callee_id] {
                    registers[register_base..register_end].fill(0);
                }''',
        '''                if !SCALAR && needs_register_zeroes[callee_id] {
                    registers[register_base..register_end].fill(0);
                }''')
    replace(lib,'''                let callback = frame.tls_callback;
                if frames.len() == 1 && !callback {
                    let value = memory.load(source, result.size)?;''',
        '''                let callback = frame.tls_callback;
                let scalar_value = if SCALAR {
                    scalar_abi[frame.function].result.map(|reg| scalar_abi::truncate(r[reg as usize], result.size))
                } else { None };
                if frames.len() == 1 && !callback {
                    let value = if let Some(value) = scalar_value { value } else { memory.load(source, result.size)? };''')
    replace(lib,'                if !callback { memory.copy(source, frame.return_address, result.size)?; }',
        '''                if !callback {
                    if let Some(value) = scalar_value { memory.store(frame.return_address, result.size, value)?; }
                    else { memory.copy(source, frame.return_address, result.size)?; }
                }''')
    content=lib.read_text();old='&mut register_bytes, &needs_register_zeroes, &limits)?'
    if content.count(old)!=3:raise RuntimeError('TLS call anchors differ')
    lib.write_text(content.replace(old,'&mut register_bytes, &needs_register_zeroes, &limits, if SCALAR { Some(scalar_abi) } else { None })?'))
    tls=directory/'tls.rs'
    replace(tls,'        needs_zeroes: &[bool], limits: &Limits) -> Result<Option<u128>, String> {',
        '        needs_zeroes: &[bool], limits: &Limits, scalar_abi: Option<&[crate::scalar_abi::FunctionAbi]>) -> Result<Option<u128>, String> {')
    replace(tls,'            memory.store(base + function.args[0].offset, 8, callback.argument as u128)?;',
        '''            if let Some(register) = scalar_abi.and_then(|abi| abi[callback.function].arguments[0]) {
                registers[register_base + register as usize] = callback.argument as u128;
            } else { memory.store(base + function.args[0].offset, 8, callback.argument as u128)?; }''')
