#!/usr/bin/env python3
"""Unbound fixed stock std CLI prepared-reuse screen; only discovery is stubbed."""
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
PACKET=Path('/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-mir-lazy-selection-probe')
OUT=PACKET/'screen-01'
LOCK=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
BINDINGS=PACKET/'screen-bindings.json'
BINDINGS_SHA='UNBOUND'
PLAN=PACKET/'decision-plan.json'
PLAN_SHA='c432cb2dc3cb182e038a936c898e7d6a76c1270d6425629a4239ef1136838826'
UNIT=PACKET/'unit-screen-01/result.json'
UNIT_SHA='UNBOUND'
QUALIFICATION=PACKET/'fixture-preparation-01/result.json'
QUALIFICATION_SHA='UNBOUND'
FIXTURE_DESCRIPTOR=PACKET/'fixture-preparation-01/fixture-descriptor.json'
FIXTURE_DESCRIPTOR_SHA='UNBOUND'
PYTHON=Path('/opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/Python.framework/Versions/3.14/bin/python3.14')
CACHE=OUT/'pycache'
GIB,MIB,FLOOR=1024**3,1024**2,16*1024**3
CASES=('stock_standalone_ready_reuse',)
ROWS,CHILDREN=[],[]
MAX_ENTRIES, MAX_TOTAL, MAX_FILE = 256, MIB, 64*1024


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
    require(descriptor['state']=='frozen', 'timing input descriptor remains a draft')
    records={name:verify_expected(Path(name),expected) for name,expected in descriptor['fixed_files'].items()}
    for arm,rootname in descriptor['roots'].items():
        root=Path(rootname)
        require(root.resolve()==root,'noncanonical source root')
        expected=descriptor['sources'][arm]
        actual={str(path.relative_to(root)) for folder in ('scripts','tests') for path in (root/folder).glob('*.py')}
        require(len(actual)=={'baseline':189,'candidate':190}[arm] and actual==set(expected),'source inventory changed')
        for relative,expected_proof in expected.items():
            require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,'source path escaped')
            records[str(root/relative)]=verify_expected(root/relative,expected_proof)
    require(len(descriptor['runtime_links'])==8,'runtime link closure differs')
    for row in descriptor['runtime_links']:
        path=Path(row['path'])
        info=path.lstat()
        observed=dict(path=str(path),identity=[info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns,info.st_ctime_ns],
                      text=os.readlink(path),resolved=str(path.resolve()))
        require(stat.S_ISLNK(info.st_mode) and observed==row,'runtime link changed')
        records[str(path)]=observed
    for path,digest in ((BINDINGS,BINDINGS_SHA),(PLAN,PLAN_SHA),(UNIT,UNIT_SHA),
                        (QUALIFICATION,QUALIFICATION_SHA),(FIXTURE_DESCRIPTOR,FIXTURE_DESCRIPTOR_SHA)):
        require(proof(path)['sha256']==digest,'stage binding changed: '+str(path))
    return records


