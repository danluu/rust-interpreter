#!/usr/bin/env python3
"""Draft C13 synthetic fixture preparation; no project APIs or timing.
Final plan/descriptor/driver hashes and a successful21-test receipt are required.
"""
import ast
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time

PACKET=Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-mir-lazy-selection-probe')
OUT=PACKET/'fixture-preparation-01'
LOCK=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
BINDINGS=PACKET/'fixture-prep-bindings.json'
BINDINGS_SHA='383bc6585f95cdbe8dc3adaf13af1f09c8315a7c9dab42c504ecf4277f0c881f'
PROCEDURE=PACKET/'fixture-preparation-plan.json'
PROCEDURE_SHA='a25afbd41cc39574e1995949cfb218ca46d1dbe724466b5ee147341f58679949'
PLAN=PACKET/'decision-plan.json'
PLAN_SHA='c432cb2dc3cb182e038a936c898e7d6a76c1270d6425629a4239ef1136838826'
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
DRIVER=PACKET/'fixture-prep.py'
DRIVER_SHA='27439f3feacb9dabb0baccfd9dfd5b19c4017e2660e106fbba00655367e31ac0'
DRIVER_TEMPLATE_SHA='9729513d49a08a0165e65d58f743ee8109d7656f4fbc8dd89036e9d98707a90e'
CACHE=OUT/'qualification-pycache'
GIB,MIB,FLOOR=1024**3,1024**2,16*1024**3
CHILDREN=[]

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def free_bytes():
    info = os.statvfs(PACKET)
    return info.f_bavail * info.f_frsize

def stamp(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink]

def proof(path, cap=16 * MIB):
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "unsafe/oversized input: " + str(path))
    data = path.read_bytes()
    require(stamp(before) == stamp(path.lstat()) and len(data) == before.st_size,
            "input changed while reading: " + str(path))
    return dict(path=str(path), resolved=str(path.resolve()), bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(), stamp=stamp(before))

def write(name, data):
    with (OUT / name).open("x", encoding="utf-8") as output:
        json.dump(data, output, sort_keys=True, indent=2)
        output.write("\n")

def verify_expected(path, expected):
    actual = proof(path)
    require({k: actual[k] for k in ("bytes", "sha256")} == expected, "binding changed: " + str(path))
    return actual

