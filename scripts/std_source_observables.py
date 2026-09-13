"""Pure archived validation of the separate real source-observable prerequisite."""
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from types import SimpleNamespace

from verified_std_diagnostics import source_span_text
from stable_mono_cgu import receipt as mono_receipt
from stable_mono_qualification import argument_values
from source_observable_transport import (POLICY, TRANSPORT, COMMANDS, PHASES, EXPORTED_PHASES,
    native_phase, validate_fixture, validate_transport)

SOURCE = 'lib/rustlib/src/rust/library/'
APP_PREFIX = '/owned-source-observable/src'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def spans(value):
    if isinstance(value, list):
        for child in value:
            yield from spans(child)
    elif isinstance(value, dict):
        if 'file_name' in value:
            yield value
        for child in value.values():
            yield from spans(child)


def diagnostics(stderr):
    return [json.loads(line) for line in stderr.splitlines() if line.startswith('{')]


def without_rendered(value):
    if isinstance(value, list):
        return [without_rendered(v) for v in value]
    if isinstance(value, dict):
        return {k: without_rendered(v) for k, v in value.items() if k != 'rendered'}
    return value


def validate_source_observables(path, owner, compiler_key, tool_key, stds, *, compiler_sysroot, read_bytes=None):
    path, owner = Path(path), Path(owner)
    require(path.is_absolute() and path.name == 'result.json' and path.is_relative_to(owner / '.work')
            and '..' not in path.parts, 'source prerequisite must be an owned result.json')
    live = read_bytes is None
    read_bytes = read_bytes or (lambda p: p.read_bytes())
    def read(selected):
        if live:
            require(selected.resolve(strict=True) == selected and selected.is_file(), 'source prerequisite is linked or missing')
        return read_bytes(selected)
    original = read(path)
    result = json.loads(original)
    expected_std = {m: {k: stds[m][k] for k in ['key', 'sysroot', 'target']} for m in ['off', 'on']}
    expected = dict(status='passed', policy=POLICY, transport_policy=TRANSPORT, guest_negative_controls=4,
        owner=str(owner), compiler_key=compiler_key, tool_key=tool_key,
        compiler_sysroot=str(compiler_sysroot), std_mir=expected_std, benchmark=False, diagnostics_rewritten=False,
        source_restored=True, qualification_only=True, unmapped_source_paths='passed',
        std_only_application_observables='unchanged', application_remap_sensitivity='expected-span-file-only-change',
        disposable_source_negatives='rejected-by-raw-source-validator', commands=COMMANDS)
    require(all(result.get(k) == v for k, v in expected.items()), 'source prerequisite is missing or uses different identities/scope')
    evidence = result.get('evidence_files')
    require(isinstance(evidence, dict) and evidence, 'source prerequisite lacks retained evidence')
    payloads, files = {}, {str(path): hashlib.sha256(original).hexdigest()}
    for name, sha in evidence.items():
        relative = PurePosixPath(name)
        require(name == str(relative) and not relative.is_absolute() and name != 'result.json'
                and all(p not in ['.', '..'] for p in relative.parts) and re.fullmatch('[0-9a-f]{64}', sha),
                'invalid source prerequisite evidence path/hash')
        payload = read(path.parent / name)
        require(hashlib.sha256(payload).hexdigest() == sha, 'source prerequisite evidence differs: ' + name)
        payloads[name], files[str(path.parent / name)] = payload, sha
    require({'plan.json', 'commands.json', 'controls.json', 'diagnostic-mapping.json'} <= payloads.keys(),
            'source prerequisite lacks required control documents')
    plan, rows, controls = [json.loads(payloads[n]) for n in ['plan.json', 'commands.json', 'controls.json']]
    require(result['plan_sha256'] == evidence['plan.json'] and plan['compiler_key'] == compiler_key
            and plan['tool_key'] == tool_key and plan['std_mir'] == expected_std
            and plan['compiler_sysroot'] == str(compiler_sysroot) and digest(plan['compiler']) == compiler_key,
            'source prerequisite plan identities differ')
    require(plan.get('policy') == POLICY and plan.get('transport_policy') == TRANSPORT
            and plan.get('expected_commands') == COMMANDS, 'source prerequisite transport plan differs')
    validate_fixture(payloads)
    sources = {p[len(SOURCE):]: h for p, h in plan['compiler']['files'].items() if p.startswith(SOURCE)}
    require(sources and sources == plan['source_files'], 'source prerequisite compiler source inventory differs')
    for mode, std in expected_std.items():
        ready = plan['std_readiness'][mode]
        identity = ready['identity']
        require(digest(identity) == std['key'] and identity['compiler_key'] == compiler_key
                and identity['namespace'] == 'stable-mono-cgu:' + mode
                and identity['source_files'] == sources and ready['full_presentation_qualified'] is False,
                'source prerequisite prepared std provenance differs')
    require(set(plan['copy_proofs']) == set(controls['second_prefix_final']) == {'native', 'off', 'on'},
            'missing complete second-prefix copy proof')
    for role, proof in plan['copy_proofs'].items():
        expected_files = plan['compiler']['files'] if role == 'native' else plan['std_readiness'][role]['sysroot_files']
        original_root = str(compiler_sysroot) if role == 'native' else expected_std[role]['sysroot']
        require(proof['files'] == expected_files and proof['files_sha256'] == digest(expected_files)
                and proof['original'] == original_root and proof['path'] == plan['copied_sources'][role]
                and controls['second_prefix_final'][role] == dict(path=proof['path'], files_sha256=proof['files_sha256'],
                    files_unchanged=True, stamps_unchanged=True), 'second-prefix copied bytes or final equality proof differs')
    require(len(rows) == COMMANDS, 'source prerequisite child history is incomplete')
    for index, row in enumerate(rows):
        child = json.loads(payloads[f'{index:03d}-child.json'])
        require(child.get('status') == 'finished' and child.get('command') == row['command']
                and child.get('cwd') == row['cwd'] and child.get('label') == row['label']
                and child.get('returncode') == row['returncode'] == row['expected_returncode']
                and child.get('finished_at', -1) >= child.get('started_at', 0),
                'source prerequisite child completion differs')
    def selected(index):
        require(type(index) is int and 0 <= index < len(rows), 'invalid source control command index')
        return rows[index]
    def source_payload(relative):
        record = controls['standard_source_files'][relative]
        require(record['sha256'] == sources[relative] == evidence[record['path']], 'retained standard source differs')
        return payloads[record['path']]
    def checked_diagnostic(row, sysroot):
        records = diagnostics(row['stderr'])
        require(row['returncode'] == 1 and any(d.get('code', {}) and d['code'].get('code') == 'E0080' for d in records),
                'source control did not retain ordinary E0080 rejection')
        prefix, seen = str(Path(sysroot) / SOURCE) + '/', set()
        for span in spans(records):
            name = span['file_name']
            if name.startswith(prefix):
                relative = name[len(prefix):]
                require(relative in sources and span.get('text') and span['text'] == source_span_text(span, source_payload(relative)),
                        'actual archived source diagnostic snippet/coordinates differ')
                seen.add(relative)
            else:
                require(not name.startswith(('/rustc/', 'library/', 'core/', 'std/')), 'unresolved archived standard source')
        require({'core/src/panic.rs', 'std/src/macros.rs'} <= seen, 'source control lacks both std expansion spans')
        return records
    histories = controls['diagnostic_histories']
    require(len(histories) == 6 and {(h['prefix'], h['role']) for h in histories}
            == {(p, r) for p in ['original', 'second'] for r in ['native', 'off', 'on']},
            'missing original/second-prefix source history')
    for history in histories:
        expected_root = (str(compiler_sysroot) if history['role'] == 'native' else expected_std[history['role']]['sysroot'])
        if history['prefix'] == 'second':
            expected_root = plan['copied_sources'][history['role']]
            require(Path(expected_root).is_relative_to(path.parent / 'second-prefix'), 'second prefix is not a disposable owned copy')
        require(history['sysroot'] == expected_root and set(history['states']) == {'cold', 'position-edited', 'restored'},
                'source history prefix or states differ')
        states = history['states']
        source_path = Path(history['source'])
        require(source_path.is_relative_to(path.parent / 'source-histories'), 'source history escaped owned fixtures')
        original_source = payloads[str(source_path.relative_to(path.parent))]
        require(states['cold']['source_sha256'] == hashlib.sha256(original_source).hexdigest()
                and states['position-edited']['source_sha256'] == hashlib.sha256('// café\n\n'.encode() + original_source).hexdigest(),
                'retained source bytes do not prove the actual position edit')
        for state in states.values():
            row = selected(state['command_index'])
            require(checked_diagnostic(row, expected_root) == state['diagnostics'], 'diagnostic view differs from raw output')
            require('--sysroot' in row['command'] and row['command'][row['command'].index('--sysroot')+1] == expected_root
                    and row['command'][0] == str(Path(compiler_sysroot if history['prefix'] == 'original'
                                                     else plan['copied_sources']['native']) / 'bin/rustc')
                    and not any(a.startswith('--remap-path-') for a in row['command']), 'unmapped source control flags differ')
        require(without_rendered(states['cold']['diagnostics']) == without_rendered(states['restored']['diagnostics'])
                and states['cold']['source_sha256'] == states['restored']['source_sha256']
                and states['cold']['source_sha256'] != states['position-edited']['source_sha256'],
                'source position edit/restoration did not occur')
        def positions(state):
            return sorted(tuple(s[k] for k in ['byte_start', 'byte_end', 'line_start', 'line_end', 'column_start', 'column_end'])
                          for s in spans(states[state]['diagnostics']) if s['file_name'] == history['source'])
        before = positions('cold')
        shift = len('// café\n\n'.encode())
        require(before and positions('position-edited') == [tuple(v + (shift if i < 2 else 2 if i < 4 else 0)
            for i, v in enumerate(values)) for values in before], 'raw source positions did not follow the exact edit')
    negatives = controls['negatives']
    require(len(negatives) == 2 and {n['kind'] for n in negatives} == {'missing', 'corrupt'}, 'missing disposable source negatives')
    original_files = plan['std_readiness']['off']['sysroot_files']
    victim = SOURCE + 'core/src/panic.rs'
    for control in negatives:
        require(Path(control['sysroot']).is_relative_to(path.parent)
                and control['changed_source'] == str(Path(control['sysroot']) / victim), 'source negative escaped its owned copy')
        after = control['after_files']
        require({p: h for p, h in after.items() if p != victim} == {p: h for p, h in original_files.items() if p != victim}
                and ((victim not in after) if control['kind'] == 'missing' else victim in after and after[victim] != original_files[victim]),
                'negative control changed more than its disposable source file')
        row = selected(control['command_index'])
        require(row['returncode'] == 1 and control['validator_rejection']
                and row['command'][0] == str(Path(compiler_sysroot) / 'bin/rustc')
                and row['command'][row['command'].index('--sysroot')+1] == control['sysroot']
                and any(d.get('code', {}) and d['code'].get('code') == 'E0080' for d in diagnostics(row['stderr'])),
                'source negative lost E0080 or did not fail validation')
    mapped = json.loads(payloads['diagnostic-mapping.json'])
    require(mapped['compiler_key'] == compiler_key and mapped['source_files'] == sources
            and mapped['diagnostic_records_rewritten'] is False and mapped['correctness_qualification_only'] is True,
            'source mapping proof differs')
    observables = controls['observable_histories']
    require(len(observables) == 4 and {(h['mode'], h['route']) for h in observables}
            == {(m, r) for m in ['off', 'on'] for r in ['native', 'exported']}, 'missing observable route or mode')
    for history in observables:
        states = history['states']
        phases = PHASES if history['route'] == 'native' else EXPORTED_PHASES
        require(set(states) == set(phases), 'incomplete observable mapping/negative history')
        indices = [states[phase]['command_index'] for phase in phases]
        require(indices == sorted(set(indices)), 'observable phase/negative/restoration order differs')
        values = {phase: states[phase]['values'] for phase in PHASES}
        require(values['unmapped'] == values['std-only'] == values['restored'], 'std-only source observables changed')
        changed = copy.deepcopy(values['application-map'])
        for label, value in changed.items():
            require(value['span_file'] == APP_PREFIX + '/' + value['relative'].removeprefix('src/')
                    and value['span_file'] != values['unmapped'][label]['span_file'], 'application mapping sensitivity differs')
            value['span_file'] = values['unmapped'][label]['span_file']
        require(changed == values['unmapped'], 'file!/local_file/coordinates changed with diagnostic-only flags')
        for phase, state in states.items():
            base_phase = native_phase(phase)
            row = selected(state['command_index']); require(row['returncode'] == 0, 'observable program failed')
            require(row['label'] == history['mode'] + '-' + phase +
                    ('-native-run' if history['route'] == 'native' else '-exported'),
                    'observable phase does not name its actual command')
            require(evidence[row['artifact_snapshot']] == row['artifact_sha256'], 'observable executed artifact snapshot differs')
            require(set(state['values']) == {'main', 'std-looking'}, 'observable source locations differ')
            if history['route'] == 'native':
                lines = [line.split('|') for line in row['stdout'].splitlines()]
                require(len(lines) == 2 and all(len(p) == 6 for p in lines), 'raw native observable output differs')
                output = {p[0]: p[1:] for p in lines}
                require(set(output) == set(state['values']), 'raw native observable output differs')
                require(state['expectation_source_sha256'] == evidence['application/src/expected.rs'],
                        'native unused expectation source differs')
            else:
                require(argument_values(row['command'], '--entry') == ['entry']
                        and argument_values(row['command'], '--package') == ['std-source-observables']
                        and argument_values(row['command'], '--manifest-path') == [str(path.parent / 'application/Cargo.toml')],
                        'exported transport did not execute the exact observation entry')
                native = next(h for h in observables if h['mode'] == history['mode'] and h['route'] == 'native')['states'][base_phase]
                native_row = selected(native['command_index'])
                require(state['values'] == native['values'] and native['command_index'] < state['command_index'],
                        'exported expectation is not the independently recorded native basis')
                transport = row['transport']
                stem = 'expectations/' + history['mode'] + '-' + phase
                require(transport == dict(policy=TRANSPORT, table=stem + '.json', source=stem + '.rs',
                    table_sha256=evidence[stem + '.json'], source_sha256=evidence[stem + '.rs'],
                    fixture_path='application/src/expected.rs', native_command_index=native['command_index'],
                    expected_mask=json.loads(payloads[stem + '.json'])['expected_mask'])
                    and state['expectation_source_sha256'] == evidence[stem + '.rs'],
                    'actual phase expectation source/table association differs')
                validate_transport(json.loads(payloads[stem + '.json']), payloads[stem + '.rs'], native['values'],
                    native['command_index'], native_row['stdout'], history['mode'], phase, row['stdout'])
            for label, value in state['values'].items():
                if history['route'] == 'native':
                    require(output[label] == [value['file'], value['span_file'], value['local_file'], str(value['line']), str(value['column'])],
                            'observable value differs from the actual output')
                relative = {'main': 'src/main.rs', 'std-looking': 'src/core/src/panic.rs'}[label]
                require(value['relative'] == relative, 'observable function source identity differs')
                workspace = Path(state['source_root'])
                require(workspace == path.parent / 'application', 'observable source root differs from actual manifest cwd')
                for field in ['file', 'local_file'] + ([] if base_phase == 'application-map' else ['span_file']):
                    reported = Path(value[field])
                    require((reported if reported.is_absolute() else workspace / reported) == workspace / relative,
                            'observable does not refer to its actual source')
                text = payloads['application/' + relative].decode()
                lines = text.splitlines()
                line = next(i for i, content in enumerate(lines) if 'observe!(marker)' in content)
                require((value['line'], value['column']) == (line + 1, lines[line].index('marker') + 1),
                        'observable coordinates disagree with retained source')
            original_main = payloads['application/src/main.rs']
            phase_source = (original_main if base_phase == 'restored' else original_main.replace(
                b'000000000000000', (str(PHASES.index(base_phase)) * 15).encode()))
            require(state['source_sha256'] == hashlib.sha256(phase_source).hexdigest(),
                    'observable phase lacks the real same-width source edit')
            flags = [] if base_phase in ['unmapped', 'restored'] else mapped['rustc_flags'][:]
            if base_phase == 'application-map': flags += ['--remap-path-prefix=src=' + APP_PREFIX]
            require(state['rustc_flags'] == flags, 'observable mapping flags differ')
            if history['route'] == 'exported':
                launches = [json.loads(line.removeprefix('rust-interp-launch: ')) for line in row['stderr'].splitlines()
                            if line.startswith('rust-interp-launch: ')]
                require(len(launches) == 1 and launches[0] == row['launch'], 'exported source control lacks its actual launch report')
                launch = launches[0]
                wrapper = plan['mono_wrapper']
                require(wrapper == dict(policy='stable-mono-cgu-routing-v1',
                    sha256=plan['tools']['rust-interp-rustc-wrapper'], compiler_sysroot=str(compiler_sysroot)),
                    'source prerequisite wrapper association differs')
                expected_compiler = dict(key=compiler_key, rustc=str(Path(compiler_sysroot) / 'bin/rustc'),
                    rustc_sha256=plan['compiler']['files']['bin/rustc'], compiler=plan['compiler']['compiler'],
                    stable_cgu_partitioning='off', stable_mono_cgu_partitioning=mono_receipt(
                        history['mode'], SimpleNamespace(identity=plan['compiler']), wrapper))
                cache = Path(state['workspace'])
                artifact = Path(launch['artifact_path'])
                require(launch['tool_key'] == tool_key and launch['custom_compiler'] == expected_compiler
                        and launch['std_mir'] == expected_std[history['mode']]
                        and launch['std_mir_policy'] == 'metadata-sysroot-v2-source-paths-release-backtrace'
                        and launch['toolchain_lookup'] == dict(mode='cached', outcome='owned-manifest')
                        and launch['workspace_path'] == str(cache)
                        and cache.is_relative_to(path.parent / 'observable-cache' / (history['mode'] + '-exported'))
                        and artifact.is_relative_to(cache / 'target')
                        and launch['artifact_sha256'] == row['artifact_sha256']
                        and launch['compiler_argv_record_dir'] == str(path.parent / 'compiler-argv' / (history['mode'] + '-' + phase))
                        and launch['artifact_bytes'] == len(payloads[row['artifact_snapshot']]),
                        'actual exported launch tool/compiler/std/artifact association differs')
            actual = [r for r in controls['actual_compiler_argv'] if (r['mode'], r['phase'], r['route'])
                      == (history['mode'], phase, history['route'])]
            require(actual, 'observable state lacks actual compiler argv')
            for proof in actual:
                argv = proof['argv']
                require(argv[0] == str(Path(compiler_sysroot) / 'bin/rustc')
                        and argument_values(argv, '--crate-name') == ['std_source_observables']
                        and [a for a in argv if a.startswith('--remap-path-')] == flags
                        and argv.count('-Zstable-cgu-partitioning=no') == 1
                        and argv.count('-Zstable-mono-cgu-partitioning=' + ('yes' if history['mode'] == 'on' else 'no')) == 1,
                        'actual observable compiler policy/remaps differ')
                if history['route'] == 'native':
                    require(proof['command_index'] == state['command_index'] - 1
                            and selected(proof['command_index'])['command'] == argv, 'native actual argv differs')
                else:
                    raw = payloads[proof['raw']]
                    fields = raw.decode().split('\0')
                    require(evidence[proof['raw']] == proof['raw_sha256'] and fields[-1] == ''
                            and fields[:3] == ['rust-interp-compiler-argv-v1', 'exported', str(compiler_sysroot)]
                            and fields[3] == state['source_root'] and fields[4:-1] == argv
                            and proof['command_index'] == state['command_index']
                            and Path(proof['raw']).is_relative_to(Path('compiler-argv') / (history['mode'] + '-' + phase))
                            and argument_values(argv, '--target') == [expected_std[history['mode']]['target']]
                            and argument_values(argv, '--sysroot') == [expected_std[history['mode']]['sysroot']],
                            'exported actual argv differs from NUL recorder bytes or source command')
    return dict(path=str(path), sha256=files[str(path)], result=result, evidence_files=files)
