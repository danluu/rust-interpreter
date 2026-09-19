#!/usr/bin/env python3
"""Fixed paired actual std-MIR readmission validation screen; no compiler builds."""
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import statistics
import subprocess
import sys
import threading
import time
PACKET=Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-readmission-stat-probe')
OUT=PACKET/'screen-01'
LOCK=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
BINDINGS=PACKET/'screen-bindings.json'
BINDINGS_SHA='1e93493bc152886005cd077545d663cca2450c959f0b2262c1f4d9007945525f'
PLAN=PACKET/'decision-plan.json'
PLAN_SHA='a10f461883b1b3d68416b23c863d304a3c7f3b65edba2fc35fe8f5beb630c76b'
UNIT=PACKET/'unit-screen-01/result.json'
UNIT_SHA='26d9bb17cd6abf6839c22a7e795af39c868e0c8657ae032b98f0c3206dc29a9a'
COMPAT=PACKET/'compatibility-screen-01/result.json'
COMPAT_SHA='3157f8de282d7af4d43cc218557341273d9a331b7a007158fef341628923a843'
QUALIFICATION=PACKET/'fixture-qualification-01/result.json'
QUALIFICATION_SHA='759b5a85fa7e40e5a8e126dc87c070e93a52ce4e68ccff9b4d8ec0498321ab0a'
FIXTURE_DESCRIPTOR=PACKET/'fixture-qualification-01/fixtures.json'
FIXTURE_DESCRIPTOR_SHA='05e1b708626d285a1186730d3813ac5273c3cbbc89ba1992d07e48c288fcd656'
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
CACHE=OUT/'pycache'
GIB,MIB,FLOOR=1024**3,1024**2,16*1024**3
CASES=('matching_saved_stamps','matching_device_readmission_receipt')
ROWS,CHILDREN=[],[]

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


def cache_snapshot(descriptor, cache_tag, magic):
    require(CACHE.resolve() == CACHE and CACHE.is_dir(), "private cache root changed")
    items, directories, total = {}, 0, 0
    for directory, subdirs, names in os.walk(CACHE, followlinks=False):
        directories += 1
        require(directories <= 256, "cache directory bound")
        require(all(not (Path(directory) / n).is_symlink() for n in subdirs), "cache directory symlink")
        for name in sorted(names):
            path = Path(directory) / name
            item = proof(path, 4 * MIB)
            total += item["bytes"]
            require(len(items) < 512 and total <= 64 * MIB, "cache inventory bound")
            suffix = "." + cache_tag + ".pyc"
            require(name.endswith(suffix), "unexpected private cache file")
            relative = path.relative_to(CACHE)
            source = Path("/") / relative.parent / (name.removesuffix(suffix) + ".py")
            resolved = source.resolve()
            require(resolved.is_relative_to(Path(descriptor["stdlib_root"]).resolve())
                    or any(resolved.is_relative_to(Path(r) / "scripts") for r in descriptor["roots"].values()),
                    "cache source outside frozen roots")
            source_item = proof(source)
            data, source_data = path.read_bytes(), source.read_bytes()
            require(len(data) >= 16 and data[:4].hex() == magic, "pyc magic/header mismatch")
            flags = int.from_bytes(data[4:8], "little")
            require(flags in (0, 1, 3), "unknown pyc flags")
            if flags == 0:
                require(int.from_bytes(data[8:12], "little") == (int(source.stat().st_mtime) & 0xffffffff)
                        and int.from_bytes(data[12:16], "little") == (len(source_data) & 0xffffffff),
                        "stale timestamp pyc")
            else:
                require(data[8:16] == importlib.util.source_hash(source_data), "stale hash pyc")
            require(hashlib.sha256(source_data).hexdigest() == source_item["sha256"]
                    and hashlib.sha256(data).hexdigest() == item["sha256"], "cache/source changed")
            items[str(relative)] = dict(cache=item, source=source_item, header=data[:16].hex(), flags=flags)
    require(items, "empty warmed bytecode cache")
    return dict(files=items, directories=directories, bytes=total)


