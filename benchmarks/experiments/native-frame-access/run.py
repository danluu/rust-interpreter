"""Census exact private-frame accesses in retained adopted native captures."""
from bisect import bisect_right
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
from patterns import recognize,classify

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from summarize_owned_sample import parse_tree, self_samples
from workflow_io import capture, require_space, write_json as write
RUN = 'native-frame-access-census-01'


def read(p):
    assert p.stat().st_size <= 256 * 1024**2
    return json.loads(p.read_text())


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        frozen = {}
        def bind(path, expected=None):
            value = sha(path)
            if expected is not None: assert value == expected, path
            frozen[str(path.relative_to(ROOT))] = value
            return read(path) if path.suffix == '.json' else value
        prior = ROOT / 'results/adopted-current-runtime-sampling-02'
        closed = bind(prior / 'closure.json')
        assert closed['status'] == 'closed' and closed['all_hashes_verified']
        summary = bind(prior / 'summary.json', closed['summary_sha256'])
        evidence = bind(ROOT / closed['evidence'], closed['evidence_sha256'])
        for path,digest in evidence.items(): bind(ROOT/path,digest)
        for path in HERE.iterdir():
            if path.suffix in ['.py','.md']: bind(path)
        for name in ['compare_saved_runtime.py','summarize_owned_sample.py','workflow_io.py','vmmap_ranges.py']:
            bind(ROOT/'scripts'/name)
        for name in ['crates/bytecode/src/jit/resumable.rs','crates/bytecode/src/frames.rs','crates/bytecode/src/native_continuation.rs']:
            bind(ROOT/name)
        subprocess.run(['git','diff','--exit-code','fca687ebac0ea9374a1426addd01169fe707f608','--',
            'crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,check=True,capture_output=True)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw = ROOT/'.work'/RUN
        raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,
            guest_commands=0,builds=0,executable_code_publications=0,performance_measurement=False,
            maximum_spans=2_000_000,minimum_initial_gib=12,minimum_child_gib=8,
            archived_vm_source_receipt=closed['source_revision'],expected_controls=6))
        command=[sys.executable,'-m','unittest','test_patterns','-v']
        require_space(ROOT,8)
        child,out,err=capture(command,cwd=HERE,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=raw/'active.json',receipt=dict(stage='exact private-frame pattern controls'))
        (raw/'controls.stdout').write_text(out)
        (raw/'controls.stderr').write_text(err)
        write(raw/'record.json',dict(command=command,pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/'controls.stdout'),stderr_sha256=sha(raw/'controls.stderr')))
        assert child.returncode==0 and 'Ran 6 tests' in err and err.rstrip().endswith('OK'),err
        results,details=[],[]
        for case in summary['cases']:
            label=case['case']
            folder=ROOT/'.work'/case['run_id']/'0'
            mapping=read(folder/'jit-code/operations.json')
            code=(folder/'jit-code/code.bin').read_bytes()
            assert len(code)<=16*1024**2 and len(code)==mapping['code_bytes']
            assert hashlib.sha256(code).hexdigest()==mapping['code_sha256']
            assert mapping['schema_version']==2 and mapping['complete'] and mapping['reconstructed_bytes_match']
            assert not mapping['profiled'] and mapping['persistent_registers'] and mapping['resumable_calls']
            functions=mapping['functions']
            starts=[f['offset'] for f in functions]
            assert starts==sorted(set(starts)) and starts[0]==0 and functions[-1]['end']==len(code)
            assert all(a['end']==b['offset'] for a,b in zip(functions,functions[1:]))
            old_report=read(ROOT/case['report'])
            profile_path,=[p for p in old_report['evidence'] if p.endswith('-profile.json')]
            assert profile_path in frozen
            profile=read(ROOT/profile_path)
            sites=[];candidate_pcs={};window_pcs={};span_count=0;transitions=Counter()
            cursor=0
            for f in functions:
                fid=f['function'];typed=profile['functions'][fid]
                assert f['name']==typed['name']
                for span in f['spans']:
                    span_count+=1;assert span_count<=2_000_000
                    assert span['offset']==cursor and cursor<=span['end']<=f['end'] and span['end']%4==0
                    cursor=span['end']
                    if span['kind']!='transition':continue
                    operation=typed['operations'][span['pc']].split(' ',1)[0]
                    assert operation in ['Call','Return']
                    transitions[operation]+=1
                    data=code[span['offset']:span['end']]
                    words=struct.unpack('<'+'I'*(len(data)//4),data)
                    found=recognize(words,operation,span['offset'])
                    for site in found:
                        sites.append(dict(function=fid,name=f['name'],pc=span['pc'],operation=operation,**site))
                        for offset in site['memory_offsets']:
                            assert offset not in candidate_pcs
                            candidate_pcs[offset]=site['kind']
                        for offset in range(site['offset'],site['end'],4):
                            assert offset not in window_pcs
                            window_pcs[offset]=site['kind']
            assert cursor==len(code) and span_count==mapping['spans']
            sampled=Counter();window_samples=Counter();generated=ambiguous=window_ambiguous=other=0
            for root in parse_tree((folder/'sample.txt').read_text()):
                for n,frame,_ in self_samples(root):
                    if '<unknown binary>' not in frame: continue
                    assert '...' not in frame
                    offsets=[int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
                    assert offsets and all(0<=x<len(code) and x%4==0 for x in offsets)
                    category,kind=classify(offsets,candidate_pcs)
                    if category=='certain':sampled[kind]+=n
                    elif category=='ambiguous':ambiguous+=n
                    else:other+=n
                    category,kind=classify(offsets,window_pcs)
                    if category=='certain':window_samples[kind]+=n
                    elif category=='ambiguous':window_ambiguous+=n
                    generated+=n
            assert generated==case['attributed_generated_samples']==sum(sampled.values())+ambiguous+other
            report=dict(case=label,original_bytes=len(code),functions=len(functions),transitions=dict(transitions),
                sites=len(sites),by_kind=dict(Counter(s['kind'] for s in sites)),
                prospective_static_words_saved=len(sites),candidate_memory_self_samples=dict(sampled),
                complete_window_self_samples=dict(window_samples),ambiguous_memory_samples=ambiguous,
                ambiguous_window_samples=window_ambiguous,other_generated_samples=other,
                generated_samples=generated,unassigned_generated_samples=0,
                candidate_memory_sample_fraction=sum(sampled.values())/generated)
            results.append(report);details.append(dict(case=label,sites=sites))
            print(json.dumps(report),flush=True)
        assert all(sha(ROOT/path)==digest for path,digest in frozen.items())
        write(raw/'details.json',details)
        destination=ROOT/'results'/RUN
        destination.mkdir(exist_ok=False)
        write(destination/'summary.json',dict(status='passed',source_revision=revision,
            raw=str(raw.relative_to(ROOT)),plan_sha256=sha(raw/'plan.json'),record_sha256=sha(raw/'record.json'),
            details_sha256=sha(raw/'details.json'),controls=6,cases=results,guest_commands=0,builds=0,
            executable_code_publications=0,production_runtime_changes=0,performance_measurement=False,
            limitation='Source-pinned private-frame patterns only. Samples on both memory instructions are opportunity context, not removable time. Reordering, native semantics, actual encoding and latency remain unqualified.'))


if __name__ == '__main__': main()
