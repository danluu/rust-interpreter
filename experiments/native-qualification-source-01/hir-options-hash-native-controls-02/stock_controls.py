"""Read-only binding of the four actually passed private-source derivation tests."""
import hashlib
import json
from pathlib import Path

A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
CONTROL=A/'experiments/native-stock-source-controls-02'
WORK=A/'.work/native-stock-source-controls-02'
OUTER=A/'.work/experiments/native-stock-source-controls-supervisor-02'
LAUNCHER=A/'.work/native-stock-source-controls-launch-execution-02'
AUDIT=A/'.work/native-stock-source-controls-independent-verification-02.json'
AUDIT_SHA='95b3ed3d656c04631c45b21c8a5a81a8fe875ef4630b3ba1fcea24eee4b54af7'
INPUTS_SHA='a66d90c86fecc2cae1a8955e6ece0b4595f5d54dfd21be38565c7f17c1971ce7'
LAUNCH_SHA='41ee419b3f949dd375c744d6a9111bc0d81b199dc7033c0d86c27303ac08895e'


def require(ok,message):
    if not ok:raise ValueError(message)


def validate(check,files):
    def read(path,expected=None):
        path=Path(check(Path(path)));require(path.stat().st_size<=2*2**20,'bounded stock control proof')
        raw=path.read_bytes();require(expected is None or hashlib.sha256(raw).hexdigest()==expected,'stock control proof digest differs')
        return json.loads(raw)
    audit=read(AUDIT,AUDIT_SHA);freeze=read(CONTROL/'inputs.json',INPUTS_SHA);launch=read(CONTROL/'launch.json',LAUNCH_SHA)
    require(audit['status']=='verified' and audit['controls']==4 and audit['input_files']==21,'actual four-control independent audit required')
    for name,row in freeze['files'].items():
        check(Path(name));current=files[name]
        stamp=[current['identity'][key] for key in ['dev','ino','mode','size','mtime_ns','ctime_ns','nlink']]
        require(stamp==row['stamp'] and current['sha256']==row['sha256'],'tested source/runner bytes changed')
    members=[]
    for root in [WORK,OUTER,LAUNCHER,A/'.work/native-stock-source-controls-verification-execution-02']:
        for path in sorted(root.rglob('*')):
            require(not path.is_symlink() and (path.is_file() or path.is_dir()),'closed stock-control evidence is indirect')
            if path.is_file():check(path);members.append(str(path))
    require(len(members)<=64,'bounded stock-control evidence membership')
    for path in [A/'.work/launch_native_stock_source_controls_02.py',A/'.work/verify_native_stock_source_controls_02.py']:
        check(path)
    terminal=read(WORK/'receipt.json',audit['receipt_sha256']);result=read(WORK/'result.json',audit['result_sha256'])
    child=read(WORK/'command/receipt.json');outer=read(OUTER/'status.json');dispatcher=read(LAUNCHER/'record.json')
    require(terminal['status']=='passed' and terminal['controls_passed']==4 and terminal['inputs_sha256']==INPUTS_SHA
            and terminal['result_sha256']==audit['result_sha256'] and len(terminal['commands'])==1
            and result['status']=='passed' and result['tests_run']==4 and result['expected_names']==freeze['expected_names']
            and all(result[k]==0 for k in ['failures','errors','skipped','expected_failures','unexpected_successes','child_processes','compiler_calls']),
            'actual four pure controls did not pass exactly')
    require(child['status']=='finished' and child['returncode']==0 and child['command']==freeze['command']
            and child['environment']==freeze['environment'] and child['supervisor_pid']==terminal['pid']
            and outer['status']=='finished' and outer['returncode']==0 and outer['child_pid']==terminal['pid']
            and outer['supervisor_pid']==terminal['parent_pid'] and outer['command']==launch['command'][6:]
            and outer['child_started_at']<=terminal['started_at']<=terminal['admitted_at']<=child['started_at']<=child['finished_at']<=terminal['finished_at']<=outer['finished_at'],
            'actual stock-control child/outer association differs')
    require(dispatcher['status']=='finished' and dispatcher['returncode']==0 and dispatcher['command']==launch['command']
            and dispatcher['launch_sha256']==LAUNCH_SHA,'actual stock-control launcher differs')
    for stream in ['stdout','stderr']:
        require(files[str(WORK/'command'/stream)]['sha256']==child[stream+'_sha256'],'actual stock-control raw changed')
    require(not list((WORK/'tmp').iterdir()),'pure fixture remains')
    return dict(source=str(CONTROL),evidence=str(WORK),launch_sha256=LAUNCH_SHA,inputs_sha256=INPUTS_SHA,
        receipt_sha256=audit['receipt_sha256'],result_sha256=audit['result_sha256'],
        audit=dict(path=str(AUDIT),sha256=AUDIT_SHA),controls=4,closed_members=members,
        preserved_unrun_rejection=str(A/'.work/native-stock-source-controls-prelaunch-rejection-01.json'))