def require_cached_sources(report, cache):
    paths = {entry["cache"]["path"] for entry in cache["files"].values()}
    for module in report["modules"].values():
        if module["cached"] is not None:
            require(module["cached"] in paths, "module lacks frozen warm bytecode")


def dependency_proofs(reports, descriptor):
    paths = {Path(module["file"]) for report in reports for module in report["modules"].values()}
    require(len(paths) <= 384, "dependency file count bound")
    standard = Path(descriptor["stdlib_root"]).resolve()
    project = {str(Path(descriptor["roots"][arm]) / p) for arm in descriptor["roots"]
               for p in descriptor["sources"][arm]}
    result, total = {}, 0
    for path in sorted(paths):
        require(path.is_absolute() and (str(path) in project or path == PACKET / "timing-driver.py"
                or path.resolve().is_relative_to(standard)), "unexpected dependency: " + str(path))
        item = proof(path)
        total += item["bytes"]
        require(total <= 64 * MIB, "dependency byte bound")
        result[str(path)] = item
    return result

MAX_ENTRIES, MAX_TOTAL, MAX_FILE = 256, MIB, 64*1024

def file_proof(path, cap=MAX_FILE):
    before = path.lstat()
    require(path.resolve(strict=True) == path and stat.S_ISREG(before.st_mode)
            and before.st_size <= cap, 'unsafe input: '+str(path))
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        require(stamp(os.fstat(fd)) == stamp(before), 'opening input changed')
        data = b''
        while len(data) <= before.st_size:
            part = os.read(fd, min(64*1024, before.st_size+1-len(data)))
            if not part:
                break
            data += part
            require(len(data) <= before.st_size, 'input grew')
        require(len(data) == before.st_size and stamp(os.fstat(fd)) == stamp(before)
                and stamp(path.lstat()) == stamp(before), 'input changed')
    finally:
        os.close(fd)
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),stamp=stamp(before)), data

def inventory(root):
    require(root.resolve(strict=True) == root and stat.S_ISDIR(root.lstat().st_mode),
            'unsafe fixture root')
    rows = {}
    pending = [root]
    total = 0
    while pending:
        path = pending.pop()
        s = path.lstat()
        require(path.resolve(strict=True) == path, 'fixture symlink/indirection')
        relative = str(path.relative_to(root))
        if stat.S_ISDIR(s.st_mode):
            rows[relative] = dict(kind='directory',stamp=stamp(s))
            children = []
            for child in path.iterdir():
                children.append(child)
                require(len(children)+len(pending)+len(rows) <= MAX_ENTRIES,
                        'fixture entries exceed bound')
            pending.extend(sorted(children,reverse=True))
        else:
            require(stat.S_ISREG(s.st_mode), 'nonregular fixture entry')
            row, _ = file_proof(path)
            rows[relative] = dict(kind='file',**row)
            total += row['bytes']
            require(total <= MAX_TOTAL, 'fixture byte budget exceeded')
        require(len(rows) <= MAX_ENTRIES, 'fixture entries exceed bound')
    return dict(entries=rows,total_file_bytes=total,entry_count=len(rows))

def verify_inputs(descriptor):
    records={name:verify_expected(Path(name),expected) for name,expected in descriptor['fixed_files'].items()}
    for arm,rootname in descriptor['roots'].items():
        root=Path(rootname)
        require(root.resolve()==root,'noncanonical source root')
        expected=descriptor['sources'][arm]
        actual={str(path.relative_to(root)) for folder in ('scripts','tests') for path in (root/folder).glob('*.py')}
        require(len(actual)==189 and actual==set(expected),'source inventory changed')
        for relative,expected_proof in expected.items():
            require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,'source path escaped')
            records[str(root/relative)]=verify_expected(root/relative,expected_proof)
    for path,digest in ((BINDINGS,BINDINGS_SHA),(PLAN,PLAN_SHA),(UNIT,UNIT_SHA),(COMPAT,COMPAT_SHA),
                        (QUALIFICATION,QUALIFICATION_SHA),(FIXTURE_DESCRIPTOR,FIXTURE_DESCRIPTOR_SHA)):
        require(proof(path)['sha256']==digest,'stage binding changed: '+str(path))
    return records