def child(label, command, environment, gate=None):
    """Blocking wait4 avoids polling quantization; a thread only observes disk."""
    require(free_bytes() > FLOOR, "16 GiB disk floor")
    if gate is not None:
        require(time.monotonic() - gate["monotonic"] < 20, "memory gate expired")
    record = dict(label=label, command=list(map(str, command)), cwd=str(PACKET),
        environment=environment, parent_pid=os.getpid(), admission=gate, started_epoch=None, pid=None, free_bytes_before=free_bytes())
    write(label + "-planned.json", record)
    done, observations, observer_errors = threading.Event(), [], []
    def observe():
        try:
            with (OUT / (label + "-disk.jsonl")).open("x") as output:
                while not done.wait(5):
                    value = dict(epoch=time.time(), free_bytes=free_bytes(), action="read_only_no_signals")
                    observations.append(value)
                    output.write(json.dumps(value, sort_keys=True) + "\n")
                    output.flush()
        except BaseException as error:
            observer_errors.append(repr(error))
    watcher = threading.Thread(target=observe, name="owned-disk-observer", daemon=True)
    process = usage = wait_status = None
    error, started, ended = None, None, None
    with (OUT / (label + ".stdout")).open("xb") as stdout, \
         (OUT / (label + ".stderr")).open("xb") as stderr:
        watcher.start()
        try:
            require(free_bytes() > FLOOR, "disk fell before launch")
            record["started_epoch"], started = time.time(), time.perf_counter()
            process = subprocess.Popen(record["command"], cwd=PACKET, env=environment,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, close_fds=True)
            record.update(pid=process.pid, popen_completed_epoch=time.time())
            write(label + "-start.json", record)
            while wait_status is None:
                try:
                    pid, wait_status, usage = os.wait4(process.pid, 0)
                    ended = time.perf_counter()
                    require(pid == process.pid, "unexpected waited child")
                except InterruptedError:
                    continue
        except BaseException as caught:
            error = repr(caught)
        finally:
            if process is not None:
                while wait_status is None:
                    try:
                        pid, wait_status, usage = os.wait4(process.pid, 0)
                        ended = time.perf_counter()
                        require(pid == process.pid, "unexpected waited child")
                    except InterruptedError:
                        continue
                    except ChildProcessError as caught:
                        error = error or repr(caught)
                        process.wait()
                        break
                if wait_status is not None:
                    process.returncode = os.waitstatus_to_exitcode(wait_status)
                record.update(returncode=process.returncode, finished_epoch=time.time(),
                    wall_seconds=(ended or time.perf_counter()) - started)
            done.set()
            watcher.join()
    record.update(error=error, observer_errors=observer_errors, disk_observations=observations,
                  free_bytes_after=free_bytes())
    if usage is not None:
        record.update(cpu_seconds=usage.ru_utime + usage.ru_stime, user_seconds=usage.ru_utime,
                      system_seconds=usage.ru_stime, peak_rss_bytes=usage.ru_maxrss)
    CHILDREN.append(record)
    write(label + "-terminal.json", record)
    record["logs"] = {name: proof(OUT / (label + "." + name), 16 * MIB) for name in ("stdout", "stderr")}
    require(process is not None and usage is not None and error is None and not observer_errors
            and process.returncode == 0, "failed child/incomplete settlement: " + label)
    require(record["free_bytes_after"] > FLOOR and all(o["free_bytes"] > FLOOR for o in observations),
            "disk floor crossed; stop before another sample")
    return record

def admission(label, environment):
    receipt = child(label + "-memory", ["/usr/bin/memory_pressure", "-Q"], environment)
    output, error = ((OUT / (label + "-memory." + name)).read_bytes() for name in ("stdout", "stderr"))
    values = re.findall(rb"System-wide memory free percentage:\s*(\d+)%", output)
    require(len(values) == 1 and not error and int(values[0]) >= 30, "30% memory floor")
    return dict(epoch=time.time(), monotonic=time.monotonic(), free_bytes=free_bytes(),
                memory_free_percent=int(values[0]), memory_receipt=receipt["label"])