def verify_units(descriptor):
    manifest=json.loads((PACKET/'unit-source-manifest.json').read_bytes())
    result=json.loads(UNIT.read_bytes())
    require(result['status']=='passed' and result['error'] is None and result['post_binding_error'] is None
            and result['expected_tests']==result['passed_tests']==21 and len(result['children'])==2
            and len(result['tests'])==1 and result['bindings']==result['bindings_after']
            and [c['label'] for c in result['children']]==['candidate-selection-memory','candidate-selection']
            and all(c['returncode']==0 and c['error'] is None for c in result['children']),
            'complete successful candidate-only21 qualification required')
    ids=sorted(i for row in manifest['tests'] for i in row['expected_ids'])
    require(len(ids)==21 and [r['expected_tests'] for r in manifest['tests']]==[8,6,7]
            and manifest['status']=='frozen' and manifest['decision_sha256']==PLAN_SHA,
            'unit suite differs from fixed stage')
    row=result['tests'][0]
    report=row['report']
    require(row['arm']=='candidate' and row['passed']==21 and row['failures']==row['ignored']==0
            and report['status']=='passed' and report['tests_run']==21
            and report['discovered_ids']==report['successful_ids']==ids
            and not any(report[k] for k in ('failures','errors','skipped','expected_failures','unexpected_successes','actual_process_attempts'))
            and report['canonical_module_object_preserved'] is True and report['cache_empty'] is True
            and report['python']['version_info'][:3]==[3,14,7] and report['python']['implementation']=='cpython'
            and Path(report['python']['executable']).resolve()==PYTHON,
            'unit names/runtime/canonical-module outcomes differ')
    require(report['manifest_sha256']==proof(PACKET/'unit-source-manifest.json')['sha256']
            and manifest['arms']['candidate']['root']==descriptor['roots']['candidate']
            and manifest['arms']['candidate']['sources']==descriptor['sources']['candidate']
            and manifest['baseline_source_provenance']['sources']==descriptor['sources']['baseline'],
            'unit actual source inventories differ')
    for arm,root in descriptor['roots'].items():
        for relative,expected in descriptor['sources'][arm].items():
            actual=result['bindings'][str(Path(root)/relative)]
            require({k:actual[k] for k in ('bytes','sha256')}==expected,'unit source binding differs')
    runtime=manifest['runtime']
    require(len(runtime['files'])==1955 and runtime['links']==descriptor['runtime_links'], 'unit runtime closure differs')
    for path,expected in runtime['files'].items():
        require(descriptor['fixed_files'][path]=={k:expected[k] for k in ('bytes','sha256')}
                and {k:result['bindings'][path][k] for k in ('bytes','sha256')}==descriptor['fixed_files'][path],
                'timing runtime differs from qualified units')
    for child_row in result['children']:
        for entry in child_row['logs'].values():
            actual=proof(Path(entry['path']))
            require({k:actual[k] for k in ('bytes','sha256')}=={k:entry[k] for k in ('bytes','sha256')},'unit log changed')
    require(not list((PACKET/'unit-screen-01/pycache').iterdir()), 'unit cache changed')
    return result


def fixture_snapshot(fixtures):
    root=Path(fixtures['fixture_output_root'])
    owner=Path(fixtures['fixture_owner'])
    compiler=Path(fixtures['compiler_sysroot'])
    require(root==PACKET/'fixture-preparation-01/fixtures' and owner==root/'owner' and compiler==root/'compiler',
            'wrong owned fixture roots')
    got=inventory(root)
    require(got==fixtures['fixture_inventory'],'frozen fixture tree changed')
    expected=fixtures['expected_report']
    require(fixtures['schema_version']==1 and fixtures['toolchain']=='nightly-2026-09-08'
            and fixtures['artifact_count']==26 and fixtures['project_imports_or_calls']==0
            and expected['metadata_bytes']==26*1024 and expected['target']=='aarch64-apple-darwin',
            'fixture route or shape differs')
    key=expected['key']
    require(re.fullmatch('[0-9a-f]{64}',key) is not None,'invalid fixture key')
    work=owner/'.work/std-mir'/key
    require(expected['sysroot']==str(work/'sysroot'),'fixture sysroot differs')
    ready_proof,ready_raw=file_proof(work/'ready.json')
    ready=json.loads(ready_raw)
    require(ready['owner']==str(owner) and ready['identity']['compiler']==fixtures['compiler_text']
            and len(ready['artifacts'])==26 and ready['metadata_bytes']==26*1024
            and ready['setup_seconds']==expected['setup_seconds']==1.0
            and ready['build_seconds']==expected['build_seconds']==0.5,'ready result differs')
    artifact_bytes=0
    for relative,expected_artifact in ready['artifacts'].items():
        path=work/relative
        require(not Path(relative).is_absolute() and '..' not in Path(relative).parts
                and path.is_relative_to(work/'sysroot'),'artifact escaped owned work')
        actual,_=file_proof(path)
        info=path.lstat()
        require(actual['bytes']==1024 and actual['sha256']==expected_artifact['sha256']
                and [info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns]==expected_artifact['stamp'],
                'ready artifact differs')
        artifact_bytes+=actual['bytes']
    require(artifact_bytes==26*1024,'wrong synthetic artifact bytes')
    std_lock=Path(fixtures['std_lock'])
    require(std_lock==owner/'.work/std-mir.lock','unexpected std lock')
    lock_proof,lock_raw=file_proof(std_lock)
    require(not lock_raw and lock_proof['stamp'][2]&0o200,'std lock must be the precreated writable empty file')
    require(all(not row['stamp'][2]&0o222 for name,row in got['entries'].items()
                if row['kind']=='file' and root/name!=std_lock),'nonlock fixture file became writable')
    return got


