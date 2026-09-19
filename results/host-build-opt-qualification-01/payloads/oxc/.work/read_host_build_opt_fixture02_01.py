from pathlib import Path
import ast
import hashlib
import json
import re
import stat

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
H = ROOT/'experiments/host-build-opt-01'
P = ROOT/'results/host-build-opt-fixture-02'
W = ROOT/'.work/host-build-opt-fixture-02'
E = ROOT/'.work/host-build-opt-fixture-execution-02'
CHECKED = {}


def file(path, limit=2**20):
    path = Path(path)
    s = path.lstat()
    identity = [s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns]
    assert stat.S_ISREG(s.st_mode) and s.st_size <= limit
    payload = path.read_bytes()
    t = path.lstat()
    assert identity == [t.st_dev,t.st_ino,t.st_mode,t.st_nlink,t.st_size,t.st_mtime_ns,t.st_ctime_ns]
    result = dict(path=str(path),sha256=hashlib.sha256(payload).hexdigest(),bytes=len(payload),identity=identity)
    CHECKED[str(path)] = result
    return result


def read(path):
    file(path)
    return json.loads(Path(path).read_text())


def reference(ref):
    actual = file(ref['path'])
    assert all(actual[k] == v for k,v in ref.items())
    return actual


def options(argv, name):
    return [argv[i+1] if x == name else x[len(name)+1:] for i,x in enumerate(argv)
            if x == name or x.startswith(name+'=')]


def cg(argv):
    result = {}
    for i,x in enumerate(argv):
        if x == '-C' or x.startswith('-C'):
            value = argv[i+1] if x == '-C' else x[2:]
            key,sep,value = value.partition('=')
            key = key.replace('_','-')
            if not sep:
                assert key == 'prefer-dynamic'
                value = 'yes'
            assert key not in result
            result[key] = value
    return result


assert file(E/'record.json')['sha256'] == '10b7ec83d1b130586b68a28735b01e9498a2d5acc72bd4c50c636586d31a738d'
parent = read(E/'record.json'); owner = read(P/'record.json'); result = read(P/'result.json')
assert parent['status'] == 'finished' and parent['returncode'] == 0 and not parent['child_may_be_live']
assert parent['qualification_verified'] and parent['child_pid'] == owner['pid'] == 84890
assert parent['parent_pid'] == owner['parent_pid'] == 83400 and owner['status'] == 'passed'
assert owner['compiler_calls_completed'] and not owner['benchmark'] and owner['no_signals']
assert parent['started_at'] <= owner['started_at'] < owner['finished_at'] <= parent['finished_at']
reference(parent['receipt']); reference(parent['source']); reference(parent['handoff'])
reference(owner['result']); reference(owner['source_manifest']); reference(result['source_manifest'])
assert result['status'] == 'passed' and not result['benchmark'] and not result['performance_qualified']
for name in ['stdout','stderr']:
    assert file(E/name)['sha256'] == parent[name+'_sha256'] and not (E/name).read_bytes()
before = read(P/'source-before.json'); after = read(P/'source-after.json')
assert before == after and len(before) == 16
manifest = read(H/'qualification-sources-02.json')
assert set(before) == set(manifest['files'])
for path,row in before.items():
    assert file(path) == row and row['sha256'] == manifest['files'][path]
tools_before = read(P/'tools-before.json'); tools_after = read(P/'tools-after.json')
assert tools_before == tools_after and set(tools_before) == {'cargo','rustc'}
copied = read(P/'fixture-after.json'); assert len(copied) == 11
for path,row in copied.items():
    assert file(path) == row
    source = H/'qualification-fixture'/Path(path).relative_to(W/'fixture')
    assert file(source)['sha256'] == row['sha256']

commands = {}; previous = owner['started_at']
for label in ['cargo-version','rustc-version','host-0','host-3']:
    row = read(P/label/'record.json'); observation = read(P/label/'observation.json')
    assert row['status'] == 'finished' and row['returncode'] == 0 and row['parent_pid'] == owner['pid']
    assert previous <= row['started_at'] < row['finished_at'] <= owner['finished_at']
    assert row['finished_at'] - row['started_at'] <= 30
    previous = row['finished_at']
    assert row['cwd'] == str(W/'fixture') and row['maximum_output_bytes'] == 256*2**20
    assert observation['violations'] == [] and observation['retained_normal_wait']
    assert not observation['hard_wall_limit'] and not observation['atomic_disk_quota']
    assert max(observation['sampled_peak'].values()) <= 256*2**20
    commands[label] = dict(record=file(P/label/'record.json'),observation=file(P/label/'observation.json'),
        stdout=file(P/label/'stdout'),stderr=file(P/label/'stderr'),pid=row['pid'],
        elapsed_seconds=row['finished_at']-row['started_at'])