def verify_inputs(descriptor):
    recorded={name:verify_expected(Path(name),expected)
              for name,expected in descriptor['fixed_files'].items()}
    for arm,root in descriptor['roots'].items():
        root=Path(root)
        require(root.resolve(strict=True)==root,'source root indirect')
        expected=descriptor['sources'][arm]
        names={str(path.relative_to(root)) for folder in ('scripts','tests')
               for path in (root/folder).glob('*.py')}
        require(names==set(expected),'project source inventory changed')
        require(len(expected)==(190 if arm=='candidate' else 189),'wrong source count')
        for name,row in expected.items():
            path=root/name
            require(path.resolve(strict=True)==path,'source file indirect')
            recorded[str(path)]=verify_expected(path,row)
    for name,expected in descriptor['runtime_files'].items():
        path=Path(name)
        require(path.resolve(strict=True)==path,'runtime file indirect')
        actual=proof(path)
        observed=actual['stamp']
        identity=[*observed[:4],str(observed[4]),str(observed[5])]
        require(identity==expected['identity'] and
                all(actual[k]==expected[k] for k in ('bytes','sha256')),
                'runtime identity/content changed')
        recorded[name]=actual
    for row in descriptor['runtime_links']:
        path=Path(row['path']);info=path.lstat()
        identity=[info.st_dev,info.st_ino,info.st_mode,info.st_size,
                  str(info.st_mtime_ns),str(info.st_ctime_ns)]
        require(stat.S_ISLNK(info.st_mode) and identity==row['identity'] and
                os.readlink(path)==row['text'] and str(path.resolve())==row['resolved'],
                'runtime link changed')
    for row in descriptor['runtime_directories']:
        path=Path(row['path']);info=path.lstat()
        identity=[info.st_dev,info.st_ino,info.st_mode,info.st_size,
                  str(info.st_mtime_ns),str(info.st_ctime_ns)]
        require(path.resolve()==path and stat.S_ISDIR(info.st_mode) and
                identity==row['identity'],'runtime directory changed')
    for path,digest in ((BINDINGS,BINDINGS_SHA),(PROCEDURE,PROCEDURE_SHA),(DRIVER,DRIVER_SHA)):
        item=proof(path)
        require(item['sha256']==digest,'final execution binding changed')
        recorded[str(path)]=item
    raw=DRIVER.read_bytes()
    old=("INPUTS_SHA='"+BINDINGS_SHA+"'").encode()
    require(raw.count(old)==1 and hashlib.sha256(
        raw.replace(old,b"INPUTS_SHA='UNBOUND'")).hexdigest()==DRIVER_TEMPLATE_SHA,
        'preparer changed beyond its input-binding literal')
    recorded[str(Path(__file__).resolve())]=proof(Path(__file__).resolve())
    unit=descriptor['unit_prerequisite']
    item=proof(Path(unit['path']))
    require(item['sha256']==unit['sha256'],'successful unit receipt changed')
    recorded[unit['path']]=item
    return recorded


def verify_units(descriptor):
    entry=descriptor['unit_prerequisite']
    require(re.fullmatch(r'[0-9a-f]{64}',entry['sha256']) is not None,
            'successful21-unit prerequisite remains UNBOUND')
    path=Path(entry['path'])
    require(path==PACKET/'unit-screen-01/result.json' and proof(path)['sha256']==entry['sha256'],
            'incorrect unit receipt')
    result=json.loads(path.read_bytes())
    manifest=json.loads((PACKET/'unit-source-manifest.json').read_bytes())
    require(result['status']=='passed' and result['error'] is None
            and result['post_binding_error'] is None
            and result['expected_tests']==result['passed_tests']==21
            and len(result['tests'])==1 and len(result['children'])==2
            and result['bindings']==result['bindings_after'],'complete21-unit receipt required')
    require([row['label'] for row in result['children']]==
            ['candidate-selection-memory','candidate-selection'] and
            all(row['returncode']==0 and row['error'] is None
                and isinstance(row['pid'],int) and 'cpu_seconds' in row
                for row in result['children']),'unsettled unit children')
    require(manifest['expected_tests']==21 and set(manifest['arms'])=={'candidate'}
            and len(manifest['tests'])==3,'wrong unit manifest')
    ids=sorted(name for row in manifest['tests'] for name in row['expected_ids'])
    require(len(ids)==len(set(ids))==21 and ids==descriptor['expected_unit_ids'],
            'wrong exact unit inventory')
    test=result['tests'][0];report=test['report']
    require(test['label']=='candidate-selection' and test['arm']=='candidate'
            and test['passed']==21 and test['failures']==test['ignored']==0
            and report['status']=='passed' and report['tests_run']==21
            and report['discovered_ids']==report['successful_ids']==ids
            and report['canonical_module_object_preserved'] is True
            and report['cache_empty'] is True
            and report['python']['version_info'][:3]==[3,14,7]
            and report['python']['implementation']=='cpython'
            and Path(report['python']['executable']).resolve()==PYTHON,
            'exact unit names/runtime/canonical module mismatch')
    require(not any(report[k] for k in ('failures','errors','failure_details','error_details',
                'skipped','expected_failures','unexpected_successes','actual_process_attempts')),
            'unsuccessful unit outcome')
    source=manifest['arms']['candidate']
    require(source['root']==descriptor['roots']['candidate']
            and source['sources']==descriptor['sources']['candidate']
            and manifest['baseline_source_provenance']['sources']==descriptor['sources']['baseline'],
            'unit source inventories differ')
    for arm,root in descriptor['roots'].items():
        for name,expected in descriptor['sources'][arm].items():
            observed=result['bindings'][str(Path(root)/name)]
            require(all(observed[k]==expected[k] for k in ('bytes','sha256')),
                    'unit receipt source mismatch')
    require(report['manifest_sha256']==proof(PACKET/'unit-source-manifest.json')['sha256'],
            'unit report manifest mismatch')
    return dict(path=str(path),sha256=entry['sha256'],passed_tests=21,children=2,
                exact_ids=ids,scope='candidate-only21; baseline sources bound, no baseline tests')