def verify_qualification(descriptor, plan):
    qualification=json.loads(QUALIFICATION.read_bytes())
    fixtures=json.loads(FIXTURE_DESCRIPTOR.read_bytes())
    require(qualification['status']=='passed' and qualification['error'] is None
            and qualification['post_binding_error'] is None and qualification['bindings']==qualification['bindings_after']
            and len(qualification['children'])==2 and qualification['project_api_calls']==0
            and qualification['prerequisites']['passed_tests']==21,
            'complete successful fixture preparation required')
    require([r['label'] for r in qualification['children']]==['prepare-memory','prepare']
            and all(r['returncode']==0 and r['error'] is None and not r['observer_errors']
                    and isinstance(r['pid'],int) and r['cpu_seconds']>0 for r in qualification['children']),
            'preparation children incompletely settled')
    require(qualification['fixtures_path']==str(FIXTURE_DESCRIPTOR)
            and qualification['fixtures_proof']==proof(FIXTURE_DESCRIPTOR)
            and fixtures['plan']['sha256']==PLAN_SHA
            and fixtures['bindings']['sha256']==proof(PACKET/'fixture-prep-bindings.json')['sha256'],
            'fixture preparation bindings differ')
    for arm,root in descriptor['roots'].items():
        for relative,expected in descriptor['sources'][arm].items():
            observed=qualification['bindings'][str(Path(root)/relative)]
            require({k:observed[k] for k in ('bytes','sha256')}==expected,'fixture preparation source differs')
    for path,expected in fixtures['source_proofs'].items():
        require(file_proof(Path(path))[0]==expected,'preparation source proof changed')
    require(fixtures['corpus_proof']==file_proof(Path(descriptor['roots']['baseline'])/'benchmarks/corpus.json')[0],
            'fixture corpus source changed')
    current=fixture_snapshot(fixtures)
    inspected=qualification['fixture_inspection']
    require(inspected['entry_count']==current['entry_count']
            and inspected['total_file_bytes']==current['total_file_bytes']
            and inspected['artifact_count']==26 and inspected['artifact_payload_bytes']==26*1024
            and inspected['project_api_calls']==0 and inspected['expected_report']==fixtures['expected_report'],
            'fixture preparation inspection differs')
    for name in ('qualification-pycache','prep-tmp'):
        path=PACKET/'fixture-preparation-01'/name
        require(path.resolve()==path and path.is_dir() and not list(path.iterdir()), 'preparation private directory changed')
    for row in qualification['children']:
        for entry in row['logs'].values():
            require(proof(Path(entry['path']))==entry,'fixture preparation log changed')
    return qualification, fixtures


