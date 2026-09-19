"""Validate two retained captures; no process or guest execution."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from composed_native_observation import validate
def read(p):return json.loads(p.read_text())
def replay():
    plan=read(ROOT/'.work/composed-fre-runtime-sampling-01/plan.json');rows=[];evidence={}
    for case in plan['cases']:
        raw=ROOT/'.work'/case['run_id'];record,=read(raw/'records.json')
        assert record['identity']['status']=='finished' and record['identity']['returncode']==0
        assert record['mapped'] and record['sample_returncode']==0 and record['statistics']['jit_declined_functions']==0
        assert '--jit-indirect-calls' in record['identity']['command'] and '--profile' not in record['identity']['command']
        assert all(sha(raw/'0'/p)==h for p,h in record['files'].items())
        files=[raw/'0/jit-code/operations.json',raw/'0/jit-code/map.json',raw/'0/jit-code/code.bin',ROOT/case['profile']]
        assert sha(files[3])==case['profile_sha256']
        operations,native,code,profile=read(files[0]),read(files[1]),files[2].read_bytes(),read(files[3])
        assert operations['indirect_calls'] is native['indirect_calls'] is True
        assert not operations['profiled'] and not native['profiled']
        checked=validate(operations,native,code,profile,record['identity']['pid'])
        indirect=sum(r['kind']=='resumable_indirect_call' for r in native['ranges']);assert indirect>0
        assert checked['static_words']['transition:CallIndirect']>0
        rows.append(dict(case=case['label'],native_indirect_regions=indirect,code_bytes=len(code),
            mapped_pcs=checked['mapped_pcs'],spans=checked['spans'],all_native_words_covered=True))
        for p in [*files,raw/'records.json',raw/'plan.json',raw/'summary.json']:evidence[str(p.relative_to(ROOT))]=sha(p)
    assert len(rows)==2
    return dict(status='passed',cases=rows,evidence=evidence,new_guest_commands=0)
if __name__=='__main__':print(json.dumps(replay(),sort_keys=True))
