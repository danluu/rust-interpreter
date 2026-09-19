"""Pure development check of saved JSON streams and malformed message fixtures."""
from pathlib import Path
import copy, hashlib, importlib.util, json, os, sys, time

ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
SOURCE=ROOT/'experiments/proc-macro-arena-ruff-screen-04/common.py'
OUT=X/'.work/ruff-screen04-json-development-01.json'
E=ROOT/'results/proc-macro-arena-ruff-screen-03'
assert not OUT.exists()
checked={}
def read(path):
    data=path.read_bytes();row={'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    assert checked.get(str(path),row)==row;checked[str(path)]=row
    return data
before=read(SOURCE)
def restricted(event,args):
    if event.startswith(('subprocess.','socket.')) or event in ['os.system','os.posix_spawn','os.exec','os.fork']:
        raise RuntimeError('no process or network in pure parser development check')
    if event=='open':
        path,mode,flags=args
        if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            assert isinstance(path,(str,bytes)) and Path(os.fsdecode(path))==OUT,'only final development report may be written'
sys.addaudithook(restricted)
spec=importlib.util.spec_from_file_location('screen04_messages_under_test',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
positives=[];negatives=[]
streams=[E/'capture/stock/97243-1789828160854290000',E/'capture/candidate/42380-1789828305523669000',E/'replays/b0-warm-stock']
for directory in streams:
    record=json.loads(read(directory/'record.json'));assert record['status']=='closed' and record['returncode']==0
    raw=read(directory/'stderr').decode();value=module.replay_messages(raw,record['command'],record['cwd'])
    assert value['diagnostics']==[] and value['check_messages']==[{'$message_type':'unused_extern','lint_level':'force-warn','unused_extern_names':[]}]
    assert {x['emit'] for x in value['artifacts']}=={'dep-info','metadata'}
    positives.append({'name':str(directory.relative_to(E)),'parsed':value,'actual_raw_unchanged':True})
argv=record['command'];base=[json.loads(line) for line in raw.splitlines()]
def encode(messages):return ''.join(json.dumps(x)+'\n' for x in messages)
def accepts(name,messages):
    value=module.replay_messages(encode(messages),argv,record['cwd']);assert value['check_messages']==[x for x in messages if x['$message_type']!='artifact']
    positives.append({'name':name,'fixture':messages,'parsed':value})
def rejects(name,messages,arguments=None):
    try:module.replay_messages(encode(messages),argv if arguments is None else arguments,record['cwd'])
    except (RuntimeError,ValueError,TypeError) as error:negatives.append({'name':name,'error':str(error),'fixture':messages})
    else:raise AssertionError('accepted malformed fixture: '+name)
def diag(level='warning',tag=True):
    value={'message':'complete diagnostic retained','code':{'code':'future_lint','explanation':None},'level':level,'spans':[],'children':[],'rendered':'warning: complete diagnostic retained\n'}
    if tag:value['$message_type']='diagnostic'
    return value
messages=copy.deepcopy(base);messages[1]['unused_extern_names']=['ordinary','r#gen'];accepts('nonempty ordered unused names including raw identifier',messages)
messages=copy.deepcopy(base);messages[1]['unused_extern_names']=['r#gen','ordinary'];accepts('unused names ordering preserved',messages)
warning=diag();warning['children']=[diag('note',False),diag('help',False)]
accepts('warning and complete child diagnostics',base+[warning])
future={'$message_type':'future_incompat','future_incompat_report':[{'diagnostic':warning}]}
accepts('nonempty future report with full tagged nested diagnostic',base+[future])
accepts('complete ordered combined selected reports',base+[warning,future])
for level in ['error','failure-note','error: internal compiler error']:
    rejects('top failure '+level,base+[diag(level)])
    nested=diag();nested['children']=[diag(level,False)];rejects('nested failure '+level,base+[nested])
    rejects('future failure '+level,base+[{'$message_type':'future_incompat','future_incompat_report':[{'diagnostic':diag(level)}]}])
for level in ['deny','forbid','warning']:
    messages=copy.deepcopy(base);messages[1]['lint_level']=level;rejects('unexpected unused lint '+level,messages)
for names in [None,'ordinary',[7]]:
    messages=copy.deepcopy(base);messages[1]['unused_extern_names']=names;rejects('invalid unused name list '+repr(names),messages)
messages=copy.deepcopy(base);messages[1]['unexpected']=True;rejects('extra unused field',messages)
rejects('unknown message kind',base+[{'$message_type':'unknown'}])
rejects('unselected section timing',base+[{'$message_type':'section_timing','name':'parse','event':'start','timestamp':1}])
rejects('empty future report',base+[{'$message_type':'future_incompat','future_incompat_report':[]}])
rejects('malformed future entry',base+[{'$message_type':'future_incompat','future_incompat_report':[warning]}])
bad=diag();bad['children']=[diag()];rejects('child diagnostic cannot carry top tag',base+[bad])
bad=diag();bad['code']={'code':'foo'};rejects('incomplete diagnostic code',base+[bad])
messages=copy.deepcopy(base);messages[0]['artifact']='/wrong/output.d';rejects('artifact outside exact output',messages)
messages=copy.deepcopy(base);messages[0]['artifact']=str(Path(messages[0]['artifact']).with_name('other.d'));rejects('wrong same-directory dependency artifact',messages)
messages=copy.deepcopy(base);messages[0]['artifact']=str(Path(messages[0]['artifact']).with_suffix('.o'));rejects('wrong artifact suffix',messages)
messages=copy.deepcopy(base);messages[0]['emit']='link';rejects('unselected artifact kind',messages)
rejects('missing selected artifact',base[1:])
rejects('duplicate selected artifact',base+[base[0]])
rejects('missing sticky force warning',base,[x for x in argv if x!='--force-warn=unused_crate_dependencies'])
assert read(SOURCE)==before
report={'status':'passed-pure-json-development-check','source':checked[str(SOURCE)],'checker':{'path':str(Path(__file__).absolute()),'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'observed_at':time.time(),'positive_count':len(positives),'negative_count':len(negatives),'positive_cases':positives,'negative_cases':negatives,'checked_files':list(checked.values()),'source_before_after_identical':True,'actual_stream_arguments_or_bytes_modified':False,'synthetic_fixtures_explicit':True,'compiler_calls':0,'cargo_calls':0,'processes_spawned':0,'rust_tests_run':False,'screen_qualification':False,'performance_claim':False}
with OUT.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'path':str(OUT),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'positive_count':len(positives),'negative_count':len(negatives)}))