def verify_report(report, entry, config, descriptor, fixtures, config_path):
    require(report['schema_version']==1 and report['status']=='PASS'
            and report['arm']==entry['arm'] and report['warmup']==entry['warmup']
            and report['main_returnvalue'] is None and not report['process_attempts'], 'actual stock main failed')
    require(report['setup_calls']==[dict(toolchain=fixtures['toolchain'],fetch=False)]
            and report['discovery_calls']==[dict(toolchain=fixtures['toolchain'],cache_directory=None,outcome='fresh')],
            'setup/discovery boundary differs')
    ordered={key:fixtures['expected_report'][key] for key in ('sysroot','target','key','setup_seconds','build_seconds','metadata_bytes')}
    require(report['cli_stdout']==json.dumps(ordered,indent=2)+'\n'
            and json.loads(report['cli_stdout'])==fixtures['expected_report'],'actual CLI stdout differs')
    require(report['pycache_prefix']==str(CACHE) and report['dont_write_bytecode']==(not entry['warmup']),
            'driver cache regime differs')
    require(all(type(report[key]) is int and report[key]>0 for key in ('component_cpu_ns','component_wall_ns')),
            'invalid component clocks')
    require(json.loads(config_path.read_bytes())==config,'retained sample config changed')
    for name in ('std_mir','std_mir_readmission','toolchain_lookup'):
        expected=str(Path(descriptor['roots'][entry['arm']])/'scripts'/(name+'.py'))
        require(report['modules'][name]['file']==expected,'wrong actual project module: '+name)
    require('tempfile' in report['modules'] and 'unittest' not in report['modules'],'ordinary import boundary differs')
    for name in ('custom_compiler','custom_cargo','custom_cargo_libraries','compiler_association'):
        require((name in report['modules'])==(entry['arm']=='baseline'),'optional import selection differs')
        if name in report['modules']:
            require(report['modules'][name]['file']==str(Path(descriptor['roots'][entry['arm']])/'scripts'/(name+'.py')),
                    'optional module came from wrong root')
    forbidden=('std_mir','std_mir_readmission','toolchain_lookup','custom_compiler','custom_cargo',
               'custom_cargo_libraries','compiler_association','tempfile','dataclasses','unittest')
    require(not any(name==blocked or name.startswith(blocked+'.') for name in report['preloaded'] for blocked in forbidden),
            'timed implementation preloaded')
    observed=dependency_proofs([report],descriptor)
    for path,item in observed.items():
        source_root=Path(descriptor['roots'][entry['arm']])
        if Path(path).is_relative_to(source_root):
            expected=descriptor['sources'][entry['arm']][str(Path(path).relative_to(source_root))]
        else:
            require(not any(Path(path).is_relative_to(Path(root)) for root in descriptor['roots'].values()),
                    'driver imported the other arm')
            expected=descriptor['fixed_files'][path]
        require({k:item[k] for k in ('bytes','sha256')}==expected,'driver dependency binding differs')



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
    require(len(rows)==46 and {phase:sum(r['phase']==phase for r in rows) for phase in ('parity','warmup','measured')}
            ==dict(parity=2,warmup=4,measured=40),'fixed schedule differs')
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
    require(set(summary)==set(CASES) and plan['case']==CASES[0], 'gate case differs')
    data,limits=summary[CASES[0]],plan['adoption_gates']
    cpu=data['component_cpu_ns']
    checks={CASES[0]+'.cpu':cpu['geometric_mean_ratio']<=limits['component_cpu_geometric_mean_ratio_max'],
            CASES[0]+'.wins':cpu['strict_wins']>=limits['component_cpu_strict_wins_min']}
    for order in ('AB','BA'):
        checks[CASES[0]+'.'+order]=cpu[order+'_geometric_mean_ratio']<limits['both_order_component_cpu_geometric_mean_ratio_max_exclusive']
    checks[CASES[0]+'.wall']=data['component_wall_ns']['geometric_mean_ratio']<=limits['component_wall_geometric_mean_ratio_max']
    for field,key in (('cpu_seconds','cpu'),('wall_seconds','wall'),('peak_rss_bytes','rss')):
        checks[CASES[0]+'.process_'+key]=data[field]['geometric_mean_ratio']<=limits['process_'+key+'_geometric_mean_ratio_max']
    require(len(checks)==8,'gate count differs')
    return checks



