#!/usr/bin/env python3
"""Inventory only the completed, warning-qualified native01 derived target."""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

OWNER=Path(__file__).resolve().parents[2]
RUN=OWNER/'.work/oxc-native-compatibility-01'
ROOT=RUN/'target'
ROOTS={'native01':ROOT}
OUTER=OWNER/'.work/experiments/oxc-native-compatibility-supervisor-01'
ARCHIVE=OWNER/'results/oxc-native-compatibility-01'
ASSESSMENT=OWNER/'.work/oxc-native-first-target-assessment-01.json'
FIELDS=['dev','ino','mode','nlink','size','mtime_ns','ctime_ns']
TESTS=['config::plugins::tests::'+name for name in ['test_plugin_normalization','test_normalize_plugin_name','test_is_normal_plugin_name']]

def read(path):return json.loads(Path(path).read_bytes())
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def identity(path):
    value=Path(path).lstat();return {name:getattr(value,'st_'+name) for name in FIELDS}
def snapshot(root):
    assert root==ROOT and root.resolve(strict=True)==root and root.is_dir()
    rows={'.':identity(root)};seen=set();allocated=0
    for directory,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            path=Path(directory)/name;row=identity(path)
            assert path.resolve(strict=True)==path and (stat.S_ISREG(row['mode']) or stat.S_ISDIR(row['mode'])),path
            rows[str(path.relative_to(root))]=row
    groups={}
    for name,row in rows.items():
        path=root if name=='.' else root/name;key=(row['dev'],row['ino'])
        if key not in seen:allocated+=path.stat().st_blocks*512;seen.add(key)
        if stat.S_ISREG(row['mode']):groups.setdefault(key,[]).append(name)
    for names in groups.values():assert rows[names[0]]['nlink']==len(names),('outside hardlink',names)
    return rows,allocated

def history():
    terminal=read(RUN/'receipt.json');outer=read(OUTER/'status.json')
    verification=read(OWNER/'.work/oxc-native-compatibility-verification-01.json')
    assert terminal['status']=='passed' and terminal['source_restored'] and terminal['native_compatibility']
    assert terminal['benchmark'] is False and verification['clean_native_performance_qualified'] is False
    assert verification['hashes']['.work/oxc-native-compatibility-01/receipt.json']==sha(RUN/'receipt.json')
    assert outer['status']=='finished' and outer['returncode']==0
    assert terminal['pid']==outer['child_pid']==19687 and terminal['parent_pid']==outer['supervisor_pid']==19684
    assert outer['started_at']<=terminal['started_at']<=terminal['finished_at']<=outer['finished_at']
    assert sha(OUTER/'command.log')==outer['log_sha256']
    assert len(terminal['children'])==56 and len(terminal['states'])==6
    assert [s['state'] for s in terminal['states']]==[0,-1,1,2,3,4]
    previous=terminal['started_at']
    for row in terminal['children']:
        path=Path(row['path']);child=read(path/'receipt.json')
        assert child==row['receipt'] and child['status']=='finished' and child['supervisor_pid']==terminal['pid']
        assert previous<=child['started_at']<=child['finished_at']<=terminal['finished_at'];previous=child['finished_at']
        assert child['returncode']==(101 if row['label']=='state--1' else 0)
        for stream in ['stdout','stderr']:assert sha(path/stream)==child[stream+'_sha256']
        if '--target-dir' in child['command']:
            assert child['command'].count('--target-dir')==1 and child['command'][child['command'].index('--target-dir')+1]==str(ROOT)
            assert child['environment']['CARGO_TARGET_DIR']==str(ROOT)
    for state in terminal['states']:
        assert {tuple(t) for t in state['tests']}=={(name,'FAILED' if state['state']==-1 else 'ok') for name in TESTS}
    final=terminal['states'][-1];assert final['label']=='restored' and final['source_sha256']==terminal['states'][0]['source_sha256']
    assert final['executable']['sha256']=='03149fdf03347e01c52f3b02c67a085372c14d3ae129b325a645913634888cb4'
    selected=Path(final['executable']['path']);assert selected==ROOT/'debug/deps/oxc_linter-d00dcfa711ee7e21'
    actual=read(Path(final['child_path'])/'receipt.json')
    assert actual['command'][actual['command'].index('--')+1:]==['--exact',*TESTS]
    artifact_rows=[json.loads(line) for line in (Path(final['child_path'])/'stdout').read_text().splitlines() if line.startswith('{')]
    assert final['executable']['artifact'] in artifact_rows
    return terminal,outer,verification

def main():
    assert Path.cwd()==OWNER and not ASSESSMENT.exists()
    terminal,outer,verification=history();rows,allocated=snapshot(ROOT)
    assert all(max(row['mtime_ns'],row['ctime_ns'])/1e9<=terminal['finished_at'] for row in rows.values())
    final=Path(terminal['states'][-1]['executable']['path'])
    fingerprint=ROOT/'debug/.fingerprint/oxc_linter-d00dcfa711ee7e21'
    assert {p.name for p in fingerprint.iterdir()}=={'output-test-lib-oxc_linter','dep-test-lib-oxc_linter','test-lib-oxc_linter','test-lib-oxc_linter.json','invoked.timestamp'}
    paths=[final,final.with_suffix('.d'),*sorted(fingerprint.iterdir())]
    artifacts={str(p.relative_to(ROOT)):dict(source=str(p),identity=identity(p),bytes=p.stat().st_size,sha256=sha(p)) for p in paths}
    assert artifacts[str(final.relative_to(ROOT))]['sha256']==terminal['states'][-1]['executable']['sha256']
    assert snapshot(ROOT)[0]==rows
    result=dict(status='assessed-not-deleted',root=str(ROOT),entries=rows,entry_count=len(rows),allocated_bytes=allocated,
        completed_at=terminal['finished_at'],assessed_at=time.time(),final_artifacts=artifacts,
        proofs={str(p):sha(p) for p in [RUN/'receipt.json',OUTER/'status.json',OWNER/'.work/oxc-native-compatibility-verification-01.json',ARCHIVE/'manifest.json',ARCHIVE/'evidence.tar.gz']},
        limitations=['No canonical admission or open-handle check yet.','Native01 semantics passed with source restoration; clean performance remains unqualified because of recorded strip warnings.',
                    'Earlier overwritten native outputs cannot be preserved; every original receipt/hash/raw output remains in the archive.','Seven final files must be archived and fully read back before deletion.'])
    with ASSESSMENT.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(dict(assessment=str(ASSESSMENT),sha256=sha(ASSESSMENT),entries=len(rows),allocated_bytes=allocated,final_artifacts=len(artifacts))))

if __name__=='__main__':main()