def fixture_support():
    # Import only the hash-bound source-only preparer's pure inventory helpers.
    spec=importlib.util.spec_from_file_location('c13_fixture_support',DRIVER)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(not any(name in sys.modules for name in
        ('std_mir','std_mir_readmission','toolchain_lookup','custom_compiler','custom_cargo')),
        'controller imported project code')
    return module


def verify_fixtures(report,support,descriptor):
    fixtures=OUT/'fixtures';owner=fixtures/'owner';compiler=fixtures/'compiler'
    require(report['schema_version']==1 and report['fixture_owner']==str(owner)
            and report['compiler_sysroot']==str(compiler)
            and report['fixture_output_root']==str(fixtures)
            and report['toolchain']=='nightly-2026-09-08'
            and report['artifact_count']==26 and report['project_imports_or_calls']==0,
            'fixture descriptor ownership/scope differs')
    current=support.inventory(fixtures)
    require(current==report['fixture_inventory'],'frozen fixture inventory changed')
    require(report['plan']['sha256']==PLAN_SHA and report['bindings']['sha256']==BINDINGS_SHA,
            'fixture decision/input proof differs')
    lock=owner/'.work/std-mir.lock'
    lockrow,lockbytes=support.file_proof(lock)
    require(report['std_lock']==str(lock) and not lockbytes
            and stat.S_IMODE(lockrow['stamp'][2])==0o600,'wrong writable empty std lock')
    corpus=(owner/'benchmarks/corpus.json').read_bytes()
    require(corpus==(Path(descriptor['roots']['baseline'])/'benchmarks/corpus.json').read_bytes()
            and json.loads(corpus)['toolchain']==report['toolchain'],'fixture corpus differs')
    source_lock=compiler/'lib/rustlib/src/rust/library/Cargo.lock'
    lockbytes=source_lock.read_bytes()
    require(lockbytes==b'# Synthetic source identity for std CLI ready-reuse qualification.\n',
            'synthetic source lock differs')
    source=(Path(descriptor['roots']['baseline'])/'scripts/std_mir.py').read_bytes()
    constants={node.targets[0].id:ast.literal_eval(node.value) for node in ast.parse(source).body
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
        and node.targets[0].id in ('FLAGS','POLICY')}
    compiler_text='rustc synthetic-std-cli-fixture\nhost: aarch64-apple-darwin\n'
    require(report['compiler_text']==compiler_text,'synthetic compiler text differs')
    identity=dict(policy=constants['POLICY'],compiler=compiler_text,target='aarch64-apple-darwin',
                  flags=constants['FLAGS'],lock_sha256=hashlib.sha256(lockbytes).hexdigest())
    key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    work=owner/'.work/std-mir'/key;ready=work/'ready.json'
    rp,raw=support.file_proof(ready);result=json.loads(raw)
    require(result['owner']==str(owner) and result['identity']==identity
            and result['source_sha256']==hashlib.sha256(b'explicitly synthetic source').hexdigest()
            and result['setup_seconds']==1.0 and result['build_seconds']==0.5
            and result['fetch_seconds']==0.0 and result['metadata_bytes']==26624,
            'ready identity/result differs')
    shape=json.loads(Path(descriptor['shape_path']).read_bytes())
    require(list(result['artifacts'])==shape['artifact_paths_in_original_order']
            and len(result['artifacts'])==26,'artifact order/count differs')
    expected_files={str(path.relative_to(fixtures)) for path in
                    (lock,owner/'benchmarks/corpus.json',source_lock,ready)}
    for name,item in result['artifacts'].items():
        path=work/name;expected_files.add(str(path.relative_to(fixtures)))
        observed,payload=support.file_proof(path)
        expected_payload=hashlib.sha256(('std-cli-selection-v1\0'+name).encode()).digest()*32
        st=observed['stamp']
        require(payload==expected_payload and observed['bytes']==1024
                and item['sha256']==observed['sha256']
                and item['stamp']==[st[0],st[1],st[3],st[4]]
                and stat.S_IMODE(st[2])==0o444,'synthetic artifact differs')
    require({name for name,row in current['entries'].items() if row['kind']=='file'}==expected_files,
            'unexpected fixture files')
    require(all(stat.S_IMODE(row['stamp'][2])==(0o600 if name==str(lock.relative_to(fixtures)) else 0o444)
                for name,row in current['entries'].items() if row['kind']=='file'),
            'fixture file modes differ')
    expected=dict(sysroot=str(work/'sysroot'),target='aarch64-apple-darwin',key=key,
                  setup_seconds=1.0,build_seconds=0.5,metadata_bytes=26624)
    require(report['expected_report']==expected,'expected CLI report differs')
    return dict(entry_count=current['entry_count'],total_file_bytes=current['total_file_bytes'],
                artifact_count=26,artifact_payload_bytes=26624,project_api_calls=0,
                expected_report=expected)