comparisons = {}; traces = []; profiles = []; binary_refs = []
assert [a['level'] for a in result['arms']] == [0,3]
for arm in result['arms']:
    level = arm['level']; run = read(P/('host-'+str(level))/'record.json')
    env = run['environment']; argv = run['command']
    assert options(argv,'--target-dir') == [str(W/('target-'+str(level)))]
    assert options(argv,'--target') == ['aarch64-apple-darwin'] and options(argv,'--jobs') == ['2']
    assert '--offline' in argv and '--locked' in argv and argv[-3:] == ['--exact','--test-threads=1','profile_contract']
    assert {k:v for k,v in env.items() if k.startswith('CARGO_PROFILE_')} == {
        'CARGO_PROFILE_DEV_BUILD_OVERRIDE_OPT_LEVEL':str(level),'CARGO_PROFILE_TEST_BUILD_OVERRIDE_OPT_LEVEL':str(level)}
    raw_stdout = (P/('host-'+str(level))/'stdout').read_text()
    assert raw_stdout.count('test profile_contract ... ok') == 1
    assert 'test result: ok. 1 passed; 0 failed;' in raw_stdout
    events = [json.loads(line) for line in raw_stdout.splitlines() if line.startswith('{')]
    assert any(e.get('reason') == 'build-finished' and e['success'] for e in events)
    emitted = {name for e in events if e.get('reason') == 'compiler-artifact' for name in e['filenames']}
    paths = sorted((W/('trace-'+str(level))).iterdir()); assert len(paths) == 11
    call_refs = {r['source']['path']:r for r in arm['calls']}; assert len(call_refs) == 7
    raw_roles = []; query_count = 0
    for path in paths:
        raw = read(path); traces.append(file(path)); args = raw['argv'][1:]
        assert raw['parent_pid'] == run['pid'] and run['started_at'] <= raw['entered_at'] <= run['finished_at']
        assert raw['argv'][0] == env['RUSTC'] and raw['cwd'] == run['cwd']
        if str(path) not in call_refs:
            assert not any(a.endswith('.rs') for a in args)
            query_count += 1
            continue
        reported = call_refs[str(path)]; reference(reported['source']); codegen = cg(args)
        assert codegen == reported['codegen']
        assert reported['host'] == (not options(args,'--target'))
        opt = codegen.get('opt-level','0'); assert opt == str(level if reported['host'] else 1)
        debug = codegen.get('debug-assertions','yes' if opt == '0' else 'no')
        assert debug in ['yes','true','on'] and codegen.get('overflow-checks',debug) in ['yes','true','on']
        raw_roles.append((reported['crate'],reported['package'],reported['host'],reported['test']))
        if not reported['host']:
            externs = []
            for value in options(args,'--extern'):
                name,filename = value.split('=',1); p = Path(filename)
                assert p.is_relative_to(W/('target-'+str(level))) and filename in emitted
                # Read only these six argv-declared products, never enumerate target trees.
                row = file(p, limit=2**20); binary_refs.append(row)
                externs.append(dict(crate=name,flavor=p.suffix,file=row))
            comparisons.setdefault(reported['crate'],{})[str(level)] = dict(
                trace=file(path),metadata=codegen['metadata'],opt_level=opt,externs=externs)
    assert query_count == 4
    assert sorted(raw_roles) == sorted([('build_script_build',p,True,False) for p in ['host','shared','target']] + [
        ('profile_shared_fixture','shared',True,False),('profile_shared_fixture','shared',False,False),
        ('profile_host_fixture','host',True,False),('profile_target_fixture','target',False,True)])
    expected = [('profile-host-fixture',False,str(level)),('profile-shared-fixture',False,str(level)),
                ('profile-shared-fixture',True,'1'),('profile-target-fixture',True,'1')]
    assert len(arm['build_scripts']) == 4
    got = []
    for row in arm['build_scripts']:
        reference(row['source']); value = read(row['source']['path']); assert value == row['value']
        assert value['debug'] == 'true' and row['cargo_event'] in events
        got.append((value['package'],row['target'],value['opt_level'])); profiles.append(file(row['source']['path']))
    assert sorted(got) == sorted(expected)

assert len(binary_refs) == 6
for name,arms in comparisons.items():
    assert arms['0']['metadata'] != arms['3']['metadata']
    a={(x['crate'],x['flavor']):x['file']['sha256'] for x in arms['0']['externs']}
    b={(x['crate'],x['flavor']):x['file']['sha256'] for x in arms['3']['externs']}
    assert set(a)==set(b)
    arms['extern_hash_equal']={str(k):a[k]==b[k] for k in a}
    arms['metadata_equal']=False

expected_files = {'record.json','result.json','source-before.json','source-after.json',
                  'tools-before.json','tools-after.json','fixture-after.json'}
expected_files |= {label+'/'+n for label in commands for n in ['record.json','observation.json','stdout','stderr']}
assert {str(p.relative_to(P)) for p in P.rglob('*') if p.is_file()} == expected_files
report = dict(status='passed-independent-saved-readback',owner_pid=84890,normal_parent_pid=83400,
    parent=file(E/'record.json'),owner=file(P/'record.json'),result=file(P/'result.json'),
    source_before_after_exact16=True,current_source16_exact=True,fixture_copy_exact11=True,
    saved_tools_before_after_equal=True,provider_binary_rehash_performed=False,
    commands=commands,trace_files=traces,profile_files=profiles,target_metadata_and_externs=comparisons,
    six_exact_extern_files_hashed_bytes=sum(x['bytes'] for x in binary_refs),binary_tree_scan=False,
    assertion_scope='Native macro, shared host dependency, target build script and selected test exercised enabled cfg/overflow plus profile-derived values; source and raw success tied exactly.',
    bytecode_caveat='Both target -Cmetadata values and all three named target-test extern hashes differ between host0/3 despite unchanged target opt1. No RBCs were produced here; application RBC equivalence remains an actual gate.',
    performance_qualified=False,reexecution=False,checked_files=list(CHECKED.values()))
out = O/'.work/host-build-opt-fixture02-independent-readback-01.json'
out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(path=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                     checked_files=len(CHECKED),binary_bytes=report['six_exact_extern_files_hashed_bytes']),sort_keys=True))
