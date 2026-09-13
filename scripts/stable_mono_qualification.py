"""Read-only admission of the strict per-MonoItem integration receipt.

The callback form reads only archived bytes. Compiler/std installation guards
belong to their existing loaders; this binds their identities to real controls.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

POLICY = 'stable-mono-cgu-integration-v1'
STD_POLICY = 'metadata-sysroot-v2-source-paths-release-backtrace'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def unstable_options(argv):
    options = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        require(not arg.startswith('@'), 'qualification argv contains a response file')
        if arg == '-Z':
            index += 1
            require(index < len(argv), 'qualification argv has incomplete -Z')
            arg = argv[index]
        elif arg.startswith('-Z'):
            arg = arg[2:]
        else:
            index += 1
            continue
        name, _, value = arg.partition('=')
        options.append((name.replace('_', '-'), value))
        index += 1
    return options


def argument_values(argv, option):
    result = []
    for index, arg in enumerate(argv):
        if arg == option:
            require(index + 1 < len(argv), 'incomplete qualification compiler option')
            result.append(argv[index + 1])
        elif arg.startswith(option + '='):
            result.append(arg[len(option) + 1:])
    return result


def validate_qualification(path, owner, compiler_key, tool_key, stds, *, compiler_sysroot,
                           read_bytes=None):
    """Return checked result/proof/evidence; never run a compiler or build std."""
    path, owner = Path(path), Path(owner)
    require(path.is_absolute() and path.name == 'result.json'
            and path.is_relative_to(owner / '.work'), 'qualification must be an owned result.json')
    live = read_bytes is None
    read_bytes = read_bytes or (lambda p: p.read_bytes())
    if live:
        require(path.resolve(strict=True) == path and not path.is_symlink(),
                'qualification follows a symlink')
    result_bytes = read_bytes(path)
    result = json.loads(result_bytes)
    expected = dict(status='passed', kind='real-custom-compiler-integration', benchmark=False,
        qualification_policy=POLICY, diagnostic_comparison='strict',
        qualification_scope='strict-integration', full_presentation_qualified=True,
        diagnostic_presentation='strict-structured-match', presentation_gap_count=0,
        semantic_controls='passed', source_restored=True, compiler_key=compiler_key,
        tool_key=tool_key, commands=36, launcher_commands=22, public_commands=11,
        expected_rejections=24, std_mir_policy='source-paths-v2',
        module_policy_by_mode=dict(off='off', on='off'), mono_policy_by_mode=dict(off='off', on='on'))
    require(all(result.get(k) == v for k, v in expected.items()),
            'strict MonoItem qualification is incomplete or uses different policy/tools')
    require(not result.get('diagnostic_presentation_gaps'), 'qualification has presentation gaps')
    expected_std = {mode: {k: stds[mode][k] for k in ['key', 'sysroot', 'target']}
                    for mode in ['off', 'on']}
    require(result.get('std_mir') == expected_std, 'qualification used different prepared std')
    evidence = result.get('evidence_files')
    require(isinstance(evidence, dict) and evidence, 'qualification lacks exact retained evidence')
    payloads, files = {}, {str(path): hashlib.sha256(result_bytes).hexdigest()}
    for name, digest in evidence.items():
        relative = PurePosixPath(name)
        require(name == str(relative) and not relative.is_absolute()
                and all(p not in ['.', '..'] for p in relative.parts)
                and name != 'result.json' and re.fullmatch('[0-9a-f]{64}', digest),
                'invalid qualification evidence path/hash')
        selected = path.parent / name
        if live:
            require(selected.resolve(strict=True) == selected and selected.is_file(),
                    'qualification evidence is linked or missing')
        payload = read_bytes(selected)
        require(hashlib.sha256(payload).hexdigest() == digest, 'qualification evidence changed: ' + name)
        payloads[name], files[str(selected)] = payload, digest
    require({'plan.json', 'commands.json'} <= evidence.keys(), 'qualification lacks plan/commands')
    require(result.get('plan_sha256') == evidence['plan.json'], 'qualification plan hash differs')
    plan = json.loads(payloads['plan.json'])
    require(plan.get('compiler_key') == compiler_key and plan.get('tool_key') == tool_key,
            'qualification plan uses different tools')
    commands = json.loads(payloads['commands.json'])
    require(isinstance(commands, list) and len(commands) == 36,
            'qualification command history is incomplete')
    for index, row in enumerate(commands):
        name = f'{index:02d}-child.json'
        require(name in payloads, 'qualification lacks a child completion receipt')
        child = json.loads(payloads[name])
        require(child.get('status') == 'finished' and child.get('command') == row.get('command')
                and child.get('returncode') == row.get('returncode')
                and child.get('label') == row.get('label')
                and child.get('finished_at', -1) >= child.get('started_at', 0),
                'qualification child completion differs')
    reference = result.get('compiler_flag_proof', {})
    require(reference.get('path') in evidence
            and reference.get('sha256') == evidence[reference['path']], 'missing actual compiler argv proof')
    proof = json.loads(payloads[reference['path']])
    require(proof.get('schema_version') == 1 and proof.get('policy') == POLICY
            and isinstance(proof.get('records'), list), 'unknown compiler argv proof schema')
    pairs, seen = set(), set()
    for record in proof['records']:
        mode, role, name = record.get('mode'), record.get('role'), record.get('path')
        require(mode in ['off', 'on'] and role in ['native-host', 'selected-guest']
                and name in evidence and name not in seen
                and record.get('sha256') == evidence[name], 'compiler argv record binding differs')
        seen.add(name)
        raw = json.loads(payloads[name])
        argv, original = raw.get('argv'), raw.get('raw', {})
        require(raw.get('schema_version') == 1 and isinstance(argv, list)
                and all(isinstance(arg, str) for arg in argv) and argv
                and argv[0] == str(Path(compiler_sysroot) / 'bin/rustc')
                and raw.get('compiler_sysroot') == str(compiler_sysroot)
                and isinstance(raw.get('cwd'), str) and Path(raw['cwd']).is_absolute(),
                'invalid actual compiler argv record')
        original_name = original.get('path')
        require(original_name in evidence and original.get('sha256') == evidence[original_name],
                'compiler argv JSON lacks its raw recorder bytes')
        envelope = ['rust-interp-compiler-argv-v1', raw.get('role'), str(compiler_sysroot), raw['cwd'], *argv, '']
        require(all(isinstance(v, str) and '\0' not in v for v in envelope)
                and payloads[original_name] == '\0'.join(envelope).encode(),
                'compiler argv JSON differs from raw recorder bytes')
        options = unstable_options(argv)
        require([v for k, v in options if k == 'stable-cgu-partitioning'] == ['no']
                and [v for k, v in options if k == 'stable-mono-cgu-partitioning']
                    == ['yes' if mode == 'on' else 'no'], 'actual compiler placement flags differ')
        require(not any(k in ['threads', 'proc-macro-execution-strategy', 'cache-proc-macros']
                        for k, _ in options)
                and not any(a.startswith('-j') or a == '--jobs' or a.startswith('--jobs=')
                            or a.startswith('--jobs-frontend') for a in argv),
                'qualification combines another compiler policy')
        require(len(argument_values(argv, '--crate-name')) == 1, 'compiler record is only a probe')
        targets = argument_values(argv, '--target')
        if role == 'native-host':
            require(raw['role'] in ['native', 'native-driver'] and not targets,
                    'native-host proof is not an actual native host invocation')
        else:
            require(raw['role'] == 'exported' and targets == [stds[mode]['target']]
                    and argument_values(argv, '--crate-name') == ['custom_compiler_fixture'],
                    'selected-guest proof is not the actual fixture export')
        pairs.add((mode, role))
    require(pairs == {(m, r) for m in ['off', 'on'] for r in ['native-host', 'selected-guest']},
            'qualification lacks one actual compiler role/mode')
    return dict(path=str(path), sha256=files[str(path)], result=result, compiler_flag_proof=proof,
                evidence_files=files)