def verify_units(descriptor):
    manifest=json.loads((PACKET/'unit-source-manifest.json').read_bytes())
    results={}
    for name,path,version,guard in (('primary',UNIT,[3,14],True),('compatibility',COMPAT,[3,9,6],False)):
        result=json.loads(path.read_bytes())
        require(result['status']=='passed' and result['error'] is None and result['post_binding_error'] is None
                and result['expected_tests']==result['passed_tests']==24 and len(result['children'])==4
                and len(result['tests'])==2 and result['bindings']==result['bindings_after']
                and all(c['returncode']==0 and c['error'] is None for c in result['children']),
                'complete successful unit qualification required: '+name)
        for row in result['tests']:
            expected=next(r for r in manifest['tests'] if r['arm']==row['arm'])
            report=row['report']
            require(row['passed']==12 and row['failures']==row['ignored']==0 and report['status']=='passed'
                    and report['discovered_ids']==report['successful_ids']==expected['expected_ids']
                    and not any(report[k] for k in ('failures','errors','skipped','expected_failures','unexpected_successes'))
                    and report['python']['version_info'][:len(version)]==version
                    and report['python']['implementation']=='cpython'
                    and report['single_stat_guard'] is (guard if row['arm']=='candidate' else None),
                    'unit names/runtime/guard differ: '+name)
        for arm,root in descriptor['roots'].items():
            require(manifest['arms'][arm]['root']==root and manifest['arms'][arm]['sources']==descriptor['sources'][arm],
                    'unit source inventory differs')
            for relative,expected in descriptor['sources'][arm].items():
                actual=result['bindings'][str(Path(root)/relative)]
                require({k:actual[k] for k in ('bytes','sha256')}==expected,'unit source binding differs')
        results[name]=result
    return results


def fixture_snapshot(fixtures):
    root=Path(fixtures['root'])
    require(root==PACKET/'fixture-qualification-01/fixtures','wrong owned fixture root')
    got=inventory(root)
    require(got==fixtures['root_inventory'],'frozen fixture tree changed')
    require([row['name'] for row in fixtures['cases']]==list(CASES),'fixture cases differ')
    for row in fixtures['cases']:
        work,ready=Path(row['work']),Path(row['ready'])
        require(work==root/row['name'] and ready.is_relative_to(work)
                and row['artifact_count']==26 and len(row['result']['artifacts'])==26
                and row['synthetic_payload_bytes']==26*1024,'fixture structure differs')
        require(inventory(work)==row['inventory'],'case fixture changed')
        ready_proof,data=file_proof(ready)
        require(ready_proof==row['ready_proof'] and data.decode()==row['ready_text']
                and json.loads(data)==row['result'],'actual ready manifest differs')
        receipt=row['receipt']
        if row['name']=='matching_saved_stamps':
            require(receipt is None,'matching-stamp route unexpectedly has receipt')
        else:
            require(receipt is not None and Path(receipt['path']).is_relative_to(work),'missing receipt')
            receipt_proof,data=file_proof(Path(receipt['path']))
            require(receipt_proof==receipt['proof'] and data.decode()==receipt['text']
                    and json.loads(data)==receipt['parsed'],'actual readmission receipt differs')
    return got


