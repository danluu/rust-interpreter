#!/usr/bin/env python3
"""Qualify two owned synthetic fixtures, after both24-test correctness stages."""
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

PACKET=Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe')
OUT=PACKET/'fixture-qualification-01'
LOCK=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
BINDINGS=PACKET/'fixture-prep-bindings.json'
BINDINGS_SHA='f811a73b1ab8c40ea9abf47ae25235218dc41d8c7a319fb40324740deebdb3ed'
PLAN=PACKET/'decision-plan.json'
PLAN_SHA='a10f461883b1b3d68416b23c863d304a3c7f3b65edba2fc35fe8f5beb630c76b'
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
DRIVER=PACKET/'fixture-prep.py'
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
    recorded={name:verify_expected(Path(name),expected) for name,expected in descriptor['fixed_files'].items()}
    for arm,root in descriptor['roots'].items():
        root=Path(root)
        require(root.resolve(strict=True)==root,'source root indirect')
        expected=descriptor['sources'][arm]
        names={str(path.relative_to(root)) for folder in ('scripts','tests') for path in (root/folder).glob('*.py')}
        require(names==set(expected),'project source inventory changed')
        recorded.update({str(root/name):verify_expected(root/name,row) for name,row in expected.items()})
    require(proof(BINDINGS)['sha256']==BINDINGS_SHA,'fixture descriptor changed')
    recorded[str(BINDINGS)]=proof(BINDINGS)
    recorded[str(Path(__file__).resolve())]=proof(Path(__file__).resolve())
    for entry in descriptor['unit_prerequisites'].values():
        item=proof(Path(entry['path']))
        require(item['sha256']==entry['sha256'],'unit qualification changed')
        recorded[entry['path']]=item
    return recorded


def verify_units(descriptor,plan):
    unit_manifest=json.loads((PACKET/'unit-source-manifest.json').read_bytes())
    reports={}
    for label,entry in descriptor['unit_prerequisites'].items():
        path=Path(entry['path'])
        require(entry['sha256']!='UNBOUND','both24-test receipts must bind before preparation')
        require(proof(path)['sha256']==entry['sha256'],'incorrect unit receipt hash')
        result=json.loads(path.read_bytes())
        require(result['status']=='passed' and result['error'] is None and result['post_binding_error'] is None
                and result['expected_tests']==result['passed_tests']==24
                and len(result['tests'])==2 and len(result['children'])==4
                and result['bindings']==result['bindings_after'],'complete24-unit receipt required')
        require(all(row['returncode']==0 and row['error'] is None and isinstance(row['pid'],int)
                    and 'cpu_seconds' in row for row in result['children']),'unsettled unit child')
        for test in result['tests']:
            arm=test['arm']
            expected=next(row for row in unit_manifest['tests'] if row['arm']==arm)
            report=test['report']
            require(test['passed']==12 and test['failures']==test['ignored']==0
                    and report['status']=='passed' and report['tests_run']==12
                    and report['discovered_ids']==report['successful_ids']==expected['expected_ids']
                    and report['canonical_module_object_preserved'] is True
                    and list(report['python']['version_info'][:2])==entry['version']
                    and report['python']['implementation']=='cpython'
                    and report['single_stat_guard']==(entry['candidate_guard'] if arm=='candidate' else None),
                    'exact unit names/runtime/production selection mismatch')
        require({test['arm'] for test in result['tests']}=={'baseline','candidate'},'unit arms differ')
        for arm,root in descriptor['roots'].items():
            for name,expected in descriptor['sources'][arm].items():
                actual=result['bindings'][str(Path(root)/name)]
                require({k:actual[k] for k in ('bytes','sha256')}==expected,'unit source mismatch')
        reports[label]=dict(path=str(path),sha256=entry['sha256'],passed_tests=24,
                            version=entry['version'],children=4)
    require(plan['compatibility_proposal']['required_before_timing'] is True,'compatibility stage omitted')
    return reports


def fixture_support():
    # Load only this bound harness's pure proof functions, never a production module.
    module_spec=importlib.util.spec_from_file_location('c9_fixture_support',DRIVER)
    module=importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    require('std_mir_readmission' not in sys.modules,'controller imported production')
    return module


