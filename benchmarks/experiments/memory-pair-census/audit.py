"""Close pair eligibility and retained controls without repeating guest work."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        out=ROOT/'results/memory-pair-census-02';summary=json.loads((out/'summary.json').read_text())
        assert summary['status']=='passed' and summary['retained_control_commands']==3 and summary['new_control_commands']==0
        raw=ROOT/summary['raw'];plan=json.loads((raw/'plan.json').read_text())
        assert sha(raw/'plan.json')==summary['plan_sha256'] and sha(raw/'records.json')==summary['records_sha256']
        frozen=plan['frozen'];assert all(sha(ROOT/p)==h for p,h in frozen.items())
        prior=ROOT/'.work/memory-pair-census-01';old=json.loads((prior/'plan.json').read_text())
        assert (prior/'records.json').read_bytes()==(raw/'records.json').read_bytes()
        history={}
        for p,h in old['frozen'].items():
            if p=='benchmarks/experiments/memory-pair-census/run.py':
                spec=old['source_revision']+':'+p
                assert hashlib.sha256(subprocess.check_output(['git','show',spec])).hexdigest()==h
                history[spec]=h
            else:assert sha(ROOT/p)==h,p
        evidence={}
        for name,expected in [('memory-pair-census-01',1),('memory-pair-census-02',0)]:
            saved=ROOT/'results'/name/'terminal.json';t=json.loads(saved.read_text())
            outer=ROOT/'.work/experiments'/name
            assert t['status']=='finished' and t['returncode']==expected
            assert t['owner']==t['cwd']==str(ROOT)
            assert saved.read_bytes()==(outer/'status.json').read_bytes()
            assert sha(outer/'plan.json')==t['plan_sha256'] and sha(outer/'command.log')==t['log_sha256']
            for p in [saved,outer/'plan.json',outer/'command.log']:evidence[str(p.relative_to(ROOT))]=sha(p)
        for case in summary['cases']:
            p=raw/(case['case']+'.json');assert sha(p)==summary['reports'][case['case']]
            report=json.loads(p.read_text());assert report['case']==case and len(report['sites'])==case['pairs']
            assert sum(case['static_pairs_by_detail'].values())==case['pairs']==case['potential_emitted_words_removed']
            assert sum(case['weighted_pair_executions'].values())==sum(s['hits'] for s in report['sites'])
            assert sum(s['samples'] for s in report['sites'])==sum(n for k,n in case['samples'].items() if k.startswith('eligible_'))
            assert not case['ambiguous'] and not case['omitted_executed_functions']
            evidence[str(p.relative_to(ROOT))]=sha(p)
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        for p,h in frozen.items():
            if p.startswith('.work/'):continue
            spec=revision+':'+p
            assert hashlib.sha256(subprocess.check_output(['git','show',spec])).hexdigest()==h,p
            history[spec]=h
        write(out/'source-bindings.json',history)
        write(out/'closure.json',dict(status='passed',frozen_inputs=len(frozen),git_bound_files=len(history),
            source_bindings_sha256=sha(out/'source-bindings.json'),frozen=frozen,evidence=evidence,
            auditor_sha256=sha(Path(__file__)),guest_commands=0,new_control_commands=0,
            retained_control_commands=3,performance_measurement=False))
        print('Closed:',len(frozen),'frozen inputs;',len(history),'Git bindings',flush=True)


if __name__=='__main__':main()
