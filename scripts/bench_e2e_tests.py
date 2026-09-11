#!/usr/bin/env python3
"""Real edit-to-test commands, including Cargo, launcher, compiler, and execution.

Adds deterministic regression assertions to existing project tests without
reducing their workloads. A deliberately wrong assertion first checks that
every engine executes the requested new source.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from interpreter import ROOT, TOOLCHAIN, checked_tools


CASES = {
    'pgrust': dict(package='hashfn', file='crates/common/hashfn/src/lib.rs',
                  test='tests::murmurhash32_inverse_roundtrips',
                  workload='Original 100,000-iteration roundtrip loop'),
    'fre': dict(package='fre-kernels', file='crates/fre-kernels/src/determinize_state_codec.rs',
                test='determinize_state_codec::tests::unsigned_roundtrips_boundaries',
                workload='Original seven codec boundary roundtrips'),
    'nushell': dict(package='nu-parser', file='crates/nu-parser/src/parse_keywords.rs',
                    test='parse_keywords::tests::is_parser_keyword_matches_single_word_keywords',
                    workload='Original five parser-keyword assertions'),
    'ruff': dict(package='ruff_linter', file='crates/ruff_linter/src/registry.rs',
                 test='registry::tests::documentation',
                 workload='Original documentation check for every registered rule'),
    'rg-aot': None, # The private test adapter is kept under ignored .work/.
}


def reference(v):
    v ^= v >> 16
    v = (v * 0x85ebca6b) & 0xffffffff
    v ^= v >> 13
    v = (v * 0xc2b2ae35) & 0xffffffff
    return v ^ (v >> 16)


def assertion(project, seed, should_pass, case):
    if case.get('private'):
        text=f'row_{seed}'
        return case['assertion'].format(input=text+'\\n',expected=len(text) if should_pass else 0)
    if project == 'pgrust':
        want = reference(seed) ^ (0 if should_pass else 1)
        return f'        assert_eq!(murmurhash32({seed}), {want});\n'
    if project == 'nushell':
        negate = '!' if should_pass else ''
        return f'        assert!({negate}is_parser_keyword(b"rust_interp_command_{seed}"));\n'
    if project == 'ruff':
        predicate = 'is_some' if should_pass else 'is_none'
        return f'        let added_rule = Rule::iter().nth({seed % 17}).unwrap();\n        assert!(added_rule.explanation().{predicate}());\n'
    want = seed ^ (0 if should_pass else 1)
    return f'''        let added_requirements = encode_requirements({seed}).unwrap();
        let mut added_bytes = [0; MAX_ENCODED_BYTES];
        encode_u32({seed}, &mut added_bytes, limits(added_requirements)).unwrap();
        let added_decode = decode_requirements(added_requirements.output_bytes).unwrap();
        assert_eq!(decode_u32(&added_bytes[..added_requirements.output_bytes],
                   limits(added_decode)).unwrap().value, {want});
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',default='e2e-tests-'+str(time.time_ns()))
    parser.add_argument('--modes',nargs='+',default=['native','interpreter','jit'],choices=['native','interpreter','jit'])
    parser.add_argument('--project',choices=CASES,default='pgrust')
    parser.add_argument('--cold',action='store_true',help='also time a successful first build in independent empty artifact caches')
    args=parser.parse_args()
    if Path(args.run_id).name != args.run_id or args.run_id in ['.', '..']:
        parser.error('--run-id must be a directory name')
    if len(set(args.modes)) != len(args.modes):
        parser.error('duplicate execution modes')
    case=CASES[args.project]
    if case is None:
        private=json.loads((ROOT/'.work/private/e2e-rg-aot.json').read_text())
        if private['owner']!=str(ROOT):raise RuntimeError('private adapter ownership mismatch')
        case=private['case']
    lock=(ROOT/'.work/benchmark.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    tools,key=checked_tools() # Bootstrap is outside the timed development loop.
    source=ROOT/'.work/sources'/args.project
    revision=json.loads((ROOT/'benchmarks/corpus.json').read_text())['projects'][args.project]['revision']
    if case.get('private') and private['revision']!=revision:
        raise RuntimeError('private adapter revision mismatch')
    marker=json.loads((source/'.rust-interp-owned.json').read_text())
    if marker['owner']!=str(ROOT) or marker['revision']!=revision:
        raise RuntimeError('snapshot ownership or revision mismatch')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()!=revision:
        raise RuntimeError('snapshot HEAD mismatch')
    if subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip():
        raise RuntimeError('snapshot has tracked changes')
    work=ROOT/'.work/runs'/args.run_id
    work.mkdir(parents=True)
    file=source/case['file']
    original=file.read_bytes();current=original
    anchor='    fn '+case['test'].split('::')[-1]+'() {\n'
    assert original.decode().count(anchor)==1
    records=[]
    env=os.environ.copy()
    for name in list(env):
        if name.startswith(('RUST_INTERP_','CARGO_PROFILE_')) or name in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']:
            env.pop(name,None)
    env['CARGO_TERM_COLOR']='never'
    env['RUST_INTERP_LAUNCH_STATS']='1'
    def run(mode,state,should_pass):
        manifest=str(source/'Cargo.toml')
        if mode=='native':
            command=['cargo','+'+TOOLCHAIN,'test','--manifest-path',manifest,'--package',case['package'],'--lib','--locked','--offline','--jobs','4','--target-dir',str(work/'native'),case['test'],'--','--exact']
        else:
            command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',manifest,'--package',case['package'],'--entry',case['test'],'--test-body','--instruction-limit','1000000000']
            if mode=='jit':command+=['--engine','jit']
            if args.cold:command+=['--cache-namespace',args.run_id+':'+mode]
        start=time.perf_counter()
        p=subprocess.Popen(command,cwd=source,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr=p.communicate()
        record=dict(mode=mode,state=state,pid=p.pid,command=command,seconds=time.perf_counter()-start,returncode=p.returncode,stdout=stdout,stderr=stderr,source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),load=os.getloadavg())
        records.append(record)
        (work/'records.json').write_text(json.dumps(records,indent=2)+'\n')
        assert (p.returncode==0)==should_pass,stderr
        if should_pass:assert ('1 passed' in stdout) if mode=='native' else stdout.strip()=='0',stdout
        elif mode=='native':assert 'assertion' in stdout+stderr,stderr
        else:assert 'guest assertion:' in stderr or ('guest trap:' in stderr and ('core::panicking::' in stderr or 'std::panicking::' in stderr)),stderr
        assert (('Compiling ' if mode=='native' else 'Checking ')+case['package']) in stderr,'the edited crate did not compile'
        print(mode,state,round(record['seconds'],3),flush=True)
    try:
        for state in ([0,-1,1,2,3,4,5] if args.cold else [-1,0,1,2,3,4,5]):
            # Native and interpreter currently have independent caches. Future
            # execution modes must also force a real source change before each
            # command so sharing checked metadata cannot create a false win.
            for mode in (args.modes if state%2==0 else list(reversed(args.modes))):
                # Different literal values also invalidate semantic queries
                # when two execution engines share the same Cargo artifacts.
                seed=1000+state+1000*args.modes.index(mode)
                if file.read_bytes()!=current:raise RuntimeError('source changed outside this benchmark')
                current=original.decode().replace(anchor,anchor+assertion(args.project,seed,state!=-1,case)).encode()
                file.write_bytes(current)
                run(mode,state,state!=-1)
    finally:
        if file.read_bytes()!=current:raise RuntimeError('source changed outside this benchmark; refusing to overwrite it')
        file.write_bytes(original)
    med={mode:statistics.median(r['seconds'] for r in records if r['mode']==mode and r['state']>0) for mode in args.modes}
    cold={r['mode']:r['seconds'] for r in records if args.cold and r['state']==0}
    result=dict(project=args.project,revision=revision,test='existing line-iteration unit test' if case.get('private') else case['package']+'::'+case['test'],workload=case['workload'],edits='five additional regression assertions',includes_launcher=True,wrong_assertion_rejected=True,tool_key=key,
                cold_success_seconds=cold,independent_engine_caches=args.cold,
                case_sha256=hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest(),
                vm_sha256=hashlib.sha256((tools/'rust-interp-vm').read_bytes()).hexdigest(),
                exporter_sha256=hashlib.sha256((tools/'rust-interp-mir-export').read_bytes()).hexdigest(),
                scripts_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).resolve(),ROOT/'scripts/interpreter.py']},
                raw=str(work.relative_to(ROOT)),median_seconds=med,
                samples=[{k:v for k,v in r.items() if k not in ['pid','command','stdout','stderr']} for r in records])
    out=ROOT/'results'/args.run_id;out.mkdir()
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    report=f'# Existing {args.project} test: edit to result\n\nFull commands, including launcher and Cargo; five test-source edits. {case["workload"]} preserved. A deliberately wrong added assertion failed in every mode before timing successful edits.\n\n| Mode | Median edited command seconds |\n|---|---:|\n'+''.join(f'| {m} | {v:.3f} |\n' for m,v in med.items())
    if cold:
        report+='\nOne successful cold build per mode, with separate empty Cargo artifact directories. Engine bootstrap, the preinstalled toolchain/sysroot, and OS file-cache coldness are excluded.\n\n| Mode | Cold command seconds |\n|---|---:|\n'+''.join(f'| {m} | {v:.3f} |\n' for m,v in cold.items())
    (out/'summary.md').write_text(report)
    print(out/'summary.md')


if __name__=='__main__':main()