def verify_fixtures(report,support,plan):
    require(report['status']=='passed' and report['decision_sha256']==PLAN_SHA
            and report['fixture_shape_sha256']==plan['fixture_shape_sha256']
            and report['root']==str(OUT/'fixtures') and report['expected_baseline_calls']==3
            and len(report['actual_baseline_calls'])==3 and report['source_payloads_read_or_copied'] is False,
            'fixture descriptor scope mismatch')
    require(support.inventory(Path(report['root']))==report['root_inventory'],'aggregate fixture state changed')
    shape=json.loads((PACKET/'fixture-shape-draft.json').read_bytes())
    require([case['name'] for case in report['cases']]==[case['name'] for case in plan['cases']],
            'fixture case order changed')
    expected_calls=[('matching_saved_stamps','saved-stamps'),
                    ('matching_device_readmission_receipt','create-receipt'),
                    ('matching_device_readmission_receipt','reuse-receipt')]
    require([(row['case'],row['phase']) for row in report['actual_baseline_calls']]==expected_calls
            and all(row['outcome'] is None and row['error'] is None and not row['stdout'] and not row['stderr']
                    for row in report['actual_baseline_calls']),'baseline calls changed')
    for case in report['cases']:
        work=Path(case['work'])
        ready=Path(case['ready'])
        require(work==OUT/'fixtures'/case['name'] and ready==work/'ready.json'
                and case['artifact_count']==26 and case['synthetic_payload_bytes']==26*1024,
                'fixture ownership/count differs')
        require(support.inventory(work)==case['inventory'],'case inventory differs')
        rp,text=support.file_proof(ready)
        require(rp==case['ready_proof'] and text.decode()==case['ready_text']
                and json.loads(text)==case['result'],'ready bytes/dict/proof differ')
        require(case['result']['owner']==str(work)
                and list(case['result']['artifacts'])==shape['artifact_paths_in_original_order'],
                'artifact order or owner changed')
        for name,item in case['result']['artifacts'].items():
            row=case['inventory']['entries'][name]
            expected_stamp=[row['stamp'][0],row['stamp'][1],row['stamp'][3],row['stamp'][4]]
            if case['name']=='matching_device_readmission_receipt':
                expected_stamp[0]+=1
            require(item['stamp']==expected_stamp and item['sha256']==row['sha256']
                    and row['bytes']==1024 and not row['stamp'][2]&0o222,'artifact source differs')
        receipt_names=[name for name in case['inventory']['entries'] if name.startswith('readmission-')]
        if case['name']=='matching_saved_stamps':
            require(case['receipt'] is None and not receipt_names,'unexpected receipt')
        else:
            receipt=case['receipt']
            path=Path(receipt['path'])
            require(path.parent==work and receipt_names==[path.name],'receipt path differs')
            row,text=support.file_proof(path)
            require(row==receipt['proof'] and text.decode()==receipt['text']
                    and json.loads(text)==receipt['parsed'],'receipt bytes/parsed proof differ')
        require(all(not row['stamp'][2]&0o222 for row in case['inventory']['entries'].values()),
                'fixture is writable')
    loaded=report['loaded_inputs']
    require(len(loaded['files'])<=384,'loaded dependency inventory too large')
    total=0
    for name,row in loaded['files'].items():
        path=Path(name)
        require(path==DRIVER or path==Path(report['baseline_source_path'])
                or path.is_relative_to(PYTHON.parent.parent/'lib/python3.14'),
                'unexpected fixture child dependency')
        actual=proof(path)
        require({k:actual[k] for k in ('bytes','sha256','stamp')}==row,'loaded dependency changed')
        total+=row['bytes']
    require(total==loaded['total_bytes'] and total<=64*MIB,'loaded dependency bytes changed')
    return True


