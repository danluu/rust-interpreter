"""Independent scalar command/receipt/header checks layered over old controls."""
from common import ROOT,CONTROL,CANDIDATE,LAUNCHER,read,require,sha

def check_call(call,artifact,scalar):
    require(type(scalar) is bool,'invalid scalar setting')
    command=call['command'];launch=call['launch']
    require(len(command)>2 and command[1]==str(LAUNCHER),'unqualified workflow launcher')
    require(command.count('--scalar-values')==int(scalar),'scalar command flag differs')
    require(type(launch.get('scalar_values')) is bool and launch['scalar_values']==scalar,'scalar launch receipt differs')
    payload=artifact.read_bytes()
    require(len(payload)>=4 and int.from_bytes(payload[:4],'little')==(6 if scalar else 5),'executed artifact header differs')
    require(sha(artifact)==launch['artifact_sha256'] and len(payload)==launch['artifact_bytes'],'executed artifact binding differs')

def verify(report,phase):
    require(phase in ['aa','e2e'],'unknown scalar verification phase')
    settings=report['tool_builds'];expected=dict(baseline=False,candidate=phase=='e2e')
    keys=dict(baseline=CONTROL,candidate=CONTROL if phase=='aa' else CANDIDATE)
    for mode,scalar in expected.items():
        require(type(settings[mode].get('scalar_values')) is bool and settings[mode]['scalar_values']==scalar,'recorded scalar mode differs')
        require(settings[mode]['tool_key']==keys[mode],'recorded phase tool differs')
    path=str(LAUNCHER.relative_to(ROOT))
    require(report['scripts_sha256'].get(path)==sha(LAUNCHER),'launcher not bound to history')
    rows=read(ROOT/report['raw']/'records.json');count=0
    for row in rows:
        if row['mode']=='native':continue
        require(len(row['calls'])==len(row['artifacts'])==1,'scalar workflow must batch selected tests')
        call=row['calls'][0];artifact=ROOT/row['artifacts'][0]['path'];mode=row['mode']
        require(call['command'].count('--tool-key')==1 and call['command'][call['command'].index('--tool-key')+1]==keys[mode] and call['launch']['tool_key']==keys[mode],'executed phase tool differs')
        check_call(call,artifact,expected[mode]);count+=1
    require(count==42,'scalar primary lacks 42 executed artifacts')
    return dict(scalar_commands_verified=count,artifact_versions=dict(baseline=5,candidate=6 if phase=='e2e' else 5))
