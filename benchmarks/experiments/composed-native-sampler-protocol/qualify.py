import hashlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
RUN='composed-native-sampler-protocol-01'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();frozen={}
        proof=ROOT/'results/vmmap-label-compatibility-01';c=read(proof/'closure.json')
        assert c['status']=='closed' and c['all_hashes_verified']
        prior=read(proof/'summary.json');assert sha(proof/'summary.json')==c['summary_sha256'] and sha(proof/'terminal.json')==c['terminal_sha256']
        assert prior['status']=='passed' and prior['retained_reports']==14
        oldraw=ROOT/prior['raw'];oldplan=read(oldraw/'plan.json');oldrecords=read(oldraw/'records.json')
        assert sha(oldraw/'plan.json')==prior['plan_sha256'] and sha(oldraw/'records.json')==prior['records_sha256']
        replay=ROOT/'benchmarks/experiments/vmmap-label-compatibility/replay.py'
        assert sha(replay)==oldplan['frozen'][str(replay.relative_to(ROOT))]
        row,=[r for r in oldrecords if r['label']=='retained-maps'];assert row['returncode']==0
        retained=oldraw/'retained-maps.stdout';assert sha(retained)==row['stdout_sha256'];expected=read(retained)
        assert expected['reports']==14 and expected['guest_commands']==0
        for p,h in expected['evidence'].items():assert sha(ROOT/p)==h;frozen[p]=h
        paths=[*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),*list((ROOT/'scripts').glob('*.py')),replay]
        for folder in ['scalar-runtime-sampling','scalar-private-transfers','operation-map']:paths+=list((ROOT/'benchmarks/experiments'/folder).glob('*.py'))
        paths+=[proof/n for n in ['closure.json','summary.json','terminal.json']]+[oldraw/'plan.json',oldraw/'records.json',retained]
        frozen.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        sampler=ROOT/'scripts/sample_owned_vm.py';absent=ROOT/'.work/composed-sampler-no-artifact.rbc';sentinel=ROOT/'.work/must-not-be-created-composed-sampler-controls'
        assert not absent.exists() and not sentinel.exists()
        base=[sys.executable,'-B',str(sampler),'--tool-key','0'*64,'--artifact',str(absent),'--artifact-sha256','0'*64,'--run-id',sentinel.name]
        specs=[dict(label='attribution',command=[sys.executable,'-B','-m','unittest','test_attribution','-v'],cwd=str(ROOT/'benchmarks/experiments/scalar-runtime-sampling'),expected=0),
            dict(label='help',command=[sys.executable,'-B',str(sampler),'--help'],cwd=str(ROOT),expected=0),
            dict(label='requires-resumable',command=base+['--jit-indirect-calls'],cwd=str(ROOT),expected=2),
            dict(label='incompatible-native',command=base+['--jit-indirect-calls','--jit-resumable-calls','--jit-native-calls'],cwd=str(ROOT),expected=2),
            dict(label='retained-maps',command=[sys.executable,'-B',str(replay)],cwd=str(ROOT),expected=0)]
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,commands=specs,
            controller_command=[sys.executable,*sys.orig_argv[1:]],new_guest_commands=0,new_rust_builds=0,minimum_initial_gib=12,minimum_child_gib=8))
        records=[];write(raw/'records.json',records);env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
        for spec in specs:
            require_space(ROOT,8);label=spec['label'];child,out,err=capture(spec['command'],cwd=spec['cwd'],env=env,receipt_path=raw/'active.json',receipt=dict(label=label))
            for stream,value in [('stdout',out),('stderr',err)]:(raw/(label+'.'+stream)).write_text(value)
            records.append(dict(**spec,pid=child.pid,returncode=child.returncode,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr'))));write(raw/'records.json',records)
            assert child.returncode==spec['expected'],(label,(out+err)[-2000:])
            if label=='attribution':assert re.search(r'Ran 11 tests\b',err) and err.rstrip().endswith('OK')
            if label=='help':assert '--jit-indirect-calls' in out
            if label=='requires-resumable':assert '--jit-indirect-calls requires --jit-resumable-calls' in err
            if label=='incompatible-native':assert 'cannot be combined with native tree/stub calls' in err
            if label=='retained-maps':assert json.loads(out)==expected
            assert not absent.exists() and not sentinel.exists()
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),commands=5,
            attribution_tests=11,invalid_cli_rejections=2,retained_maps=14,legacy_option_shape_preserved=True,
            new_guest_commands=0,new_rust_builds=0,performance_measurement=False,
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json')))
        print('11 attribution controls, two early CLI rejections and14 retained maps passed; no guest launched')
if __name__=='__main__':main()
