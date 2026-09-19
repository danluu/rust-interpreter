"""Read back exactly two completed strict primes without executing or rewriting them."""
from pathlib import Path
import json


def verify(a):
    from run import PRIOR_WORK, SOURCE, R_OWNER, FORBIDDEN, flags, validate_hir_flags
    from custom_compiler import file_digest as sha, require
    from mono_qualification import decode_record, option
    from workflow_compiler import runtime_receipt, verify_runtime_call, verify_flags
    read = lambda p: json.loads(Path(p).read_bytes())
    plan = read(a.plan['failed_plan']['path'])
    terminal = read(PRIOR_WORK / 'supervision.json')
    result = read(PRIOR_WORK / 'result.json')
    audit = read(a.plan['prior_failure_audit']['path'])
    expected_error = "RuntimeError('runtime admission input changed: " + str(SOURCE / a.plan['editable_source']['relative_path']) + "')"
    require(terminal['status'] == result['status'] == 'failed'
            and terminal['error'] == result['error'] == expected_error,
            'prior strict failure was not the exact retained mutable-source guard failure')
    require(audit['status'] == 'verified-retained-harness-failure'
            and audit['receipt_sha256'] == sha(PRIOR_WORK / 'supervision.json')
            and audit['result_sha256'] == sha(PRIOR_WORK / 'result.json')
            and audit['accidentally_frozen_mutable_paths'] == [a.plan['editable_source']['path']],
            'prior failure audit does not bind the two preserved primes')
    outer = read(a.plan['prior_outer']['path'])
    require(outer['status'] == 'finished' and outer['returncode'] == 1
            and outer['child_pid'] == terminal['pid'] and outer['supervisor_pid'] == terminal['parent_pid']
            and outer['child_started_at'] <= terminal['started_at'] <= terminal['admitted_at']
            <= terminal['finished_at'] <= outer['finished_at'], 'prior controller ownership/times differ')
    require(terminal['plan_sha256'] == sha(a.plan['failed_plan']['path'])
            and terminal['freeze_sha256'] == sha(a.plan['failed_freeze']['path'])
            and len(terminal['children']) == len(result['records']) == 2
            and plan['history'] == a.plan['history'], 'prior history/plan differs')
    freeze = read(a.plan['failed_freeze']['path'])
    snapshot = Path(a.plan['editable_source']['original_snapshot']['path'])
    require(snapshot == PRIOR_WORK / 'inputs' / a.plan['editable_source']['path'].lstrip('/')
            and sha(snapshot) == a.plan['editable_source']['original_sha256']
            == freeze['files'][a.plan['editable_source']['path']], 'original source snapshot differs')
    for name, digest in freeze['files'].items():
        require(sha(PRIOR_WORK / 'inputs' / name.lstrip('/')) == digest,
                'prior frozen source copy changed: ' + name)
    checked = []
    last = terminal['admitted_at']
    for index, (ref, row) in enumerate(zip(terminal['children'], result['records'], strict=True)):
        spec, declared = plan['history'][index], plan['commands'][index]
        require(all(row[k] == v for k, v in spec.items()) and row['state'] == 0,
                'saved prime state/order differs')
        directory = PRIOR_WORK / 'raw' / f'{index:03d}-{spec["label"]}'
        child = read(directory / 'receipt.json')
        require(ref == dict(label=spec['label'], path=str(directory), receipt=child)
                and row['receipt'] == str(directory / 'receipt.json')
                and child['command'] == declared['command'] and child['cwd'] == str(R_OWNER)
                and child['environment'] == plan['child_environment']
                and child['status'] == 'finished' and child['returncode'] == 0
                and child['supervisor_pid'] == terminal['pid']
                and child['parent_pid'] == terminal['parent_pid']
                and last <= child['started_at'] <= child['finished_at'] <= terminal['finished_at'],
                'saved prime actual argv/environment/owner/order differs')
        last = child['finished_at']
        identity = child['identity']
        require(identity['ps_returncode'] == identity['cwd_returncode'] == 0
                and identity['ps'].split()[:3] == [str(child['pid']), str(terminal['pid']), str(child['pid'])]
                and identity['ps'].endswith(' '.join(child['command']))
                and 'n' + str(R_OWNER) in identity['cwd'].splitlines(), 'saved prime process proof differs')
        for stream in ['stdout', 'stderr']:
            require((directory / stream).stat().st_size <= 64*2**20
                    and sha(directory / stream) == child[stream + '_sha256'], 'saved raw stream changed')
        stdout, stderr = (directory / 'stdout').read_text(), (directory / 'stderr').read_text()
        reports = [json.loads(line.removeprefix('rust-interp-launch: '))
                   for line in stderr.splitlines() if line.startswith('rust-interp-launch: ')]
        proof = row['proof']
        require(len(reports) == 1 and reports[0] == proof['launch'] and stdout.strip() == '0',
                'saved original-source test batch did not pass exactly once')
        launch = reports[0]
        require(launch['trap_unsupported_calls'] is False and launch['run_try_callbacks'] is False
                and 'call_report_path' not in launch and 'unavailable_calls' not in launch,
                'saved prime used compatibility policies')
        call = dict(command=child['command'], stdout=stdout, stderr=stderr, returncode=0, launch=launch)
        verify_runtime_call(call, runtime_receipt(a.compiler),
                            dict(key=a.standard[2], sysroot=str(a.standard[0]), target=a.standard[1]))
        verify_flags(call, flags(spec['mode']), launcher=True)
        require(launch['tool_key'] == a.key, 'saved tool key differs')
        for key in ['bytecode', 'catalog', 'dep_info', 'cargo_timing']:
            item = proof[key]; path = Path(item['path'])
            require(path.is_relative_to(PRIOR_WORK / 'artifacts') and path.resolve(strict=True) == path
                    and path.stat().st_size == item['bytes'] and sha(path) == item['sha256'],
                    'saved prime artifact changed')
        require(proof['bytecode']['sha256'] == launch['artifact_sha256'], 'saved bytecode launch association differs')
        selected = []
        for record in proof['compiler_records']:
            path = Path(record['path'])
            require(path.is_relative_to(PRIOR_WORK / 'compiler-argv' / spec['label'])
                    and sha(path) == record['sha256'], 'saved compiler record changed')
            actual = decode_record(path)
            require(all(record[k] == v for k, v in actual.items()), 'saved decoded compiler record differs')
            if record['role'] == 'exported': selected.append(record)
        require(len(selected) == 1, 'saved selected export count differs')
        selected = selected[0]
        require(selected['argv'][0] == str(a.compiler.rustc)
                and selected['compiler_sysroot'] == str(a.compiler.sysroot)
                and option(selected['argv'], '--crate-name') == 'ruff_linter' and '--test' in selected['argv'],
                'saved selected compiler route differs')
        validate_hir_flags(selected['argv'], 'on' if spec['mode'] == 'candidate' else 'off')
        deps = proof['exporter_env_dependencies']
        dep_lines = Path(proof['dep_info']['path']).read_text().splitlines()
        require(all(name in deps and deps[name] is None and '# env-dep:' + name in dep_lines for name in FORBIDDEN),
                'saved exporter policy was not unset')
        checked.append(dict(row, evidence_owner=str(PRIOR_WORK), reused_saved_call=True))
    require(checked[0]['proof']['bytecode']['sha256'] == checked[1]['proof']['bytecode']['sha256'],
            'saved original-source bytecode differs by mode')
    return checked
