"""Install caller value operands into an exact qualified native source copy."""
from pathlib import Path
import re
HERE=Path(__file__).resolve().parent

def replace(s,old,new):
    if s.count(old)!=1:raise RuntimeError('caller-value anchor differs: '+old[:110])
    return s.replace(old,new)

def inject(source):
    root=source/'crates/bytecode/src'
    # Every descriptor initializer, including test scaffolding and TLS, must
    # write the new tag. Its default is the established memory destination.
    for p in root.rglob('*.rs'):
        s=p.read_text()
        s=re.sub(r'tls_callback: (false|true|callback)([, }])',r'return_value: false, tls_callback: \1\2',s)
        p.write_text(s)
    p=root/'frames.rs';s=p.read_text()
    s=replace(s,'    pub return_address: usize,','    /// Address, or caller register index when return_value is true.\n    pub return_address: usize,')
    s=replace(s,'    pub tls_callback: bool,','    pub tls_callback: bool,\n    pub return_value: bool,')
    s=replace(s,'    pub const SIZE: usize =', '    pub const RETURN_VALUE: usize = std::mem::offset_of!(Frame, return_value);\n    pub const SIZE: usize =')
    s=replace(s,'assert!(SIZE == 48 && ALIGN == 8);','assert!(RETURN_VALUE == 41 && SIZE == 48 && ALIGN == 8);');p.write_text(s)
    p=root/'lib.rs';s=p.read_text()
    s=replace(s,'pub mod scalar_abi;','pub mod scalar_abi;\nmod scalar_calls;\npub use scalar_calls::{CallArgument, CallDestination};')
    s=replace(s,'    RegisterTlsDestructor { callback: Reg, argument: Reg },\n}', '''    RegisterTlsDestructor { callback: Reg, argument: Reg },
    /// Version 6 only. Explicit values coexist with address/aggregate operands.
    CallValue { function: usize, args: Vec<CallArgument>, destination: CallDestination },
}''')
    s=replace(s,'''            Op::Call {
                args, destination, ..
            }
            | Op::CallIndirect {
                args, destination, ..
            } => {
                let callee_id = match instruction {''', '''            Op::Call { .. } | Op::CallIndirect { .. } | Op::CallValue { .. } => {
                let (args, destination) = match instruction {
                    Op::Call { args, destination, .. } | Op::CallIndirect { args, destination, .. } =>
                        (scalar_calls::Arguments::Addresses(args), CallDestination::Address(*destination)),
                    Op::CallValue { args, destination, .. } => (scalar_calls::Arguments::Mixed(args), *destination),
                    _ => unreachable!(),
                };
                let callee_id = match instruction {''')
    s=replace(s,'                    Op::Call { function, .. } => *function,','                    Op::Call { function, .. } | Op::CallValue { function, .. } => *function,')
    s=replace(s,'                let return_address = r[*destination as usize] as usize;', '''                let return_address = match destination {
                    CallDestination::Address(reg) => r[reg as usize] as usize,
                    CallDestination::Value(reg) => reg as usize,
                };''')
    s=replace(s,'''                    for ((src, slot), register) in args.iter().zip(&callee.args).zip(&scalar_abi[callee_id].arguments) {
                        let address = registers[caller_register_base + *src as usize] as usize;
                        if let Some(register) = register {
                            let value = memory.load(address, slot.size)?;
                            registers[callee_register_base + *register as usize] = value;
                        } else { memory.copy(address, base + slot.offset, slot.size)?; }
                    }''', '''                    for (index, (slot, register)) in callee.args.iter().zip(&scalar_abi[callee_id].arguments).enumerate() {
                        let operand = args.at(index);
                        let input = registers[caller_register_base + operand.register() as usize];
                        match (operand, register) {
                            (CallArgument::Address(_), Some(reg)) =>
                                registers[callee_register_base + *reg as usize] = memory.load(input as usize, slot.size)?,
                            (CallArgument::Value(_), Some(reg)) =>
                                registers[callee_register_base + *reg as usize] = scalar_abi::truncate(input, slot.size),
                            (CallArgument::Address(_), None) => memory.copy(input as usize, base + slot.offset, slot.size)?,
                            (CallArgument::Value(_), None) => memory.store(base + slot.offset, slot.size, scalar_abi::truncate(input, slot.size))?,
                        }
                    }''')
    # These are the two established version-5 memory-copy loops only.
    old='for (src, slot) in args.iter().zip(&callee.args) {'
    if s.count(old)!=2:raise RuntimeError('legacy call loops changed')
    s=s.replace(old,'for (src, slot) in args.addresses().iter().zip(&callee.args) {')
    s=replace(s,'''                    return_address,
                    return_value: false, tls_callback: false,''', '''                    return_address,
                    return_value: matches!(destination, CallDestination::Value(_)), tls_callback: false,''')
    s=replace(s,'''                    if let Some(value) = scalar_value { memory.store(frame.return_address, result.size, value)?; }
                    else { memory.copy(source, frame.return_address, result.size)?; }''', '''                    if frame.return_value {
                        let value = match scalar_value { Some(value) => value, None => memory.load(source, result.size)? };
                        let caller = frames.last().ok_or("missing value-return caller")?;
                        registers[caller.register_base + frame.return_address] = value;
                    } else if let Some(value) = scalar_value { memory.store(frame.return_address, result.size, value)?; }
                    else { memory.copy(source, frame.return_address, result.size)?; }''')
    s=replace(s,'                Op::Return | Op::Trap { .. } => {}','''                Op::CallValue { function, args, destination } =>
                    scalar_calls::validate_call(program, f, *function, args, *destination)?,
                Op::Return | Op::Trap { .. } => {}''');p.write_text(s)
    (root/'scalar_calls.rs').write_text((HERE/'operands.rs').read_text())
    p=root/'registers.rs';s=p.read_text()
    s=replace(s,'        Op::Call{args,destination,..}=>{read(*destination);for &r in args {read(r);}},', '''        Op::Call{args,destination,..}=>{read(*destination);for &r in args {read(r);}},
        Op::CallValue{args,destination,..}=>{
            if let crate::CallDestination::Address(r)=destination {read(*r);}
            for arg in args {read(arg.register());}
        },''')
    s=replace(s,'    match op {\n        Op::Binary{dst,overflow,..}=>{write(*dst);write(*overflow);},', '''    match op {
        Op::CallValue{destination,..}=>{if let crate::CallDestination::Value(r)=destination {write(*r);}},
        Op::Binary{dst,overflow,..}=>{write(*dst);write(*overflow);},''');p.write_text(s)
    p=root/'native_continuation.rs';s=p.read_text()
    s=replace(s,'        Ok(frame)\n    }', '''        if frame.return_value {
            let caller = state.frame_len.checked_sub(2).and_then(|i| frames.prepared_frame(i))
                .ok_or("native value return has no caller")?;
            let caller_function = program.functions.get(caller.function).ok_or("native value return has invalid caller")?;
            if program.version != crate::scalar_abi::SCALAR_VERSION || frame.tls_callback
                || !crate::scalar_calls::scalar_width(function.result.size)
                || frame.return_address >= caller_function.registers
                || caller.register_base.checked_add(caller_function.registers) != Some(frame.register_base) {
                return Err("native continuation returned an invalid value destination".into());
            }
        }
        Ok(frame)
    }''');p.write_text(s)
    p=root/'jit.rs';s=p.read_text()
    s=replace(s,'if resumable && matches!(f.code[pc], Op::Call { .. } | Op::Return)',
        'if resumable && matches!(f.code[pc], Op::Call { .. } | Op::CallValue { .. } | Op::Return)');p.write_text(s)
    p=root/'jit/resumable.rs';s=p.read_text()
    s=replace(s,'use super::*;','use super::*;\nuse crate::{CallArgument, CallDestination, scalar_calls::Arguments};')
    s=replace(s,'''                    args,
                    *destination,
                    self.resumable.as_ref().unwrap().zeroes[*function],''', '''                    Arguments::Addresses(args),
                    CallDestination::Address(*destination),
                    self.resumable.as_ref().unwrap().zeroes[*function],''')
    s=replace(s,'            Op::Return => a.resumable_return(f, pc, result, self.profiled, &mut declines)?,', '''            Op::CallValue { function, args, destination } => {
                a.resumable_call(f, pc, *function, &self.program.functions[*function],
                    self.scalar_abi.map(|table| &table[*function]), Arguments::Mixed(args), *destination,
                    self.resumable.as_ref().unwrap().zeroes[*function], self.profiled, &mut declines)?;
            }
            Op::Return => a.resumable_return(f, pc, result, self.scalar_abi.is_some(), self.profiled, &mut declines)?,''')
    s=replace(s,'        args: &[Reg],\n        destination: Reg,','        args: Arguments<\'_>,\n        destination: CallDestination,')
    s=replace(s,'''        for (index, (source, slot)) in args.iter().zip(&callee.args).enumerate() {
            // Preserve the interpreter's ordered argument reads and faults.
            self.address(11, *source, slot.size, false);
            if let Some(reg) = abi.and_then(|a| a.arguments[index]) {
                self.load_mem(9, 10, 11, slot.size);''', '''        for (index, slot) in callee.args.iter().enumerate() {
            let input = args.at(index);
            // Preserve ordered address checks. Value operands never read memory.
            match input {
                CallArgument::Address(source) => self.address(11, source, slot.size, false),
                CallArgument::Value(source) => {
                    self.get(9, source, false); self.get(10, source, true);
                    self.scalar_call_clip(9, 10, slot.size);
                }
            }
            if let Some(reg) = abi.and_then(|a| a.arguments[index]) {
                if matches!(input, CallArgument::Address(_)) { self.load_mem(9, 10, 11, slot.size); }''')
    # Only the argument copy site, not the result copy site, is replaced here.
    s=replace(s,'''                self.abi_copy(slot.size)?;
            }
        }
        if abi.is_none()''', '''                if matches!(input, CallArgument::Value(_)) { self.store_mem(9, 10, 12, slot.size); }
                else { self.abi_copy(slot.size)?; }
            }
        }
        if abi.is_none()''')
    s=replace(s,'        self.get(15, destination, false);', '''        match destination {
            CallDestination::Address(reg) => self.get(15, reg, false),
            CallDestination::Value(reg) => self.imm(15, u64::from(reg)),
        }''')
    s=replace(s,'        self.emit(0x39000000 | ((frame::TLS_CALLBACK as u32) << 10) | (20 << 5) | 31);', '''        self.emit(0x39000000 | ((frame::TLS_CALLBACK as u32) << 10) | (20 << 5) | 31);
        let tag = if matches!(destination, CallDestination::Value(_)) { self.imm(13, 1); 13 } else { 31 };
        self.emit(0x39000000 | ((frame::RETURN_VALUE as u32) << 10) | (20 << 5) | tag);''')
    s=replace(s,'        result: Option<Reg>,\n        profiled: bool,', '        result: Option<Reg>,\n        value_calls: bool,\n        profiled: bool,')
    start=s.index('        if let Some(reg) = result {',s.index('    fn resumable_return('))
    end=s.index('        self.mov(3, 21);',start)
    old=s[start:end]
    s=s[:start]+'''        // Values return directly to caller register backing. Ordinary
        // destinations retain the checked memory store/copy path below.
        let value_branch = if value_calls && crate::scalar_calls::scalar_width(f.result.size) {
            self.emit(0x39400000 | ((frame::RETURN_VALUE as u32) << 10) | (20 << 5) | 9);
            self.cmp(9, 31);
            let at = self.words.len(); self.emit(0x54000000 | Cond::Ne as u32); Some(at)
        } else { None };
''' +old+'''        let value_skip = if let Some(at) = value_branch {
            let skip = self.words.len(); self.emit(0x14000000);
            self.patch_conditional(at, self.words.len())?;
            if let Some(reg) = result {
                self.get(9, reg, false); self.get(10, reg, true);
                self.scalar_call_clip(9, 10, f.result.size);
            } else {
                self.imm(11, f.result.offset as u64);
                self.three(0x8b000000, 11, 1, 11);
                self.three(0x8b000000, 11, 2, 11);
                self.load_mem(9, 10, 11, f.result.size);
            }
            self.sub_imm(11, 20, frame::SIZE);
            self.load64(11, 11, frame::REGISTER_BASE);
            self.load64(12, 20, frame::RETURN_ADDRESS);
            self.three(0x8b000000, 11, 11, 12);
            self.lsl_imm(11, 11, 4);
            self.load64(12, 19, REGISTERS);
            self.three(0x8b000000, 12, 12, 11);
            self.store_mem(9, 10, 12, 16);
            Some(skip)
        } else { None };
        let value_join = self.words.len();
''' +s[end:]
    s=replace(s,'        self.mov(3, 21);\n        self.store64(22, 19, state::REGISTER_LEN);', '''        self.mov(3, 21);
        if let Some(skip) = value_skip { patch_jump(&mut self.words, skip, value_join)?; }
        self.store64(22, 19, state::REGISTER_LEN);''')
    s=replace(s,'    fn resumable_return(', '''    fn scalar_call_clip(&mut self, lo: u32, hi: u32, size: usize) {
        debug_assert!(crate::scalar_calls::scalar_width(size));
        if size < 8 {
            self.imm(13, (1u64 << (size * 8)) - 1);
            self.three(0x8a000000, lo, lo, 13);
        }
        if size < 16 { self.mov(hi, 31); }
    }

    fn resumable_return(''');p.write_text(s)
    # The new tests share the existing same-artifact native comparison harness.
    p=root/'scalar_abi_runtime_tests.rs';s=p.read_text()
    s+='\n#[cfg(all(target_arch="aarch64",target_os="macos"))]\n#[path="scalar_value_call_tests.rs"]\nmod value_calls;\n'
    p.write_text(s);(root/'scalar_value_call_tests.rs').write_text((HERE/'tests.rs').read_text())
    p=root/'scalar_abi_native_tests.rs';s=p.read_text()
    s=replace(s,'fn outcome(e:Result<Execution,String>)','pub(super) fn outcome(e:Result<Execution,String>)');p.write_text(s)
    with (root/'native_continuation/tests.rs').open('a') as out:out.write((HERE/'boundary_tests.rs').read_text())

    p=source/'crates/mir-export/src/lower/scalar_promote_transform.rs';s=p.read_text()
    first=s.index('fn registers(');last=s.index('\nfn starts(',first)
    s=s[:first]+'fn registers(op:&Op,read:impl FnMut(Reg),write:impl FnMut(Reg)) {\n    rust_interp_bytecode::diagnostic_visit_registers(op,read,write);\n}\n'+s[last:];p.write_text(s)
    p=source/'crates/mir-export/src/lower/scalar_promote_moves.rs';s=p.read_text()
    s=replace(s,'        Op::Call{args,destination,..}=>{map(destination);for r in args {map(r);}},', '        Op::Call{args,destination,..}=>{map(destination);for r in args {map(r);}},\n        Op::CallValue{args,destination,..}=>{\n            if let rust_interp_bytecode::CallDestination::Address(r)=destination {map(r);}\n            for arg in args {match arg {rust_interp_bytecode::CallArgument::Address(r)|rust_interp_bytecode::CallArgument::Value(r)=>map(r)}}\n        },');p.write_text(s)

    p=root/'jit/local_memory.rs';s=p.read_text()
    s=replace(s,'            Op::Call {..} | Op::CallIndirect {..} | Op::CopyDynamic {..}',
        '            Op::Call {..} | Op::CallIndirect {..} | Op::CallValue {..} | Op::CopyDynamic {..}');p.write_text(s)
    for name in ['calls.rs','inline.rs']:
        p=root/name;s=p.read_text()
        anchor='Op::Local { dst, offset } => locals[*dst as usize] = (epoch, *offset),'
        s=replace(s,anchor,'Op::CallValue { destination, .. } => {\n                    if let crate::CallDestination::Value(dst) = destination { locals[*dst as usize].0 = 0; }\n                },\n                Op::Local { dst, offset } => locals[*dst as usize] = (epoch, *offset),');p.write_text(s)
