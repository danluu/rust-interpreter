"""Scope exact zero-range tails in four closed native captures."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
from model import OLD, TAIL, ASM, helpers, controls

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RUN = 'short-clear-tail-scope-01'
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write
from summarize_owned_sample import parse_tree,self_samples
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scalar-private-transfers'))
from native_observation import validate,locate
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
read = focus.read


def macho_text(data):
    assert struct.unpack_from('<I',data)[0] == 0xfeedfacf
    assert struct.unpack_from('<I',data,4)[0] == 0x0100000c
    assert struct.unpack_from('<I',data,12)[0] == 1 # MH_OBJECT, not executable
    ncmds = struct.unpack_from('<I',data,16)[0]
    offset,found = 32,[]
    for _ in range(ncmds):
        command,size = struct.unpack_from('<II',data,offset)
        assert size >= 8 and offset+size <= len(data)
        if command == 0x19:
            sections = struct.unpack_from('<I',data,offset+64)[0]
            assert 72+sections*80 <= size
            for index in range(sections):
                section = offset+72+index*80
                if data[section:section+16].rstrip(b'\0') == b'__text':
                    length = struct.unpack_from('<Q',data,section+40)[0]
                    file_offset = struct.unpack_from('<I',data,section+48)[0]
                    assert struct.unpack_from('<I',data,section+60)[0] == 0
                    assert file_offset+length <= len(data)
                    found.append(data[file_offset:file_offset+length])
        offset += size
    text, = found
    return text


def derive(case):
    folder = ROOT/case['folder']
    native = read(folder/'jit-code/map.json')
    operations = read(folder/'jit-code/operations.json')
    profile = read(ROOT/case['profile'])
    code = (folder/'jit-code/code.bin').read_bytes()
    record = read(folder/'record.json')
    checked = validate(operations,native,code,profile,record['identity']['pid'])
    matches = helpers(code)
    parts = {}
    for start in matches:
        rows = [locate(checked,start+i) for i in range(0,len(OLD),4)]
        assert len({(r['function'],r['pc'],r['kind']) for r in rows}) == 1
        assert rows[0]['kind'] == 'transition' and rows[0]['label'] == 'transition:Call'
        for i in range(0,len(OLD),4): parts[start+i] = 'chunks' if i < 24 else 'byte_tail'
    counts,ambiguous,sites = Counter(),[],Counter()
    for root in parse_tree((folder/'sample.txt').read_text()):
        for count,frame,_ in self_samples(root):
            if '<unknown binary>' not in frame: continue
            offsets = [int(a,16)-native['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
            if not offsets or not any(0 <= p < len(code) for p in offsets): continue
            labels = {parts.get(p,'other') for p in offsets}
            if '...' in frame or len(labels) != 1 or any(not 0 <= p < len(code) for p in offsets):
                ambiguous.append(dict(count=count,frame=frame))
                continue
            label, = labels
            counts[label] += count
            if label != 'other':
                identities = {(locate(checked,p)['function'],locate(checked,p)['pc']) for p in offsets}
                if len(identities) == 1:
                    fid,pc = next(iter(identities));sites[fid,pc,label] += count
    report = read(ROOT/case['report'])
    assert sum(counts.values())+sum(x['count'] for x in ambiguous) == report['attributed_generated_samples']
    return dict(name=case['name'],helper_count=len(matches),generated_samples=report['attributed_generated_samples'],
        samples=dict(counts),ambiguous=ambiguous,top_sites=[dict(function=fid,pc=pc,part=part,samples=n,
            name=profile['functions'][fid]['name']) for (fid,pc,part),n in sites.most_common(15)],
        tail_fraction=counts['byte_tail']/report['attributed_generated_samples'])


def main():
    frozen = {}
    def bind(path,expected=None):
        digest = sha(path)
        assert expected is None or digest == expected,path
        frozen[str(path.relative_to(ROOT))] = digest
        return read(path) if path.suffix == '.json' else digest
    for name in ['adopted-es8-diagnostics-01','adopted-current-runtime-sampling-02']:
        folder = ROOT/'results'/name
        closure = bind(folder/'closure.json')
        assert closure['status'] == 'closed' and closure['all_hashes_verified']
        summary = bind(folder/'summary.json',closure['summary_sha256'])
        bind(folder/'terminal.json',closure['terminal_sha256'])
        assert summary['status'] == 'passed'
    cases = []
    for name,profile in [
            ('adopted-es8-sample-0-01','.work/adopted-es8-diagnostics-01/0-profile.json'),
            ('adopted-es8-sample-1-01','.work/adopted-es8-diagnostics-01/1-profile.json'),
            ('adopted-current-sample-block-02','.work/runtime-composition-profile-02/control-0-profile.json'),
            ('adopted-current-sample-exhaustive-02','.work/runtime-composition-profile-02/control-1-profile.json')]:
        report_path = ROOT/'results'/name/'operation-attribution.json'
        report = bind(report_path)
        assert report['status'] == 'passed' and report['reconstructed_same_process_code']
        assert report['vm_sha256'] == '6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf'
        assert report['unassigned_generated_samples'] == 0
        # Historical report source identities remain bound through its source
        # commit; operational evidence and the chosen static profile stay exact.
        for p,h in report['evidence'].items():
            if p.startswith(('.work/','results/')): bind(ROOT/p,h)
        assert profile in report['evidence']
        folder = ROOT/'.work'/name/'0'
        record = bind(folder/'record.json')
        for p,h in record['files'].items(): bind(folder/p,h)
        cases.append(dict(name=name,folder=str(folder.relative_to(ROOT)),profile=profile,
            report=str(report_path.relative_to(ROOT))))
    paths = [*HERE.glob('*.py'),*HERE.glob('*.md'),Path(focus.__file__),
        ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py',
        ROOT/'scripts/summarize_owned_sample.py',ROOT/'scripts/vmmap_ranges.py',
        ROOT/'benchmarks/experiments/scalar-private-transfers/native_observation.py',
        ROOT/'crates/bytecode/src/jit/native_calls.rs',ROOT/'crates/bytecode/src/jit/resumable.rs',
        ROOT/'crates/bytecode/src/jit/scalar_calls.rs']
    for p in paths: bind(p)
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    raw = ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
    write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,cases=cases,
        controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=1,
        original_project_guest_commands=0,performance_measurement=False))
    write(raw/'records.json',[])
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        model = controls()
        write(raw/'controls.json',model)
        (raw/'tail.s').write_text(ASM)
        cmd = ['/usr/bin/clang','-c','-target','arm64-apple-macos11',str(raw/'tail.s'),'-o',str(raw/'tail.o')]
        child,out,err = capture(cmd,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
            receipt_path=raw/'assembler-child.json',receipt=dict(label='assembler'))
        for stream,value in [('stdout',out),('stderr',err)]: (raw/('assembler.'+stream)).write_text(value)
        records = [dict(label='assembler',command=cmd,pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/'assembler.stdout'),stderr_sha256=sha(raw/'assembler.stderr'))]
        write(raw/'records.json',records)
        assert child.returncode == 0,err
        expected = struct.pack('<9I',*TAIL)
        assert macho_text((raw/'tail.o').read_bytes()) == expected
        scopes = []
        for case in cases:
            require_space(ROOT,8)
            scopes.append(derive(case))
            write(raw/'scopes.json',scopes)
            print(case['name'],scopes[-1]['samples'],flush=True)
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        result = ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        outputs = {str(p.relative_to(ROOT)):sha(p) for p in raw.iterdir() if p.is_file()}
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=1,
            controls=model,scopes=scopes,assembler_words_match=True,outputs=outputs,
            original_project_guest_commands=0,performance_measurement=False))


def close():
    raw = ROOT/'.work'/RUN
    terminal = read(ROOT/'.work/experiments'/RUN/'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        summary = read(ROOT/'results'/RUN/'summary.json')
        plan = read(raw/'plan.json')
        assert summary['controls'] == controls()
        assert summary['scopes'] == [derive(case) for case in plan['cases']]
        assert summary['assembler_words_match']
        assert macho_text((raw/'tail.o').read_bytes()) == struct.pack('<9I',*TAIL)
    focus.RUN = RUN;focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']: close()
    else:
        assert len(sys.argv) == 1
        main()
