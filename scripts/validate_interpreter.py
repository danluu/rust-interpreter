#!/usr/bin/env python3
"""Differential and rejection tests for the custom MIR/bytecode path."""
import atexit
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / '.work/interpreter-build/release'
TOOLCHAIN = 'nightly-2026-09-08'


def main():
    started = time.perf_counter()
    work = ROOT / '.work' / ('interpreter-validation-' + str(time.time_ns()))
    work.mkdir()
    records = []
    # Preserve every completed command without rewriting the growing archive
    # thousands of times. The final JSON keeps existing result readers working;
    # JSON Lines also survives interruption before the final snapshot is written.
    def checkpoint():
        (work / 'records.json').write_text(json.dumps(records, indent=2))
    atexit.register(checkpoint)

    def run(command, env=None, success=True):
        start = time.perf_counter()
        p = subprocess.run(list(map(str, command)), cwd=ROOT, env=env, text=True, capture_output=True)
        record = dict(command=list(map(str, command)), returncode=p.returncode,
                      seconds=time.perf_counter()-start, stdout=p.stdout, stderr=p.stderr)
        records.append(record)
        with (work / 'commands.jsonl').open('a') as log:
            log.write(json.dumps(record) + '\n')
        if (p.returncode == 0) != success:
            raise RuntimeError(str(command) + '\n' + p.stderr)
        if 'internal compiler error' in p.stderr:
            raise RuntimeError('compiler crashed: ' + p.stderr)
        return p.stdout.strip()

    def export(source, success=True, policy='strict', sysroot=None, extra=(), entry='rust_interp_entry', test_body=False, crate_name='interpreter_case', entries=None):
        env = os.environ.copy()
        env.pop('RUST_INTERP_ENTRIES',None)
        env.pop('RUST_INTERP_AUDIT_SELECTION',None)
        env.update(RUST_INTERP_OUTPUT=str(work / 'program.rbc'), RUST_INTERP_ENTRY=entry,
                   RUST_INTERP_EXPORT_TEST='1' if test_body else '0',
                   RUST_INTERP_DEMAND_BODIES='0' if policy=='strict' else '1',RUST_INTERP_DEMAND_CACHE='1' if policy=='demand-cache' else '0')
        if entries is not None: env['RUST_INTERP_ENTRIES']=json.dumps(entries)
        command=[BUILD / 'rust-interp-mir-export', source, '--crate-name',crate_name,'--edition=2024', '--emit=metadata', '-C','incremental='+str(work/policy/'incremental'),'-o', work / 'program.rmeta']
        if sysroot:command+=['--sysroot',sysroot]
        command+=list(extra)
        run(command, env, success)
        assert (work / 'program.rbc').exists() == success

    def evaluate(seed,success=True):
        values=[run([BUILD/'rust-interp-vm','--engine',engine,work/'program.rbc',seed],success=success) for engine in ['interpreter','jit']]
        assert values[0]==values[1]
        return values[0]

    source = ROOT / 'tests/interpreter_fixture.rs'
    export(source)
    run(['rustc', '+' + TOOLCHAIN, source, '--edition=2024', '-o', work / 'native'])
    seeds = [0,1,2,3,127,128,255,256,2**63-1,2**63,2**64-1]
    seeds += [random.Random(i).getrandbits(64) for i in range(100)]
    expected = run([work / 'native', *seeds]).splitlines()
    for seed, want in zip(seeds, expected):
        assert evaluate(seed) == want

    popcount_source = ROOT / 'tests/popcount_fixture.rs'
    export(popcount_source)
    run(['rustc', '+' + TOOLCHAIN, popcount_source, '--edition=2024', '-o', work / 'popcount-native'])
    popcount_expected = run([work / 'popcount-native', *seeds]).splitlines()
    for seed, want in zip(seeds, popcount_expected):
        assert evaluate(seed) == want

    local_layout_source = ROOT / 'tests/local_layout_fixture.rs'
    export(local_layout_source)
    run(['rustc', '+' + TOOLCHAIN, local_layout_source, '--edition=2024', '-o', work / 'local-layout-native'])
    local_layout_expected = run([work / 'local-layout-native', *seeds]).splitlines()
    assert len(local_layout_expected) == len(seeds)
    for seed, want in zip(seeds, local_layout_expected):
        assert evaluate(seed) == want

    constructor_dependency=ROOT/'tests/constructor_dependency.rs'
    constructor_source=ROOT/'tests/constructor_fixture.rs'
    dependency=work/'libconstructor_dependency.rlib'
    run(['rustc','+'+TOOLCHAIN,constructor_dependency,'--crate-type=rlib',
         '--crate-name=constructor_dependency','--edition=2024','-o',dependency])
    dependency_args=['--extern','constructor_dependency='+str(dependency)]
    export(constructor_source,extra=dependency_args)
    run(['rustc','+'+TOOLCHAIN,constructor_source,'--edition=2024',*dependency_args,'-o',work/'constructor-native'])
    constructor_expected=run([work/'constructor-native',*seeds]).splitlines()
    for seed,want in zip(seeds,constructor_expected):assert evaluate(seed)==want

    result_source=ROOT/'tests/result_test_fixture.rs'
    result_native=work/'result-native'
    run(['rustc','+'+TOOLCHAIN,result_source,'--edition=2024','--test','-o',result_native])
    result_cases={name:True for name in ['unit_ok','tagged_ok','niche_ok','bool_ok','empty_error','large_ok','string_ok','alias_ok']}
    result_cases.update({name:False for name in ['tagged_err','niche_err','bool_err','large_err','string_err','alias_err']})
    for name,success in result_cases.items():
        native=run([result_native,'--exact',name,'--test-threads=1'],success=success)
        assert ('1 passed' if success else '1 failed') in native
        export(result_source,entry=name,test_body=True,extra=['--test'])
        for engine in ['interpreter','jit']:
            value=run([BUILD/'rust-interp-vm','--engine',engine,work/'program.rbc'],success=success)
            if success:assert value=='0'
            else:assert f'test {name} returned Err' in records[-1]['stderr']
    for name in ['scalar_success','argument_result','fake_result']:
        export(result_source,entry=name,test_body=True,extra=['--test'],success=False)
    # The Result adapter is opt-in with test mode, even in a test compilation.
    export(result_source,entry='tagged_ok',extra=['--test'],success=False)

    cases = {
        'uncalled-type-error': 'fn unused() { let _: u8 = "bad"; }',
        'uncalled-borrow-error': 'fn unused() { let mut a = 1; let b = &a; a = 2; let _ = *b; }',
        'bad-constant': 'const BAD: u8 = 1 / 0; const _: u8 = BAD;',
    }
    for name, invalid in cases.items():
        bad = work / (name + '.rs')
        bad.write_text('pub fn rust_interp_entry(a: u64) -> u64 { a }\n' + invalid + '\nfn main() {}\n')
        export(bad, success=False)

    for name, body in {
        'external-call': 'unsafe extern "C" { fn getpid() -> i32; } unsafe { getpid() as u64 }',
    }.items():
        unsupported = work / (name + '.rs')
        unsupported.write_text('pub fn rust_interp_entry(a: u64) -> u64 { ' + body + ' }\nfn main() {}\n')
        export(unsupported, success=False)
    unsupported=work/'float16.rs'
    unsupported.write_text('#![feature(f16)] pub fn rust_interp_entry(a:u64)->u64 { (a as f16 * 1.5) as u64 } fn main() {}\n')
    export(unsupported,success=False)
    assert 'unsupported floating-point type f16' in records[-1]['stderr']

    heap_source=ROOT/'tests/heap_fixture.rs'
    export(heap_source)
    run(['rustc','+'+TOOLCHAIN,heap_source,'--edition=2024','-o',work/'heap-native'])
    heap_expected=run([work/'heap-native',*seeds]).splitlines()
    for seed,want in zip(seeds,heap_expected):assert evaluate(seed)==want
    simd_source=ROOT/'tests/simd_fixture.rs'
    export(simd_source)
    run(['rustc','+'+TOOLCHAIN,simd_source,'--edition=2024','-o',work/'simd-native'])
    simd_expected=run([work/'simd-native',*seeds]).splitlines()
    for seed,want in zip(seeds,simd_expected):assert evaluate(seed)==want
    dst_source=ROOT/'tests/dst_fixture.rs'
    # Exercise the explicitly benchmarked MIR inlining configurations against
    # native Rust as well as both custom engines. These are not engine defaults.
    mir_inline_modes=[('mir-inline'+str(scale),['-Zmir-opt-level=3',
                       '-Zinline-mir-threshold='+str(50*scale),
                       '-Zinline-mir-hint-threshold='+str(100*scale),
                       '-Zinline-mir-forwarder-threshold='+str(30*scale)])
                      for scale in [2,4,8]]
    dst_modes=[('debug',[]),('mir3',['-Zmir-opt-level=3']),('optimized',['-Copt-level=3','-Coverflow-checks=yes'])]+mir_inline_modes
    for _,options in mir_inline_modes:
        for name in cases:
            export(work/(name+'.rs'),extra=options,success=False)
    for mode,options in dst_modes:
        export(dst_source,extra=options)
        native=work/('dst-native-'+mode)
        run(['rustc','+'+TOOLCHAIN,dst_source,'--edition=2024',*options,'-o',native])
        expected=run([native,*seeds]).splitlines()
        for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(mode,seed,want)
    pointer_mask_source=ROOT/'tests/pointer_mask_fixture.rs'
    for mode,options in dst_modes:
        export(pointer_mask_source,extra=options)
        native=work/('pointer-mask-native-'+mode)
        run(['rustc','+'+TOOLCHAIN,pointer_mask_source,'--edition=2024',*options,'-o',native])
        expected=run([native,*seeds]).splitlines()
        for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(mode,seed,want)
    checked_arithmetic_source=ROOT/'tests/checked_arithmetic_fixture.rs'
    for mode,options in dst_modes:
        export(checked_arithmetic_source,extra=options)
        native=work/('checked-arithmetic-native-'+mode)
        run(['rustc','+'+TOOLCHAIN,checked_arithmetic_source,'--edition=2024',*options,'-o',native])
        expected=run([native,*seeds]).splitlines()
        for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(mode,seed,want)

    division_source=ROOT/'tests/division_fixture.rs'
    for mode,options in dst_modes:
        export(division_source,extra=options)
        native=work/('division-native-'+mode)
        run(['rustc','+'+TOOLCHAIN,division_source,'--edition=2024',*options,'-o',native])
        expected=run([native,*seeds]).splitlines()
        for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(mode,seed,want)

    scalar_constant_source=ROOT/'tests/scalar_constant_fixture.rs'
    for mode,options in dst_modes:
        export(scalar_constant_source,extra=options)
        native=work/('scalar-constant-native-'+mode)
        run(['rustc','+'+TOOLCHAIN,scalar_constant_source,'--edition=2024',*options,'-o',native])
        expected=run([native,*seeds]).splitlines()
        for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(mode,seed,want)
    from std_mir import checked_std_mir
    std_root,_,std_key,_=checked_std_mir(TOOLCHAIN)
    type_id_source=ROOT/'tests/type_id_fixture.rs'
    for mode,options in dst_modes:
        export(type_id_source,sysroot=std_root,extra=options,crate_name='type_id_case')
        native=work/('type-id-native-'+mode)
        run(['rustc','+'+TOOLCHAIN,type_id_source,'--crate-name','type_id_case','--edition=2024',*options,'-o',native])
        expected=run([native,*seeds]).splitlines()
        for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(mode,seed,want)
    carrying_source=ROOT/'tests/carrying_fixture.rs'
    coercion_source=ROOT/'tests/coercion_fixture.rs'
    closure_pointer_source=ROOT/'tests/closure_pointer_fixture.rs'
    for sysroot_label,sysroot in [('installed',None),('metadata',std_root)]:
        for mode,options in dst_modes:
            export(closure_pointer_source,sysroot=sysroot,extra=options)
            native=work/('closure-pointer-native-'+sysroot_label+'-'+mode)
            run(['rustc','+'+TOOLCHAIN,closure_pointer_source,'--edition=2024',*options,'-o',native])
            expected=run([native,*seeds]).splitlines()
            for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(sysroot_label,mode,seed,want)
            export(coercion_source,sysroot=sysroot,extra=options)
            native=work/('coercion-native-'+sysroot_label+'-'+mode)
            run(['rustc','+'+TOOLCHAIN,coercion_source,'--edition=2024',*options,'-o',native])
            expected=run([native,*seeds]).splitlines()
            for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(sysroot_label,mode,seed,want)
            export(carrying_source,sysroot=sysroot,extra=options)
            native=work/('carrying-native-'+sysroot_label+'-'+mode)
            run(['rustc','+'+TOOLCHAIN,carrying_source,'--edition=2024',*options,'-o',native])
            expected=run([native,*seeds]).splitlines()
            for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(sysroot_label,mode,seed,want)
    dynamic_source=ROOT/'tests/dynamic_fixture.rs'
    export(dynamic_source,sysroot=std_root)
    run(['rustc','+'+TOOLCHAIN,dynamic_source,'--edition=2024','-o',work/'dynamic-native'])
    dynamic_expected=run([work/'dynamic-native',*seeds]).splitlines()
    for seed,want in zip(seeds,dynamic_expected):assert evaluate(seed)==want
    float_source=ROOT/'tests/float_fixture.rs'
    export(float_source,sysroot=std_root)
    run(['rustc','+'+TOOLCHAIN,float_source,'--edition=2024','-o',work/'float-native'])
    float_expected=run([work/'float-native',*seeds]).splitlines()
    for seed,want in zip(seeds,float_expected):assert evaluate(seed)==want,(seed,want)
    atomic_source=ROOT/'tests/atomic_fixture.rs'
    export(atomic_source,sysroot=std_root)
    run(['rustc','+'+TOOLCHAIN,atomic_source,'--edition=2024','-o',work/'atomic-native'])
    atomic_expected=run([work/'atomic-native',*seeds]).splitlines()
    for seed,want in zip(seeds,atomic_expected):assert evaluate(seed)==want,(seed,want)
    static_source=ROOT/'tests/static_fixture.rs'
    export(static_source,sysroot=std_root)
    run(['rustc','+'+TOOLCHAIN,static_source,'--edition=2024','-o',work/'static-native'])
    static_expected=run([work/'static-native',*seeds]).splitlines()
    for seed,want in zip(seeds,static_expected):assert evaluate(seed)==want,(seed,want)
    tls_source=ROOT/'tests/tls_fixture.rs'
    tls_batch_source=ROOT/'tests/tls_batch_fixture.rs'
    uninhabited_source=ROOT/'tests/uninhabited_fixture.rs'
    for mode,options in dst_modes:
        native=work/('uninhabited-native-'+mode)
        run(['rustc','+'+TOOLCHAIN,uninhabited_source,'--edition=2024',*options,'-o',native])
        expected=run([native,*seeds]).splitlines()
        export(uninhabited_source,extra=options)
        for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(mode,seed,want)
        native=work/('tls-native-'+mode)
        run(['rustc','+'+TOOLCHAIN,tls_source,'--edition=2024',*options,'-o',native])
        # Each native process gets fresh TLS, matching a fresh VM invocation.
        expected=[run([native,seed]) for seed in seeds]
        export(tls_source,sysroot=std_root,extra=options)
        for seed,want in zip(seeds,expected):assert evaluate(seed)==want,(mode,seed,want)
        native_batch=work/('tls-batch-native-'+mode)
        run(['rustc','+'+TOOLCHAIN,tls_batch_source,'--edition=2024','--test',*options,'-o',native_batch])
        assert '2 passed' in run([native_batch,'--test-threads=1'])
        for sysroot in [None,std_root]:
            export(tls_batch_source,sysroot=sysroot,extra=['--test',*options],test_body=True,entries=['a_first','b_second'])
            for engine in ['interpreter','jit']:
                assert run([BUILD/'rust-interp-vm','--engine',engine,work/'program.rbc'])=='0'
    caller_source=ROOT/'tests/caller_fixture.rs'
    for mode,options in [('ordinary',[]),('mir-inline',['-Zmir-opt-level=3','-Copt-level=1'])]+mir_inline_modes:
        export(caller_source,sysroot=std_root,extra=options)
        run(['rustc','+'+TOOLCHAIN,caller_source,'--edition=2024',*options,'-o',work/('caller-native-'+mode)])
        caller_expected=run([work/('caller-native-'+mode),*seeds]).splitlines()
        for seed,want in zip(seeds,caller_expected):assert evaluate(seed)==want,(mode,seed,want)
        # A tracked CLI root is reified like the native function pointer in
        # fixture case 2, rather than requiring a caller argument from the CLI.
        export(caller_source,sysroot=std_root,extra=options,entry='tracked')
        for engine in ['interpreter','jit']:
            assert run([BUILD/'rust-interp-vm','--engine',engine,work/'program.rbc'])==caller_expected[2]
    # These exercise our guest-memory checks only; never execute UB natively.
    for name,body in [
        ('unaligned-atomic', 'let a = [0u64;2]; let p = a.as_ptr().cast::<u8>().wrapping_add(1).cast::<u64>(); unsafe { core::intrinsics::atomic_load::<u64, {core::intrinsics::AtomicOrdering::Relaxed}, false>(p) }'),
        ('out-of-bounds-atomic', 'unsafe { core::intrinsics::atomic_load::<u64, {core::intrinsics::AtomicOrdering::Relaxed}, false>(0xffff_fff8usize as *const u64) }'),
        ('read-only-atomic-write', 'unsafe { core::intrinsics::atomic_store::<u64, {core::intrinsics::AtomicOrdering::Relaxed}, false>(&7u64 as *const u64 as *mut u64, a); } 0'),
    ]:
        bad=work/(name+'.rs')
        bad.write_text('#![feature(core_intrinsics)] pub fn rust_interp_entry(a:u64)->u64 { '+body+' } fn main() {}\n')
        export(bad,sysroot=std_root)
        evaluate(1,success=False)
        expected_error = {'unaligned-atomic':'unaligned atomic',
                          'out-of-bounds-atomic':'invalid guest memory access',
                          'read-only-atomic-write':'write to read-only guest memory'}[name]
        assert expected_error in records[-2]['stderr'],records[-2]['stderr']
        jit_errors = [expected_error] if name=='unaligned-atomic' else [expected_error,'JIT guest memory access failed']
        assert any(message in records[-1]['stderr'] for message in jit_errors),records[-1]['stderr']
    for name,body in [
        ('release-atomic-load', 'let value=7u64; unsafe { core::intrinsics::atomic_load::<u64, {core::intrinsics::AtomicOrdering::Release}, false>(&value) }'),
        ('relaxed-atomic-fence', 'unsafe { core::intrinsics::atomic_fence::<{core::intrinsics::AtomicOrdering::Relaxed}>(); } a'),
    ]:
        bad=work/(name+'.rs')
        bad.write_text('#![feature(core_intrinsics)] pub fn rust_interp_entry(a:u64)->u64 { '+body+' } fn main() {}\n')
        export(bad,success=False,sysroot=std_root)
        assert 'invalid atomic memory ordering' in records[-1]['stderr'] or 'invalid relaxed atomic fence' in records[-1]['stderr']
    custom_allocator=work/'custom-allocator.rs'
    custom_allocator.write_text('#[global_allocator] static A: std::alloc::System = std::alloc::System; pub fn rust_interp_entry(a:u64)->u64 { *Box::new(a) } fn main() {}\n')
    export(custom_allocator,success=False)
    for name,prefix,body in [
        ('foreign-thread-local','#![feature(thread_local)] unsafe extern "C" { #[thread_local] static VALUE:u64; }','unsafe { VALUE }'),
        ('foreign-static','unsafe extern "C" { static VALUE:u64; }','unsafe { VALUE }'),
    ]:
        unsupported=work/(name+'.rs')
        unsupported.write_text(prefix+' pub fn rust_interp_entry(a:u64)->u64 { '+body+' } fn main() {}\n')
        export(unsupported,success=False)
    tls_drop=work/'tls-drop.rs'
    tls_drop.write_text('thread_local! { static VALUE: std::cell::RefCell<Vec<u64>> = const { std::cell::RefCell::new(Vec::new()) }; } pub fn rust_interp_entry(a:u64)->u64 { VALUE.with(|v| {v.borrow_mut().push(a);v.borrow()[0]}) } fn main() {}\n')
    export(tls_drop,sysroot=std_root,success=False)
    # Registration now lowers; strict mode still rejects the required unwind intrinsic.
    assert 'unsupported intrinsic catch_unwind' in records[-1]['stderr'],records[-1]['stderr']
    tls_access=work/'tls-access-error.rs'
    tls_access.write_text('#![feature(thread_local_internals)] const KEY:std::thread::LocalKey<u64>=unsafe{std::thread::LocalKey::new(|_|std::ptr::null())}; pub fn rust_interp_entry(a:u64)->u64 {assert!(KEY.try_with(|v|*v).is_err()); if a==0 {7} else {KEY.with(|v|*v)}} fn main(){println!("{}",rust_interp_entry(std::env::args().nth(1).unwrap().parse().unwrap()));}\n')
    run(['rustc','+'+TOOLCHAIN,tls_access,'--edition=2024','-o',work/'tls-access-native'])
    assert run([work/'tls-access-native',0])=='7'
    run([work/'tls-access-native',1],success=False)
    for sysroot in [None,std_root]:
        export(tls_access,sysroot=sysroot)
        assert evaluate(0)=='7'
        evaluate(1,success=False)
        assert 'panic_access_error' in records[-1]['stderr'],records[-1]['stderr']
    tls_namespace=work/'tls-panic-namespace.rs'
    tls_namespace.write_text('pub mod thread {pub mod local {pub fn panic_access_error()->! {unsafe extern "C" {fn fake_tls_abort()->!;} unsafe{fake_tls_abort()}}}} pub fn rust_interp_entry(a:u64)->u64 {if a==0 {7} else {thread::local::panic_access_error()}} fn main() {}\n')
    export(tls_namespace,success=False,crate_name='std')
    assert 'fake_tls_abort' in records[-1]['stderr'],records[-1]['stderr']
    for payload in ['()', 'std::mem::MaybeUninit<std::convert::Infallible>', '&\'static std::convert::Infallible']:
        reachable=work/'inhabited-unsupported.rs'
        reachable.write_text('unsafe extern "C" {fn reachable_foreign_call()->u64;} enum State<T>{Left(u64),Missing(T)} fn select<T>(s:State<T>)->u64 {match s {State::Left(a)=>a,State::Missing(_)=>unsafe{reachable_foreign_call()}}} pub fn rust_interp_entry(a:u64)->u64 {select::<'+payload+'>(State::Left(a))} fn main() {}\n')
        export(reachable,success=False)
        assert 'reachable_foreign_call' in records[-1]['stderr'],records[-1]['stderr']
    for declaration,body in [
        ('unsafe extern "C" {fn abort()->u64;}', 'unsafe {abort()}'),
        ('unsafe extern "C" {fn CCRandomGenerateBytes(p:*mut u8,n:u32)->i32;}', 'let mut b=0;unsafe {CCRandomGenerateBytes(&mut b,1) as u64}'),
    ]:
        bad=work/'bad-system-signature.rs'
        bad.write_text(declaration+' pub fn rust_interp_entry(a:u64)->u64 {'+body+'} fn main() {}\n')
        export(bad,success=False)
        assert 'signature' in records[-1]['stderr'],records[-1]['stderr']

    panics = work / 'panics.rs'
    panics.write_text('pub fn rust_interp_entry(a: u64) -> u64 { a + 1 }\nfn main() {}\n')
    export(panics)
    evaluate(2**64-1,success=False)
    abort=work/'abort.rs'
    abort.write_text('#![feature(core_intrinsics)] #![allow(internal_features)] pub fn rust_interp_entry(a:u64)->u64 { if a==1 {std::intrinsics::abort()} a } fn main() {}\n')
    export(abort)
    assert evaluate(7)=='7'
    evaluate(1,success=False)
    exact=work/'exact-division.rs'
    exact.write_text('#![feature(core_intrinsics)] #![allow(internal_features)] pub fn rust_interp_entry(a:u64)->u64 { unsafe {std::intrinsics::exact_div(a,3)} } fn main() {}\n')
    export(exact)
    for n in [0,3,99,2**64-1]:assert evaluate(n)==str(n//3)
    for n in [1,4,2**64-2]:evaluate(n,success=False)
    result_case=work/'result-unwrap.rs'
    result_case.write_text('#[derive(Debug)] struct Error; pub fn rust_interp_entry(a:u64)->u64 { let r=if a&1==0 {Ok(a.wrapping_add(3))} else {Err(Error)}; r.unwrap() } fn main() {}\n')
    export(result_case)
    for n in [0,2,16]:assert evaluate(n)==str(n+3)
    evaluate(1,success=False)
    namespace=work/'panic-namespace.rs'
    namespace.write_text('mod core { pub mod panicking { pub fn ordinary(a:u64)->u64 {a+9} } } pub fn rust_interp_entry(a:u64)->u64 {core::panicking::ordinary(a)} fn main() {}\n')
    export(namespace)
    assert evaluate(19)=='28'
    # The exact def-path in a user crate must not acquire alloc's panic shim.
    alloc_namespace=work/'alloc-panic-namespace.rs'
    alloc_namespace.write_text('pub mod sync { pub fn panic_arc_overflow()->! { unsafe extern "C" { fn fake_alloc_abort()->!; } unsafe { fake_alloc_abort() } } } pub fn rust_interp_entry(a:u64)->u64 { if a==0 {7} else {sync::panic_arc_overflow()} } fn main() {}\n')
    export(alloc_namespace,success=False,crate_name='alloc')
    assert 'fake_alloc_abort' in records[-1]['stderr']
    integer_panic_source=ROOT/'tests/integer_panic_fixture.rs'
    integer_cases=[(0,7,True),(0,2**64-1,False),(1,3,True),(1,2**64-1,False),
                   (2,3,True),(2,0,False),(3,7,True),(3,2**64-1,False),
                   (4,1,True),(4,2**63,False),(5,9,True),(6,2,True),(6,64,False),
                   (7,3,True),(7,2**63,False),(8,19,True),(9,2,True),(9,64,False),
                   (10,3,True),(10,2**63,False),(11,100,True),(11,0,False),
                   (12,8,True),(12,0,False),(13,9,True),(13,0,False)]
    for mode,flags in [('debug',[]),('mir3',['-Zmir-opt-level=3']),('optimized',['-Copt-level=3'])]+mir_inline_modes:
        # Installed sysroot only: no custom std MIR is needed for panic helpers.
        export(integer_panic_source,extra=flags)
        native=work/('integer-panic-native-'+mode)
        run(['rustc','+'+TOOLCHAIN,integer_panic_source,'--edition=2024',*flags,'-o',native])
        for case,value,success in integer_cases:
            expected=run([native,case,value],success=success)
            for engine in ['interpreter','jit']:
                got=run([BUILD/'rust-interp-vm','--engine',engine,work/'program.rbc',case,value],success=success)
                if success:assert got==expected
                else:assert 'guest trap:' in records[-1]['stderr']
    slicing=work/'slice-range.rs'
    slicing.write_text('pub fn rust_interp_entry(a:u64)->u64 { let bytes=[1u8,2,3,4]; bytes[..a as usize].len() as u64 } fn main() {}\n')
    export(slicing)
    for n in [0,2,4]:assert evaluate(n)==str(n)
    evaluate(5,success=False)
    string_slicing=work/'string-slice-range.rs'
    string_slicing.write_text('pub fn rust_interp_entry(a:u64)->u64 { "éx"[..a as usize].len() as u64 } fn main() {}\n')
    export(string_slicing)
    for n in [0,2,3]:assert evaluate(n)==str(n)
    for n in [1,4]:evaluate(n,success=False)
    unused_pointer=work/'unused-function-pointer.rs'
    unused_pointer.write_text('fn unsupported(a:u64)->u64 { unsafe extern "C" { fn getpid()->i32; } a.wrapping_add(unsafe {getpid()} as u64) } pub fn rust_interp_entry(a:u64)->u64 { let p=std::hint::black_box(unsupported as fn(u64)->u64); a+((p as usize != 0) as u64) } fn main() {}\n')
    export(unused_pointer)
    assert evaluate(12)=='13'
    called_pointer=work/'called-function-pointer.rs'
    called_pointer.write_text('fn unsupported(a:u64)->u64 { unsafe extern "C" { fn getpid()->i32; } a.wrapping_add(unsafe {getpid()} as u64) } pub fn rust_interp_entry(a:u64)->u64 { let p=std::hint::black_box(unsupported as fn(u64)->u64); p(a) } fn main() {}\n')
    export(called_pointer,success=False)
    mixed_pointers=work/'mixed-function-pointer-shapes.rs'
    mixed_pointers.write_text('fn unused(a:u64,b:u64)->f64 { unsafe extern "C" { fn getpid()->i32; } (a+b+unsafe {getpid()} as u64) as f64 } fn called(a:i64)->i64 {a.wrapping_add(7)} pub fn rust_interp_entry(a:u64)->u64 { let unused=std::hint::black_box(unused as fn(u64,u64)->f64); let f:fn(u64)->u64=unsafe {std::mem::transmute(called as fn(i64)->i64)}; f(a)^((unused as usize != 0) as u64) } fn main() {}\n')
    export(mixed_pointers)
    for n in [0,2**63,2**64-1]:assert evaluate(n)==str(((n+7)%(2**64))^1)
    # Re-create a successful artifact for the following corruption checks.
    export(slicing)
    corrupt = work / 'corrupt.rbc'
    corrupt.write_bytes((work / 'program.rbc').read_bytes()[:31])
    run([BUILD / 'rust-interp-vm', corrupt, 0], success=False)
    for flags in [['--emit=metadata,llvm-ir'],['--emit=metadata','--emit=link'],['--emit','metadata,asm']]:
        env=os.environ.copy()
        env.update(RUST_INTERP_OUTPUT=str(work/'program.rbc'),RUST_INTERP_ENTRY='rust_interp_entry',RUST_INTERP_DEMAND_BODIES='0')
        (work/'program.rbc').write_bytes(b'previous artifact')
        run([BUILD/'rust-interp-mir-export',panics,*flags,'-o',work/'forbidden-output'],env,success=False)
        assert not (work/'program.rbc').exists()

    audit_selection=work/'audit-selection.json'
    audit_selection.write_text(json.dumps(['rust_interp_entry']))
    for cache in ['0','1']:
        env=os.environ.copy()
        for name in ['RUST_INTERP_ENTRY','RUST_INTERP_ENTRIES']:env.pop(name,None)
        env.update(RUST_INTERP_OUTPUT=str(work/'audit.json'),RUST_INTERP_AUDIT_SELECTION=str(audit_selection),
                   RUST_INTERP_DEMAND_BODIES='1',RUST_INTERP_DEMAND_CACHE=cache)
        (work/'audit.json').write_text('previous report')
        run([BUILD/'rust-interp-mir-export',panics,'--emit=metadata','-o',work/'audit.rmeta'],env,success=False)
        assert 'lowering audits require ordinary strict frontend checking' in records[-1]['stderr']
        assert not (work/'audit.json').exists()

    executed_errors={
        'called-type-error':'let _: u8 = "bad"; a',
        'called-borrow-error':'let mut x = a; let y = &x; x = 2; *y',
        'called-unsafety-error':'let p = &a as *const u64; *p',
    }
    for policy in ['demand','demand-cache']:
        export(source,policy=policy)
        for seed,want in zip(seeds,expected):
            assert evaluate(seed)==want
        for name in ['uncalled-type-error','uncalled-borrow-error']:
            export(work/(name+'.rs'),policy=policy)
            assert evaluate(19)=='19'
        for name,body in executed_errors.items():
            bad=work/(name+'.rs')
            bad.write_text('pub fn rust_interp_entry(a: u64) -> u64 { '+body+' }\nfn main() {}\n')
            export(bad,success=False,policy=policy)
    # Reuse a committed compiler session across actual callee and layout edits.
    edited=work/'edited.rs'
    for index,body in enumerate([
        'fn callee(a: u64) -> u64 { a.wrapping_mul(3) }',
        'fn callee(a: u64) -> u64 { a.wrapping_mul(7) }',
        'struct Pair(u8,u64); fn callee(a: u64) -> u64 { let p=Pair(11,a); p.1.wrapping_add(p.0 as u64) }',
        'struct Pair(u64,u8); fn callee(a: u64) -> u64 { let p=Pair(a,13); p.0.wrapping_add(p.1 as u64) }',
        'fn helper(a: u64) -> u64 { !a } fn callee(a: u64) -> u64 { helper(a) }',
    ]):
        edited.write_text(body+'\npub fn rust_interp_entry(a:u64)->u64 { callee(a) }\nfn main() { for s in std::env::args().skip(1) { println!("{}",rust_interp_entry(s.parse().unwrap())); } }\n')
        export(edited,policy='demand-cache')
        run(['rustc','+'+TOOLCHAIN,edited,'--edition=2024','-o',work/'edited-native'])
        values=[0,127,2**64-1]
        wants=run([work/'edited-native',*values]).splitlines()
        for value,want in zip(values,wants):
            assert evaluate(value)==want
    cache_files=list((work/'demand-cache/incremental').rglob('query-cache.bin'))
    assert cache_files and any(not p.parent.name.endswith('-working') for p in cache_files)
    summary = dict(raw=str(work.relative_to(ROOT)), differential_inputs_per_policy=len(seeds),policies=['strict','demand','demand-cache'],
                   engines=['interpreter','jit'],
                   rejected_invalid_sources=list(cases), rejected_unsupported=['custom-global-allocator','float16','external-call'],
                   heap_differential_inputs=len(seeds),
                   simd_differential_inputs=len(seeds),
                   dynamic_differential_inputs=len(seeds),
                   nested_dst_differential_inputs_per_mode=len(seeds),
                   nested_dst_modes=[mode for mode,_ in dst_modes],
                   nested_dst_alignment_packing_upcasts_and_drop_checked=True,
                   pointer_mask_inputs_per_mode=len(seeds),
                   pointer_mask_modes=[mode for mode,_ in dst_modes],
                   type_id_native_inputs_per_mode=len(seeds),
                   type_id_modes=[mode for mode,_ in dst_modes],
                   type_id_hashes_aggregates_any_and_io_error_downcasts_checked=True,
                   type_id_sysroot='metadata',
                   pointer_mask_stack_heap_mutability_and_metadata_checked=True,
                   checked_arithmetic_native_inputs_per_mode=len(seeds),
                   checked_arithmetic_modes=[mode for mode,_ in dst_modes],
                   checked_arithmetic_integer_types=12,
                   division_native_inputs_per_mode=len(seeds),
                   division_modes=[mode for mode,_ in dst_modes],
                   division_integer_types=12,
                   scalar_constant_native_inputs_per_mode=len(seeds),
                   scalar_constant_modes=[mode for mode,_ in dst_modes],
                   scalar_constant_numeric_bits_call_storage_and_pointer_relocations_checked=True,
                   carrying_mul_add_inputs_per_configuration=len(seeds),
                   carrying_mul_add_integer_types=12,
                   carrying_mul_add_modes=[mode for mode,_ in dst_modes],
                   carrying_mul_add_sysroots=['installed','metadata'],
                   ordinary_intrinsic_bodies_lowered_in_custom_engine=True,
                   structural_coercion_inputs_per_configuration=len(seeds),
                   structural_coercion_modes=[mode for mode,_ in dst_modes],
                   structural_coercion_sysroots=['installed','metadata'],
                   smart_pointer_weak_drop_allocator_and_aliasing_checked=True,
                   arc_overflow_shim_crate_identity_checked=True,
                   closure_pointer_inputs_per_configuration=len(seeds),
                   closure_pointer_modes=[mode for mode,_ in dst_modes],
                   closure_pointer_sysroots=['installed','metadata'],
                   closure_pointer_constants_tuples_aggregates_and_unsafe_calls_checked=True,
                   zero_sized_argument_evaluation_alignment_and_drop_checked=True,
                   float_differential_inputs=len(seeds),
                   population_count_differential_inputs=len(seeds),
                   population_count_signed_unsigned_widths=[8,16,32,64,128],
                   atomic_differential_inputs=len(seeds),
                   sequential_atomic_operations_and_arc_checked=True,
                   dynamic_std_mir_key=std_key,
                   virtual_calls_upcasts_and_dynamic_slice_drop_checked=True,
                   exact_division_remainder_checked=True,
                   immutable_static_cycles_and_alignment_checked=True,
                   foreign_statics_and_tls_destructor_registration_rejected=True,
                   single_thread_tls_native_inputs_per_mode=len(seeds),
                   tls_modes=[mode for mode,_ in dst_modes],
                   tls_batch_process_statics_preserved_and_tls_reset=True,
                   tls_randomstate_hashmap_semantics_checked=True,
                   uninhabited_branches_and_reachable_foreign_rejections_checked=True,
                   foreign_system_shim_names_and_signatures_checked=True,
                   overflow_traps=True, corrupt_artifact_rejected=True,
                   partial_modes_accept_uncalled_errors=True,partial_modes_reject_called_errors=list(executed_errors),
                   committed_cache_edit_states=5,committed_cache_present=True,
                   native_emission_requests_rejected=True,
                   audits_reject_partial_checking=True,
                   result_unwrap_and_panic_namespace_checked=True,
                   integer_overflow_panic_cases=len(integer_cases),
                   integer_overflow_panic_modes=['debug','mir3','optimized']+[mode for mode,_ in mir_inline_modes],
                   slice_range_bounds_checked=True,
                   string_slice_bounds_and_utf8_checked=True,
                   indirect_calls_and_address_only_bodies_checked=True,
                   external_constructors_native_inputs=len(seeds),
                   native_test_result_cases=result_cases,
                   mutable_static_native_inputs=len(seeds),
                   caller_location_native_inputs_per_mode=len(seeds),
                   caller_location_modes=['ordinary','mir-inline']+[mode for mode,_ in mir_inline_modes],
                   mir_inlining_configurations={mode:flags for mode,flags in mir_inline_modes},
                   inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,popcount_source,local_layout_source,constructor_dependency,constructor_source,result_source,heap_source,simd_source,dynamic_source,dst_source,pointer_mask_source,checked_arithmetic_source,division_source,scalar_constant_source,type_id_source,carrying_source,coercion_source,closure_pointer_source,float_source,atomic_source,static_source,tls_source,tls_batch_source,uninhabited_source,caller_source,integer_panic_source,Path(__file__),BUILD/'rust-interp-vm',BUILD/'rust-interp-mir-export']})
    checkpoint()
    atexit.unregister(checkpoint)
    summary.update(completed_commands=len(records), elapsed_seconds=time.perf_counter()-started,
                   subprocess_seconds=sum(record['seconds'] for record in records))
    (ROOT / 'results/interpreter-validation.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
