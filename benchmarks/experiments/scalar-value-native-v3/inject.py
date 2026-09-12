"""Add scalar ABI support to our native emitter in a qualified source copy."""
from pathlib import Path

HERE = Path(__file__).resolve().parent


def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('native injection anchor differs: ' + old[:100])
    return text.replace(old, new)


def inject(source):
    root = source/'crates/bytecode/src'
    p = root/'scalar_abi_runtime.rs'; s = p.read_text()
    s = replace(s, '        if engine == Engine::Jit { return Err("scalar ABI JIT execution is not implemented".into()); }', '''        if engine == Engine::Jit {
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
        }'''); p.write_text(s)
    p = root/'lib.rs'; s = p.read_text()
    s = replace(s, '    if let Some(jit) = &mut jit { jit.compile_nanos = started.elapsed().as_nanos(); }', '''    if let Some(jit) = &mut jit {
        if SCALAR { jit.set_scalar_abi(scalar_abi); }
        jit.compile_nanos = started.elapsed().as_nanos();
    }'''); p.write_text(s)
    p = root/'jit.rs'; s = p.read_text()
    s = replace(s, "    program: &'a Program,", "    program: &'a Program,\n    scalar_abi: Option<&'a [crate::scalar_abi::FunctionAbi]>,")
    s = replace(s, 'Ok(Self { _thread_bound: std::marker::PhantomData, program, profiled,',
        'Ok(Self { _thread_bound: std::marker::PhantomData, program, scalar_abi: None, profiled,')
    s = replace(s, '        let staged = self.emit_function(&self.program.functions[id], remaining);', '''        let staged = self.emit_function_with_abi(&self.program.functions[id], remaining,
            self.scalar_abi.map(|table| &table[id]));''')
    s = replace(s, "    fn emit_function(&self, f: &'a Function, word_budget: usize) -> Result<Option<CompiledFunction<'a>>, EmitError> {", '''    #[cfg(test)]
    fn emit_function(&self, f: &'a Function, word_budget: usize) -> Result<Option<CompiledFunction<'a>>, EmitError> {
        self.emit_function_with_abi(f, word_budget, None)
    }

    fn emit_function_with_abi(&self, f: &'a Function, word_budget: usize,
        abi: Option<&crate::scalar_abi::FunctionAbi>) -> Result<Option<CompiledFunction<'a>>, EmitError> {''')
    s = replace(s, '''        let reads = read_registers(f);
        let values = self.persistent_registers.then(|| values::analyze(f)).flatten();''', '''        let result = abi.and_then(|a| a.result);
        let reads = read_registers_with_result(f, result);
        let values = self.persistent_registers.then(|| values::analyze_with_result(f, result)).flatten();''')
    s = replace(s, 'self.emit_resumable_transition(f, pc, &reads, values.as_ref())?',
        'self.emit_resumable_transition(f, pc, &reads, values.as_ref(), result)?')
    s = replace(s, 'fn read_registers(f: &Function) -> Vec<Option<(usize, usize)>> {', '''fn read_registers(f: &Function) -> Vec<Option<(usize, usize)>> {
    read_registers_with_result(f, None)
}
fn read_registers_with_result(f: &Function, result: Option<Reg>) -> Vec<Option<(usize, usize)>> {''')
    s = replace(s, '        crate::registers::visit_registers(op, &mut mark, |_| {});', '''        crate::registers::visit_registers(op, &mut mark, |_| {});
        // Return's value comes from metadata, so it is an implicit operand.
        if matches!(op, Op::Return) { if let Some(r) = result { mark(r); } }''')
    p.write_text(s)
    p = root/'jit/values.rs'; s = p.read_text()
    s = replace(s, '''    analyze_with_work(f, MAX_WORK)
}
fn analyze_with_work(f: &Function, max_work: usize) -> Option<Allocation> {''', '''    analyze_with_result(f, None)
}
pub(super) fn analyze_with_result(f: &Function, result: Option<Reg>) -> Option<Allocation> {
    analyze_with_result_and_work(f, result, MAX_WORK)
}
#[cfg(test)]
fn analyze_with_work(f: &Function, max_work: usize) -> Option<Allocation> {
    analyze_with_result_and_work(f, None, max_work)
}
fn analyze_with_result_and_work(f: &Function, result: Option<Reg>, max_work: usize) -> Option<Allocation> {''')
    s = replace(s, '''        if !valid || defs[pc].iter().any(|&r| r as usize >= f.registers) { return None; }''', '''        if matches!(op, Op::Return) {
            if let Some(r) = result {
                if r as usize >= f.registers || operands >= MAX_OPERANDS { return None; }
                uses[pc].push(r); operands += 1;
                frequency[r as usize] += 1;
            }
        }
        if !valid || defs[pc].iter().any(|&r| r as usize >= f.registers) { return None; }''')
    p.write_text(s)
    p = root/'jit/resumable.rs'; s = p.read_text()
    s = replace(s, "impl<'a> Jit<'a> {", '''impl<'a> Jit<'a> {
    // Called only after Artifact validation, before any function is prepared.
    pub(crate) fn set_scalar_abi(&mut self, abi: &'a [crate::scalar_abi::FunctionAbi]) {
        assert!(self.prepared.iter().all(|p| !p));
        assert_eq!(abi.len(), self.program.functions.len());
        self.scalar_abi = Some(abi);
        if let Some(entries) = &mut self.resumable {
            entries.zeroes = self.program.functions.iter().zip(abi).map(|(f, a)| {
                let mut inputs: Vec<_> = a.arguments.iter().filter_map(|r| *r).collect();
                inputs.extend(a.result);
                crate::registers::needs_initial_zeroes_with_inputs(f, &inputs)
            }).collect();
        }
    }
''')
    s = replace(s, "        values: Option<&'b values::Allocation>,\n    )", "        values: Option<&'b values::Allocation>,\n        result: Option<Reg>,\n    )")
    s = replace(s, '''                    callee,
                    args,''', '''                    callee,
                    self.scalar_abi.map(|table| &table[*function]),
                    args,''')
    s = replace(s, 'a.resumable_return(f, pc, self.profiled, &mut declines)?',
        'a.resumable_return(f, pc, result, self.profiled, &mut declines)?')
    s = replace(s, '''        callee: &Function,
        args: &[Reg],''', '''        callee: &Function,
        abi: Option<&crate::scalar_abi::FunctionAbi>,
        args: &[Reg],''')
    begin = s.index('        for (source, slot) in args.iter().zip(&callee.args) {', s.index('    fn resumable_call('))
    end = s.index('        self.get(15, destination, false);', begin)
    s = s[:begin] + '''        // x21 holds the callee frame base, x22 its initialized register base.
        // Set the result before input assignments: result/input aliasing is valid.
        if abi.is_some() {
            self.imm(9, caller.registers as u64 * 16);
            self.three(0x8b000000, 22, 0, 9);
            if zeroes {
                self.mov(11, 22);
                self.imm(12, callee.registers as u64 * 16);
                self.three(0x8b000000, 12, 22, 12);
                self.zero_range_at_least(callee.registers * 16)?;
            }
        }
        if let Some(result) = abi.and_then(|a| a.result) {
            self.imm(12, u64::from(result) * 16);
            self.three(0x8b000000, 12, 22, 12);
            self.store_mem(31, 31, 12, 16);
        }
        for (index, (source, slot)) in args.iter().zip(&callee.args).enumerate() {
            // Preserve the interpreter's ordered argument reads and faults.
            self.address(11, *source, slot.size, false);
            if let Some(reg) = abi.and_then(|a| a.arguments[index]) {
                self.load_mem(9, 10, 11, slot.size);
                self.imm(12, u64::from(reg) * 16);
                self.three(0x8b000000, 12, 22, 12);
                self.store_mem(9, 10, 12, 16);
            } else {
                self.imm(12, slot.offset as u64);
                self.three(0x8b000000, 12, 21, 12);
                self.three(0x8b000000, 12, 2, 12);
                self.abi_copy(slot.size)?;
            }
        }
        if abi.is_none() {
            // Preserve the version-5 emission order exactly.
            self.imm(9, caller.registers as u64 * 16);
            self.three(0x8b000000, 22, 0, 9);
            if zeroes {
                self.mov(11, 22);
                self.imm(12, callee.registers as u64 * 16);
                self.three(0x8b000000, 12, 22, 12);
                self.zero_range_at_least(callee.registers as usize * 16)?;
            }
        }
''' + s[end:]
    s = replace(s, '''    fn resumable_return(
        &mut self,
        f: &Function,
        pc: usize,
        profiled: bool,''', '''    fn resumable_return(
        &mut self,
        f: &Function,
        pc: usize,
        result: Option<Reg>,
        profiled: bool,''')
    s = replace(s, '''        self.imm(11, f.result.offset as u64);
        self.three(0x8b000000, 11, 1, 11);
        self.three(0x8b000000, 11, 2, 11);
        self.load64(12, 20, frame::RETURN_ADDRESS);
        self.checked_address(12, f.result.size, true);
        self.abi_copy(f.result.size)?;''', '''        if let Some(reg) = result {
            self.load64(12, 20, frame::RETURN_ADDRESS);
            self.checked_address(12, f.result.size, true);
            self.get(9, reg, false);
            self.get(10, reg, true);
            self.store_mem(9, 10, 12, f.result.size);
        } else {
            self.imm(11, f.result.offset as u64);
            self.three(0x8b000000, 11, 1, 11);
            self.three(0x8b000000, 11, 2, 11);
            self.load64(12, 20, frame::RETURN_ADDRESS);
            self.checked_address(12, f.result.size, true);
            self.abi_copy(f.result.size)?;
        }''')
    p.write_text(s)
    # Extend, rather than weaken, existing interpreter comparisons. The formerly
    # unsupported engine is now qualified; the incompatible tree mode stays explicit.
    p = root/'scalar_abi_runtime_tests.rs'; s = p.read_text()
    s = replace(s, '''    assert_eq!(a.execute_with_engine(&[],Limits::default(),Engine::Jit).unwrap_err(),"scalar ABI JIT execution is not implemented");''', '''    assert_eq!(a.execute_with_engine(&[],Limits{jit_native_calls:true,..Limits::default()},Engine::Jit).unwrap_err(),
        "scalar ABI does not support native tree/stub calls");''')
    s = replace(s, '''fn check(a:&Artifact,args:&[u128],want:u128) {
''', '''fn check(a:&Artifact,args:&[u128],want:u128) {
    #[cfg(all(target_arch="aarch64",target_os="macos"))]
    native::compare(a, args, want);
''')
    s += '\n#[cfg(all(target_arch="aarch64",target_os="macos"))]\n#[path="scalar_abi_native_tests.rs"]\nmod native;\n'
    p.write_text(s)
    (root/'scalar_abi_native_tests.rs').write_text((HERE/'tests.rs').read_text())