def main():
    require(sys.argv[1:]==['--prepare-frozen-fixtures'],'explicit preparation mode required')
    require(proof(BINDINGS)['sha256']==BINDINGS_SHA,'binding descriptor changed')
    descriptor=json.loads(BINDINGS.read_bytes())
    require(all(row['sha256']!='UNBOUND' for row in descriptor['unit_prerequisites'].values()),
            'both primary and compatibility24-unit receipts remain required and UNBOUND')
    require(sys.platform=='darwin' and sys.version_info[:2]==(3,14)
            and Path(sys.executable).resolve()==PYTHON and sys.flags.isolated and sys.flags.no_site
            and sys.dont_write_bytecode,'pinned Python -I -S -B required')
    require(proof(PLAN)['sha256']==PLAN_SHA,'decision changed')
    plan=json.loads(PLAN.read_bytes())
    require(descriptor['roots']=={'baseline':plan['baseline_root'],'candidate':plan['candidate_root']}
            and plan['preparation']['work_children']==plan['preparation']['memory_children']==1
            and plan['preparation']['actual_baseline_validate_calls']==3,'scope changed')
    verify_units(descriptor,plan)
    require(PACKET.resolve(strict=True)==PACKET and not OUT.exists() and not OUT.is_symlink()
            and free_bytes()>FLOOR,'fresh output and16GiB required')
    lockfd=os.open(LOCK,os.O_RDWR|os.O_NOFOLLOW)
    try:
        ls=os.fstat(lockfd)
        require(stat.S_ISREG(ls.st_mode),'lock must be regular')
        print(json.dumps(dict(status='waiting for shared benchmark lock',pid=os.getpid())),flush=True)
        fcntl.flock(lockfd,fcntl.LOCK_EX)
        require((ls.st_dev,ls.st_ino)==(LOCK.lstat().st_dev,LOCK.lstat().st_ino),'lock replaced')
        require(free_bytes()>FLOOR and not OUT.exists() and not OUT.is_symlink(),'output/admission changed')
        OUT.mkdir(mode=0o700)
        CACHE.mkdir(mode=0o700)
        temporary=OUT/'prep-tmp';temporary.mkdir(mode=0o700)
        before=after=fixtures=preparation=prerequisites=None
        error=post_error=None
        try:
            prerequisites=verify_units(descriptor,plan)
            before=verify_inputs(descriptor)
            write('inputs.json',dict(bindings=before,prerequisites=prerequisites,
                expected_children=2,expected_baseline_calls=3,lock_identity=[ls.st_dev,ls.st_ino],
                controller_pid=os.getpid(),controller_parent_pid=os.getppid()))
            env=dict(HOME='/Users/danluu',PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',
                     PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(temporary),
                     PYTHONPYCACHEPREFIX=str(CACHE))
            gate=admission('prepare',env)
            config=dict(output=str(OUT),fixtures=str(OUT/'fixtures'),cache=str(CACHE),
                baseline=str(Path(descriptor['roots']['baseline'])/'scripts/std_mir_readmission.py'),
                plan_sha256=PLAN_SHA,shape_sha256=plan['fixture_shape_sha256'],
                output_identity=[OUT.stat().st_dev,OUT.stat().st_ino],prerequisites=prerequisites)
            write('prep-config.json',config)
            config_path=OUT/'prep-config.json'
            config_sha=proof(config_path)['sha256']
            child('prepare',[PYTHON,'-I','-S','-B','-X','pycache_prefix='+str(CACHE),DRIVER,
                             config_path,config_sha],env,gate)
            require(len(CHILDREN)==2 and not list(CACHE.iterdir()),'child count/cache differs')
            preparation=json.loads((OUT/'prep-result.json').read_bytes())
            require(preparation['status']=='passed' and preparation['error'] is None
                    and len(preparation['actual_baseline_calls'])==3,'preparation failed')
            require(proof(OUT/'fixtures.json',MIB)['bytes']<=MIB,'fixture descriptor too large')
            fixtures=json.loads((OUT/'fixtures.json').read_bytes())
            support=fixture_support()
            verify_fixtures(fixtures,support,plan)
        except BaseException as caught:
            error=repr(caught)
        finally:
            if before is not None:
                try:
                    after=verify_inputs(descriptor)
                    require(after==before,'bound sources/receipts changed')
                except BaseException as caught:
                    post_error=repr(caught)
                    error=error or post_error
        result=dict(status='passed' if error is None else 'failed',error=error,
            post_binding_error=post_error,bindings=before,bindings_after=after,
            children=CHILDREN,expected_children=2,prerequisites=prerequisites,
            actual_baseline_calls=preparation['actual_baseline_calls'] if preparation else [],
            expected_baseline_calls=3,fixtures_path=str(OUT/'fixtures.json') if fixtures else None,
            fixtures_proof=proof(OUT/'fixtures.json',MIB) if fixtures else None,
            scope='Owned synthetic26-path preparation through actual baseline validate; no performance samples')
        write('result.json',result)
        print(json.dumps(dict(status=result['status'],error=error,result=str(OUT/'result.json'))),flush=True)
        return 0 if error is None else 1
    finally:
        os.close(lockfd)


if __name__=='__main__':
    raise SystemExit(main())
