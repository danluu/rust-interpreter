"""Bind the exact actual-compiler std/no_std probe evidence to this controller."""
import ast,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
from compare_saved_runtime import sha
PROOF='compact-native-switch-guard-protocol-01'
def verified_paths():
    out=ROOT/'results'/PROOF;closure=json.loads((out/'closure.json').read_text());summary=json.loads((out/'summary.json').read_text())
    assert closure['status']=='closed' and closure['all_hashes_verified'] and closure['four_expected_compiler_rejections']
    assert sha(out/'summary.json')==closure['summary_sha256'] and sha(out/'terminal.json')==closure['terminal_sha256']
    assert summary['status']=='passed' and summary['tests']==26
    raw=ROOT/summary['raw'];plan=json.loads((raw/'plan.json').read_text());assert sha(raw/'plan.json')==summary['plan_sha256']
    records=json.loads((raw/'records.json').read_text());assert sha(raw/'records.json')==summary['records_sha256']
    source=Path(__file__).with_name('benchmark.py')
    loops=[node for node in ast.walk(ast.parse(source.read_text())) if isinstance(node,ast.For) and isinstance(node.target,ast.Tuple)
        and [getattr(n,'id',None) for n in node.target.elts]==['label','code','diagnostic']]
    assert len(loops)==1
    probes=ast.literal_eval(loops[0].iter);assert [p[0] for p in probes]==['type','borrow']
    paths=[out/name for name in ['closure.json','summary.json','terminal.json']]+[raw/'plan.json',raw/'records.json',raw/'compiler.json']
    for prefix in ['std','no_std']:
        for label,code,diagnostic in probes:
            name=prefix+'-'+label;p=raw/(name+'.rs')
            assert sha(p)==plan['frozen'][str(p.relative_to(ROOT))]
            assert p.read_bytes()==(b'#![no_std]\n' if prefix=='no_std' else b'')+code
            row,=[r for r in records if r['label']==name];assert row['expected_diagnostic']==diagnostic and row['returncode']==1
            for stream in ['stdout','stderr']:
                q=raw/(name+'.'+stream);assert sha(q)==row[stream+'_sha256'];paths.append(q)
            paths.append(p)
    return paths
