"""Reuse closed exact typed Call/Return attribution; select structurally pure DAGs."""
from collections import Counter
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import sha
from workflow_io import write_json as write
def read(p):return json.loads(p.read_text())
def main(run):
    assert re.fullmatch(r'scalar-chain-census-\d{2}',run)
    evidence={}
    def bind(p,h=None):
        digest=sha(p)
        if h is not None:assert digest==h,p
        evidence[str(p.relative_to(ROOT))]=digest
    prior=ROOT/'results/current-call-shapes-01';closed=read(prior/'closure.json');old=read(prior/'attribution.json')
    assert closed['status']=='closed' and closed['all_hashes_verified'] and old['status']=='passed'
    bind(prior/'summary.json',closed['summary_sha256']);binding=ROOT/closed['bindings'];bind(binding,closed['bindings_sha256'])
    for p,h in read(binding)['artifacts'].items():bind(ROOT/p,h)
    census_path=ROOT/'.work'/run/'census.json';census=read(census_path);bind(census_path)
    assert census['status']=='passed' and census['memory_work_remaining']>0 and not census['production_policy_changed']
    original=read(ROOT/'.work/current-call-shapes-01/census.json')
    assert census['artifact_sha256']==original['artifact_sha256']
    rows={r['function']:r for r in census['rows']};assert len(rows)==len(original['rows'])
    for r in original['rows']:
        assert r['name']==rows[r['function']]['name'] and r['function_sha256']==rows[r['function']]['function_sha256']
    expected={(r['caller'],r['pc']):r['callee'] for r in original['calls']}
    assert {(r['caller'],r['pc']):r['callee'] for r in census['calls']}==expected
    cases=[]
    for case in old['cases']:
        p=ROOT/case['report'];bind(p,case['report_sha256']);targets=read(p)['targets'];selected=[];declines=Counter()
        assert sum(t['call_samples']+t['return_samples'] for t in targets)==case['transition_samples']
        for t in targets:
            row=rows[t['function']];candidate=row['candidate'];count=t['call_samples']+t['return_samples']
            if candidate and candidate['calls']>0:
                assert not t['captured_scalar_body']
                selected.append(dict(function=t['function'],name=t['name'],candidate=candidate,
                    call_samples=t['call_samples'],return_samples=t['return_samples'],call_parts=t['call_parts'],return_parts=t['return_parts']))
            elif not t['captured_scalar_body']:declines[row['decline'] or 'existing_leaf']+=count
        selected.sort(key=lambda r:-(r['call_samples']+r['return_samples']))
        cases.append(dict(case=case['case'],generated_samples=case['generated_samples'],transition_samples=case['transition_samples'],
            selected_transition_samples=sum(t['call_samples']+t['return_samples'] for t in selected),
            selected_frame_clear_samples=sum(t['call_parts'].get('call_frame_clear',0) for t in selected),
            sampled_chains=len(selected),selected_targets=selected,remaining_transition_declines=dict(declines)))
    out=ROOT/'results'/run;out.mkdir(exist_ok=False)
    write(out/'attribution.json',dict(status='passed',cases=cases,evidence=evidence,
        eligible_leaves=sum(bool(r['candidate']) and r['candidate']['calls']==0 for r in rows.values()),
        eligible_chains=sum(bool(r['candidate']) and r['candidate']['calls']>0 for r in rows.values()),
        declines=dict(Counter(r['decline'] for r in rows.values() if r['decline'])),
        guest_commands=0,performance_measurement=False,
        scope='Exact original typed call targets and complete transition samples. Structural admission only; no parent scalar emission, resource peak proof, runtime guard hits, removed instruction count or latency estimate.'))
if __name__=='__main__':main(sys.argv[1])