def main():
    require(sys.argv[1:]==['--prepare-frozen-fixture'],'explicit preparation mode required')
    require(all(re.fullmatch(r'[0-9a-f]{64}',value) for value in
                (BINDINGS_SHA,PROCEDURE_SHA,DRIVER_SHA)),'draft execution bindings UNBOUND')
    require(sys.platform=='darwin' and sys.implementation.name=='cpython'
            and sys.version_info[:3]==(3,14,7) and Path(sys.executable).resolve()==PYTHON
            and sys.flags.isolated and sys.flags.no_site and sys.flags.no_user_site
            and sys.dont_write_bytecode,'pinned Python -I -S -B required')
    require(os.environ.get('HOME')=='/Users/danluu','HOME changed')
    require(proof(BINDINGS)['sha256']==BINDINGS_SHA
            and proof(PROCEDURE)['sha256']==PROCEDURE_SHA
            and proof(PLAN)['sha256']==PLAN_SHA,'bound descriptor/procedure/decision changed')
    descriptor=json.loads(BINDINGS.read_bytes());procedure=json.loads(PROCEDURE.read_bytes())
    plan=json.loads(PLAN.read_bytes())
    require(descriptor['state']==procedure['state']=='frozen'
            and descriptor['base_commit']==plan['base_commit']
            and descriptor['roots']=={'baseline':plan['baseline_root'],'candidate':plan['candidate_root']}
            and procedure['decision_sha256']==PLAN_SHA
            and procedure['qualification_path']==descriptor['unit_prerequisite']['path']
            and procedure['qualification_sha256']==descriptor['unit_prerequisite']['sha256']
            and procedure['work_children']==procedure['memory_children']==1
            and procedure['required_successful_candidate_tests']==21
            and procedure['free_gib_min']==16 and procedure['memory_free_percent_min']==30,
            'wrong preparation scope')
    require(PACKET.resolve(strict=True)==PACKET and not OUT.exists() and not OUT.is_symlink()
            and free_bytes()>FLOOR,'fresh output and16GiB required')
    # Missing qualification fails before lock, output creation or any child.
    prerequisites=verify_units(descriptor)
    before=verify_inputs(descriptor)
    lockfd=os.open(LOCK,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        ls=os.fstat(lockfd)
        require(stat.S_ISREG(ls.st_mode),'shared lock must be regular')
        print(json.dumps(dict(status='waiting for shared benchmark lock',pid=os.getpid())),flush=True)
        fcntl.flock(lockfd,fcntl.LOCK_EX)
        now=LOCK.lstat()
        require(stat.S_ISREG(now.st_mode) and (ls.st_dev,ls.st_ino)==(now.st_dev,now.st_ino),
                'lock replaced')
        require(free_bytes()>FLOOR and not OUT.exists() and not OUT.is_symlink(),
                'output/admission changed')
        require(verify_inputs(descriptor)==before and verify_units(descriptor)==prerequisites,
                'inputs changed while waiting')
        OUT.mkdir(mode=0o700);CACHE.mkdir(mode=0o700)
        temporary=OUT/'prep-tmp';temporary.mkdir(mode=0o700)
        after=fixtures=fixture_proof=inspection=None
        error=post_error=None
        try:
            write('inputs.json',dict(bindings=before,prerequisites=prerequisites,
                procedure=procedure,expected_children=2,expected_project_api_calls=0,
                lock_identity=[ls.st_dev,ls.st_ino],controller_pid=os.getpid(),
                controller_parent_pid=os.getppid(),terminal=None))
            env=dict(HOME='/Users/danluu',PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',
                     PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(temporary))
            gate=admission('prepare',env)
            child('prepare',[PYTHON,'-I','-S','-B','-X','pycache_prefix='+str(CACHE),
                             DRIVER,'--prepare-std-cli-fixture'],env,gate)
            require(len(CHILDREN)==2 and [x['label'] for x in CHILDREN]==['prepare-memory','prepare']
                    and not list(CACHE.iterdir()) and not list(temporary.iterdir()),
                    'child count/private cache/TMP differs')
            raw=(OUT/'prepare.stdout').read_bytes()
            require(len(raw)<=MIB and not (OUT/'prepare.stderr').read_bytes(),
                    'unexpected preparation output')
            report=json.loads(raw)
            require(report['status']=='prepared'
                    and report['descriptor']==str(OUT/'fixture-descriptor.json'),
                    'wrong preparation summary')
            fixture_proof=proof(OUT/'fixture-descriptor.json',MIB)
            fixtures=json.loads((OUT/'fixture-descriptor.json').read_bytes())
            inspection=verify_fixtures(fixtures,fixture_support(),descriptor)
            require(report['entry_count']==inspection['entry_count']
                    and report['total_file_bytes']==inspection['total_file_bytes'],
                    'preparation counts differ')
        except BaseException as caught:
            error=repr(caught)
        finally:
            try:
                after=verify_inputs(descriptor)
                require(after==before,'bound inputs changed during preparation')
                if fixtures is not None:
                    require(proof(OUT/'fixture-descriptor.json',MIB)==fixture_proof,
                            'fixture descriptor changed')
                    verify_fixtures(fixtures,fixture_support(),descriptor)
            except BaseException as caught:
                post_error=repr(caught);error=error or post_error
        result=dict(status='passed' if error is None else 'failed',error=error,
            post_binding_error=post_error,bindings=before,bindings_after=after,
            children=CHILDREN,expected_children=2,prerequisites=prerequisites,
            project_api_calls=0,fixture_inspection=inspection,
            fixtures_path=str(OUT/'fixture-descriptor.json') if fixtures else None,
            fixtures_proof=fixture_proof,
            scope='Synthetic source-only26-artifact fixture preparation; actual main parity remains pending')
        write('result.json',result)
        print(json.dumps(dict(status=result['status'],error=error,result=str(OUT/'result.json'))),flush=True)
        return 0 if error is None else 1
    finally:
        os.close(lockfd)


if __name__=='__main__':raise SystemExit(main())