def schedule():
    rows=[]
    for case in CASES:
        rows.extend(dict(phase='parity',warmup=False,pair=0,case=case,arm=arm) for arm in ('baseline','candidate'))
    for case in CASES:
        rows.extend(dict(phase='warmup',warmup=True,pair=i//2,case=case,arm=arm)
                    for i,arm in enumerate(('baseline','candidate','candidate','baseline')))
    for pair in range(20):
        cases=CASES if pair%2==0 else tuple(reversed(CASES))
        arms=('baseline','candidate') if pair%2==0 else ('candidate','baseline')
        for case in cases:
            rows.extend(dict(phase='measured',warmup=False,pair=pair,case=case,arm=arm) for arm in arms)
    require(len(rows)==92 and {phase:sum(r['phase']==phase for r in rows) for phase in ('parity','warmup','measured')}
            ==dict(parity=4,warmup=8,measured=80),'fixed schedule differs')
    return rows


def metrics():
    require([{k:r[k] for k in ('phase','warmup','pair','case','arm')} for r in ROWS]==schedule(),
            'incomplete or changed schedule')
    result={}
    geo=lambda values:math.exp(sum(math.log(v) for v in values)/len(values))
    for case in CASES:
        measured=[r for r in ROWS if r['phase']=='measured' and r['case']==case]
        require(len(measured)==40,'case incomplete')
        result[case]={}
        for field in ('component_cpu_ns','component_wall_ns','cpu_seconds','wall_seconds','peak_rss_bytes'):
            ratios,baseline,candidate=[],[],[]
            for pair in range(20):
                pair_rows={r['arm']:r for r in measured if r['pair']==pair}
                require(set(pair_rows)=={'baseline','candidate'},'missing pair')
                a,b=pair_rows['baseline'][field],pair_rows['candidate'][field]
                require(a>0 and b>0 and math.isfinite(a) and math.isfinite(b),'invalid clock')
                baseline.append(a);candidate.append(b);ratios.append(b/a)
            result[case][field]=dict(paired_ratios=ratios,geometric_mean_ratio=geo(ratios),
                strict_wins=sum(r<1 for r in ratios),median_baseline=statistics.median(baseline),
                median_candidate=statistics.median(candidate),
                median_paired_delta=statistics.median(b-a for a,b in zip(baseline,candidate)),
                median_arm_delta=statistics.median(candidate)-statistics.median(baseline),
                AB_geometric_mean_ratio=geo(ratios[::2]),BA_geometric_mean_ratio=geo(ratios[1::2]))
    return result


def decision_checks(summary,plan):
    checks={}
    require(set(plan['adoption']['by_case'])==set(CASES),'gate cases differ')
    for case in CASES:
        data,limits=summary[case],plan['adoption']['by_case'][case]
        cpu=data['component_cpu_ns']
        checks[case+'.cpu']=cpu['geometric_mean_ratio']<=limits['component_cpu_geometric_ratio_max']
        checks[case+'.wins']=cpu['strict_wins']>=limits['component_cpu_strict_wins_min']
        for order in ('AB','BA'):
            checks[case+'.'+order]=cpu[order+'_geometric_mean_ratio']<limits[order.lower()+'_component_cpu_geometric_ratio_max_exclusive']
        checks[case+'.wall']=data['component_wall_ns']['geometric_mean_ratio']<=limits['component_wall_geometric_ratio_max']
        for field,key in (('cpu_seconds','cpu'),('wall_seconds','wall'),('peak_rss_bytes','wait4_peak_rss')):
            checks[case+'.process_'+key]=data[field]['geometric_mean_ratio']<=limits['process_'+key+'_geometric_ratio_max']
    require(len(checks)==plan['adoption']['numeric_gate_count']==16,'gate count differs')
    return checks


def verify_qualification(descriptor, plan):
    qualification = json.loads(QUALIFICATION.read_bytes())
    fixtures = json.loads(FIXTURE_DESCRIPTOR.read_bytes())
    require(qualification['status'] == 'passed' and qualification['error'] is None
            and qualification['post_binding_error'] is None
            and qualification['bindings'] == qualification['bindings_after']
            and qualification['expected_children'] == len(qualification['children']) == 2
            and qualification['expected_baseline_calls'] == 3,
            'complete successful fixture qualification required')
    require([row['label'] for row in qualification['children']] == ['prepare-memory', 'prepare']
            and all(row['returncode'] == 0 and row['error'] is None
                    and not row['observer_errors'] and isinstance(row['pid'], int)
                    and row['cpu_seconds'] > 0 for row in qualification['children']),
            'fixture children incompletely settled')
    require(qualification['fixtures_path'] == str(FIXTURE_DESCRIPTOR)
            and qualification['fixtures_proof'] == proof(FIXTURE_DESCRIPTOR)
            and fixtures['schema_version'] == 1 and fixtures['status'] == 'passed'
            and fixtures['decision_sha256'] == PLAN_SHA
            and fixtures['fixture_shape_sha256'] == plan['fixture_shape_sha256']
            and fixtures['source_payloads_read_or_copied'] is False,
            'fixture source or scope differs')
    calls = fixtures['actual_baseline_calls']
    require(calls == qualification['actual_baseline_calls']
            and fixtures['expected_baseline_calls'] == len(calls) == 3
            and [(r['case'], r['phase']) for r in calls] == [
                (CASES[0], 'saved-stamps'), (CASES[1], 'create-receipt'), (CASES[1], 'reuse-receipt')]
            and all(r['outcome'] is None and r['error'] is None and not r['stdout'] and not r['stderr']
                    for r in calls), 'actual fixture validation outcomes differ')
    for name, digest in (('primary', UNIT_SHA), ('compatibility', COMPAT_SHA)):
        prerequisite = qualification['prerequisites'][name]
        require(prerequisite['sha256'] == digest and prerequisite['passed_tests'] == 24
                and prerequisite['children'] == 4, 'fixture unit prerequisite differs')
    baseline = Path(descriptor['roots']['baseline']) / 'scripts/std_mir_readmission.py'
    require(fixtures['baseline_source_path'] == str(baseline)
            and file_proof(baseline)[0] == fixtures['baseline_source'], 'fixture baseline changed')
    for arm, root in descriptor['roots'].items():
        for relative, expected in descriptor['sources'][arm].items():
            observed = qualification['bindings'][str(Path(root) / relative)]
            require({key: observed[key] for key in ('bytes', 'sha256')} == expected,
                    'fixture qualification source differs')
    cache = fixtures['qualification_cache']
    require(cache['empty'] is True and Path(cache['path']) == PACKET / 'fixture-qualification-01/qualification-pycache'
            and not list(Path(cache['path']).iterdir()), 'qualification cache changed')
    loaded = fixtures['loaded_inputs']
    require(len(loaded['files']) <= 384 and loaded['total_bytes'] <= 64 * MIB,
            'fixture dependency inventory bound')
    for name, expected in loaded['files'].items():
        observed = proof(Path(name))
        require({key: observed[key] for key in ('bytes', 'sha256', 'stamp')} == expected,
                'fixture dependency changed')
    current = fixture_snapshot(fixtures)
    require(all(not row['stamp'][2] & 0o222 for row in current['entries'].values()),
            'qualified fixture is writable')
    return qualification, fixtures


def verify_report(report, entry, config, descriptor, fixtures, config_path):
    require(report['schema_version'] == 1 and report['status'] == 'PASS' and report['stage'] == 'api'
            and report['api'] == 'validate' and report['api_calls'] == 1 and report['parity'] is True
            and report['fixture_parity'] is True and report['result'] is None
            and report['result_is_none'] is True and report['error'] is None
            and not report['api_stdout'] and not report['api_stderr'] and report['argument_unchanged'] is True,
            'actual public API parity failed')
    require(all(report[key] == entry[key] for key in ('arm', 'phase', 'warmup', 'case'))
            and report['pycache_prefix'] == str(CACHE) and report['dont_write_bytecode'] == (not entry['warmup'])
            and report['single_stat_guard'] is (True if entry['arm'] == 'candidate' else None),
            'actual API arm/cache/runtime route differs')
    for key in ('decision_sha256', 'runtime_manifest_sha256', 'unit_receipt_sha256',
                'compatibility_receipt_sha256', 'fixture_qualification_sha256', 'fixture_descriptor_sha256'):
        require(report[key] == config[key], 'driver stage binding differs: ' + key)
    require(report['config_proof'] == file_proof(config_path)[0], 'driver config differs')
    require(all(type(report[key]) is int and report[key] > 0
                for key in ('component_cpu_ns', 'component_wall_ns')), 'invalid component clock')
    fixture = next(row for row in fixtures['cases'] if row['name'] == entry['case'])
    expected_receipt = None if fixture['receipt'] is None else fixture['receipt']['proof']
    expected_hash = hashlib.sha256(json.dumps(fixtures['root_inventory'], sort_keys=True,
                                             separators=(',', ':')).encode()).hexdigest()
    require(report['fixture_root'] == fixtures['root'] and report['fixture_work'] == fixture['work']
            and report['ready_path'] == fixture['ready'] and report['ready_proof'] == fixture['ready_proof']
            and report['receipt_proof'] == expected_receipt and report['artifact_count'] == 26
            and report['fixture_entry_count'] == fixtures['root_inventory']['entry_count']
            and report['fixture_total_file_bytes'] == fixtures['root_inventory']['total_file_bytes']
            and all(report[key] == expected_hash for key in ('fixture_before_sha256', 'fixture_after_sha256',
                                                           'fixture_expected_sha256')),
            'driver fixture receipt differs')
    source = Path(descriptor['roots'][entry['arm']]) / 'scripts/std_mir_readmission.py'
    require(report['source_module'] == file_proof(source)[0]
            and report['modules']['std_mir_readmission']['file'] == str(source)
            and report['preclock_modules'] == report['modules'], 'actual imported source changed')


def main():
    require(sys.argv[1:] == ["--execute-frozen-readmission-stat-screen"], "explicit execution flag required")
    require(all(v != "UNBOUND" for v in (BINDINGS_SHA, UNIT_SHA, COMPAT_SHA, QUALIFICATION_SHA, FIXTURE_DESCRIPTOR_SHA)), "completed stage hashes remain UNBOUND")
    require(sys.platform == "darwin" and sys.version_info[:2] == (3, 14)
            and Path(sys.executable).resolve() == PYTHON.resolve(), "pinned macOS Python required")
    require(os.environ.get("HOME") == "/Users/danluu", "HOME must remain unchanged")
    require(proof(BINDINGS)["sha256"] == BINDINGS_SHA and proof(PLAN)["sha256"] == PLAN_SHA,
            "unbound/changed descriptor or decision")
    descriptor, plan = json.loads(BINDINGS.read_bytes()), json.loads(PLAN.read_bytes())
    require(descriptor["base_commit"] == plan["base_commit"] and descriptor["roots"] ==
            {"baseline": plan["baseline_root"], "candidate": plan["candidate_root"]}
            and list(CASES) == [r["name"] for r in plan["cases"]], "decision/root/case mismatch")
    require(descriptor["changed_files"] == ["scripts/std_mir_readmission.py", "tests/test_std_mir_readmission.py"],
            "unexpected candidate scope")
    a, b = descriptor["sources"]["baseline"], descriptor["sources"]["candidate"]
    require({name for name in set(a) | set(b) if a.get(name) != b.get(name)} == set(descriptor["changed_files"]),
            "unexpected actual arm difference")
    require(descriptor["fixed_files"][str(PACKET.parent / "std-readmission-stat-proposal/v3/candidate.patch")]["sha256"]
            == plan["proposal_patch_sha256"] and plan["schedule"]["total_api_drivers"] == 92
            and plan["schedule"]["memory_admission_children"] == 92 and plan["schedule"]["measured_pairs_per_case"] == 20,
            "frozen patch/schedule differs")
    before = verify_inputs(descriptor)
    units = verify_units(descriptor)
    qualification, fixtures = verify_qualification(descriptor, plan)
    frozen_fixtures = fixture_snapshot(fixtures)
    require(PACKET.resolve() == PACKET and free_bytes() > FLOOR and not OUT.exists()
            and not OUT.is_symlink(), "fresh output/16 GiB required")
    fd = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW)
    try:
        lock_info = os.fstat(fd)
        require(stat.S_ISREG(lock_info.st_mode), "shared lock is not regular")
        print(json.dumps(dict(status="waiting for shared benchmark lock", controller_pid=os.getpid())), flush=True)
        fcntl.flock(fd, fcntl.LOCK_EX)
        require((lock_info.st_dev, lock_info.st_ino) == (LOCK.lstat().st_dev, LOCK.lstat().st_ino), "shared lock inode changed")
        require(free_bytes() > FLOOR and not OUT.exists() and not OUT.is_symlink(), "output/admission changed")
        OUT.mkdir(mode=0o700)
        reports, sample_inputs, report_proofs, warm_reports = [], [], [], []
        warmed = dependencies = None
        module_sets = {}
        error = post_error = summary = checks = None
        controller_before = proof(Path(__file__).resolve())
        try:
            require(verify_inputs(descriptor) == before and fixture_snapshot(fixtures) == frozen_fixtures,
                    "inputs changed during admission")
            for name, value in (("inputs-before.json", before), ("decision-plan.json", plan),
                                ("screen-bindings.json", descriptor), ("qualification.json", qualification),
                                ("unit-qualification.json", units), ("controller.json", controller_before),
                                ("fixtures-before.json", frozen_fixtures), ("schedule.json", schedule())):
                write(name, value)
            CACHE.mkdir(mode=0o700)
            (OUT / "tmp").mkdir(mode=0o700)
            environment = dict(HOME="/Users/danluu", PATH="/usr/bin:/bin", LANG="C", LC_ALL="C",
                PYTHONNOUSERSITE="1", PYTHONPYCACHEPREFIX=str(CACHE), TMPDIR=str(OUT / "tmp"),
                __CF_USER_TEXT_ENCODING="0x1F5:0x0:0x52")
            for index, entry in enumerate(schedule()):
                phase, warmup, pair, case, arm = (entry[k] for k in ("phase", "warmup", "pair", "case", "arm"))
                label = f"{index:03d}-{phase}-{case}-{pair:02d}-{arm}"
                require(verify_inputs(descriptor) == before, "source/tool/semantic metadata changed")
                require(fixture_snapshot(fixtures) == frozen_fixtures, "fixture changed before sample")
                if phase == "parity":
                    require(not list(CACHE.iterdir()), "parity cache must remain empty")
                if phase == "measured":
                    require(warmed is not None and len(warm_reports) == 8, "warm cache not frozen")
                    require(dependency_proofs(warm_reports, descriptor) == dependencies, "dependencies changed")
                    require(cache_snapshot(descriptor, reports[0]["python"]["cache_tag"], reports[0]["python"]["magic"]) == warmed,
                            "cache changed before sample")
                config = dict(schema_version=1, arm=arm, phase=phase, case=case,
                    source_root=descriptor["roots"][arm], output_root=str(OUT), pycache_prefix=str(CACHE),
                    decision_sha256=PLAN_SHA, runtime_manifest_sha256=BINDINGS_SHA,
                    unit_receipt_sha256=UNIT_SHA, compatibility_receipt_sha256=COMPAT_SHA,
                    fixture_qualification_sha256=QUALIFICATION_SHA,
                    fixture_descriptor_sha256=FIXTURE_DESCRIPTOR_SHA)
                write(label + "-input.json", config)
                sample_inputs.append(proof(OUT / (label + "-input.json")))
                gate = admission(label, environment)
                command = [str(PYTHON), "-I", "-S", "-X", "pycache_prefix=" + str(CACHE)]
                if not warmup:
                    command.append("-B")
                command += [str(PACKET / "timing-driver.py"), str(OUT / (label + "-input.json"))]
                receipt = report = None
                child_error = parse_error = None
                try:
                    receipt = child(label, command, environment, gate)
                except BaseException as caught:
                    child_error = repr(caught)
                    if CHILDREN and CHILDREN[-1]["label"] == label:
                        receipt = CHILDREN[-1]
                # Preserve raw stdout and a row before any exit/parity/report-field assertion.
                stdout_proof = proof(OUT / (label + ".stdout"), 16 * MIB)
                try:
                    report = json.loads((OUT / (label + ".stdout")).read_bytes())
                except BaseException as caught:
                    parse_error = repr(caught)
                write(label + "-report.json", dict(report=report, parse_error=parse_error, stdout=stdout_proof))
                report_proofs.append(proof(OUT / (label + "-report.json")))
                row = dict(receipt or {}, **entry, child_error=child_error, report_parse_error=parse_error,
                    component_cpu_ns=report.get("component_cpu_ns") if isinstance(report, dict) else None,
                    component_wall_ns=report.get("component_wall_ns") if isinstance(report, dict) else None,
                    driver_status=report.get("status") if isinstance(report, dict) else None,
                    driver_report=report, raw_stdout=stdout_proof)
                ROWS.append(row)
                with (OUT / "samples.jsonl").open("a") as output:
                    output.write(json.dumps(row, sort_keys=True) + "\n")
                require(child_error is None and parse_error is None and receipt is not None
                        and not (OUT / (label + ".stderr")).read_bytes(), "child/driver transport failed")
                verify_report(report, entry, config, descriptor, fixtures,
                              OUT / (label + "-input.json"))
                if reports:
                    require(report["python"] == reports[0]["python"], "Python identity differs")
                require(Path(report["python"]["executable"]).resolve() == PYTHON.resolve(), "driver interpreter differs")
                previous_modules = module_sets.setdefault((arm, case), report["modules"])
                require(previous_modules == report["modules"], "per-API module inventory changed")
                reports.append(report)
                require(fixture_snapshot(fixtures) == frozen_fixtures, "API changed fixture")
                if phase == "parity":
                    require(not list(CACHE.iterdir()), "-B parity wrote bytecode")
                if warmup:
                    warm_reports.append(report)
                if index == 11:
                    require(len(warm_reports) == 8, "warmup schedule incomplete")
                    dependencies = dependency_proofs(warm_reports, descriptor)
                    warmed = cache_snapshot(descriptor, report["python"]["cache_tag"], report["python"]["magic"])
                    for value in reports:
                        require_cached_sources(value, warmed)
                    write("dependencies-frozen.json", dependencies)
                    write("bytecode-cache-frozen.json", warmed)
                if phase == "measured":
                    require_cached_sources(report, warmed)
                    require(cache_snapshot(descriptor, report["python"]["cache_tag"], report["python"]["magic"]) == warmed,
                            "measured child changed cache")
            require(len(ROWS) == 92 and len(CHILDREN) == 184 and len({r["label"] for r in CHILDREN}) == 184
                    and all(r["returncode"] == 0 and r["error"] is None for r in CHILDREN), "incomplete child settlement")
            summary = metrics()
            checks = decision_checks(summary, plan)
        except BaseException as caught:
            error = repr(caught)
        finally:
            try:
                after = verify_inputs(descriptor)
                require(after == before, "final source/tool/semantic identity changed")
                require(proof(Path(__file__).resolve()) == controller_before, "controller changed")
                require(fixture_snapshot(fixtures) == frozen_fixtures, "final real fixture changed")
                write("fixtures-after.json", fixture_snapshot(fixtures))
                if warmed is not None:
                    final_cache = cache_snapshot(descriptor, reports[0]["python"]["cache_tag"], reports[0]["python"]["magic"])
                    require(final_cache == warmed, "final cache changed")
                    require(dependency_proofs(warm_reports, descriptor) == dependencies, "final dependencies changed")
                    write("bytecode-cache-after.json", final_cache)
                require(all(proof(Path(p["path"])) == p for p in sample_inputs + report_proofs), "retained sample input/report changed")
                write("inputs-after.json", after)
            except BaseException as caught:
                post_error = repr(caught)
        status = "PASS" if error is None and post_error is None and len(ROWS) == 92 and len(CHILDREN) == 184 else "FAIL"
        result = dict(status=status, error=error, post_binding_error=post_error, rows=ROWS, children=CHILDREN,
            preparation=[], summary=summary, gates=checks,
            fixed_decision_satisfied=status == "PASS" and checks is not None and len(checks) == 16 and all(checks.values()),
            scope=plan["adoption"]["decision_scope"], decision_sha256=PLAN_SHA, bindings_sha256=BINDINGS_SHA,
            qualification_sha256=QUALIFICATION_SHA, fixture_descriptor_sha256=FIXTURE_DESCRIPTOR_SHA,
            unit_qualification_sha256=UNIT_SHA, compatibility_qualification_sha256=COMPAT_SHA)
        write("result.json", result)
        print(json.dumps({k: result[k] for k in ("status", "error", "post_binding_error", "summary", "gates", "fixed_decision_satisfied")}), flush=True)
        return 0 if status == "PASS" else 1
    finally:
        os.close(fd)

if __name__=='__main__':
    raise SystemExit(main())
