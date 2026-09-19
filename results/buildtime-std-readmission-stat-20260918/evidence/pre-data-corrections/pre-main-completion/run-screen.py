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
BINDINGS_SHA='UNBOUND'
PLAN=PACKET/'decision-plan.json'
PLAN_SHA='a10f461883b1b3d68416b23c863d304a3c7f3b65edba2fc35fe8f5beb630c76b'
UNIT=PACKET/'unit-screen-01/result.json'
UNIT_SHA='UNBOUND'
COMPAT=PACKET/'compatibility-screen-01/result.json'
COMPAT_SHA='UNBOUND'
QUALIFICATION=PACKET/'fixture-qualification-01/result.json'
QUALIFICATION_SHA='UNBOUND'
FIXTURE_DESCRIPTOR=PACKET/'fixture-qualification-01/fixtures.json'
FIXTURE_DESCRIPTOR_SHA='UNBOUND'
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


def main():
    require(sys.argv[1:]==['--execute-frozen-readmission-stat-screen'],'explicit execution required')
    require(all(x!='UNBOUND' for x in (BINDINGS_SHA,UNIT_SHA,COMPAT_SHA,QUALIFICATION_SHA,FIXTURE_DESCRIPTOR_SHA)),
            'stage inputs remain UNBOUND')
    raise RuntimeError('Timing main and report schema remain source-only UNBOUND')


if __name__=='__main__':
    raise SystemExit(main())