def main():
    require(sys.argv[1:] == ["--execute-frozen-std-cli-screen"], "explicit execution flag required")
    require(all(v != "UNBOUND" for v in (BINDINGS_SHA, UNIT_SHA, QUALIFICATION_SHA, FIXTURE_DESCRIPTOR_SHA)), "completed stage hashes remain UNBOUND")
    require(sys.platform == "darwin" and sys.implementation.name == "cpython" and sys.version_info[:3] == (3, 14, 7)
            and sys.flags.isolated and sys.flags.no_site and sys.flags.no_user_site and sys.dont_write_bytecode
            and Path(sys.executable).resolve() == PYTHON.resolve(), "pinned macOS Python required")
    require(os.environ.get("HOME") == "/Users/danluu", "HOME must remain unchanged")
    require(proof(BINDINGS)["sha256"] == BINDINGS_SHA and proof(PLAN)["sha256"] == PLAN_SHA,
            "unbound/changed descriptor or decision")
    descriptor, plan = json.loads(BINDINGS.read_bytes()), json.loads(PLAN.read_bytes())
    require(descriptor["base_commit"] == plan["base_commit"] and descriptor["roots"] ==
            {"baseline": plan["baseline_root"], "candidate": plan["candidate_root"]}
            and CASES == (plan["case"],), "decision/root/case mismatch")
    require(descriptor["changed_files"] == ["scripts/std_mir.py", "tests/test_std_mir_selection.py"],
            "unexpected candidate scope")
    a, b = descriptor["sources"]["baseline"], descriptor["sources"]["candidate"]
    require({name for name in set(a) | set(b) if a.get(name) != b.get(name)} == set(descriptor["changed_files"]),
            "unexpected actual arm difference")
    require(descriptor["fixed_files"][str(PACKET.parent / "std-mir-lazy-selection-proposal/candidate.patch")]["sha256"]
            == plan["proposal_patch_sha256"] and plan["schedule"]["total_drivers"] == 46
            and plan["schedule"]["memory_children"] == 46 and plan["schedule"]["measured_pairs"] == 20
            and plan["schedule"]["parity_order"] == ["baseline", "candidate"]
            and plan["schedule"]["warmup_order"] == ["baseline", "candidate", "candidate", "baseline"]
            and plan["schedule"]["measured_drivers"] == 40
            and plan["resource"]["free_gib_min"] == 16 and plan["resource"]["memory_free_percent_min"] == 30,
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
                    require(warmed is not None and len(warm_reports) == 4, "warm cache not frozen")
                    require(dependency_proofs(warm_reports, descriptor) == dependencies, "dependencies changed")
                    require(cache_snapshot(descriptor, reports[0]["python"]["cache_tag"], reports[0]["python"]["magic"]) == warmed,
                            "cache changed before sample")
                config = dict(schema_version=1, arm=arm, phase=phase, case=case, label=label, warmup=warmup,
                    source_root=descriptor["roots"][arm], output_root=str(OUT), pycache_prefix=str(CACHE),
                    decision_sha256=PLAN_SHA, runtime_manifest_sha256=BINDINGS_SHA,
                    unit_receipt_sha256=UNIT_SHA, fixture_qualification_sha256=QUALIFICATION_SHA,
                    fixture_descriptor_sha256=FIXTURE_DESCRIPTOR_SHA,
                    **{key: fixtures[key] for key in ("fixture_owner", "compiler_sysroot", "fixture_output_root",
                        "toolchain", "compiler_text", "artifact_count", "expected_report")})
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
                    require(report["cli_stdout"] == reports[0]["cli_stdout"], "CLI parity changed")
                require(Path(report["python"]["executable"]).resolve() == PYTHON.resolve(), "driver interpreter differs")
                previous_modules = module_sets.setdefault((arm, case), report["modules"])
                require(previous_modules == report["modules"], "per-arm CLI module inventory changed")
                reports.append(report)
                require(fixture_snapshot(fixtures) == frozen_fixtures, "CLI changed fixture")
                if phase == "parity":
                    require(not list(CACHE.iterdir()), "-B parity wrote bytecode")
                if warmup:
                    warm_reports.append(report)
                if index == 5:
                    require(len(warm_reports) == 4, "warmup schedule incomplete")
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
            require(len(ROWS) == 46 and len(CHILDREN) == 92 and len({r["label"] for r in CHILDREN}) == 92
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
        status = "PASS" if error is None and post_error is None and len(ROWS) == 46 and len(CHILDREN) == 92 else "FAIL"
        result = dict(status=status, error=error, post_binding_error=post_error, rows=ROWS, children=CHILDREN,
            preparation=[], summary=summary, gates=checks,
            fixed_decision_satisfied=status == "PASS" and checks is not None and len(checks) == 8 and all(checks.values()),
            scope=plan["scope"], decision_sha256=PLAN_SHA, bindings_sha256=BINDINGS_SHA,
            qualification_sha256=QUALIFICATION_SHA, fixture_descriptor_sha256=FIXTURE_DESCRIPTOR_SHA,
            unit_qualification_sha256=UNIT_SHA)
        write("result.json", result)
        print(json.dumps({k: result[k] for k in ("status", "error", "post_binding_error", "summary", "gates", "fixed_decision_satisfied")}), flush=True)
        return 0 if status == "PASS" else 1
    finally:
        os.close(fd)

if __name__=='__main__':
    raise SystemExit(main())
