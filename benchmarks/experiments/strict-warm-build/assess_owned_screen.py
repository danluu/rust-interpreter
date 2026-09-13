#!/usr/bin/env python3
"""Validate and archive saved compiler, Cargo and proc-macro mechanism screens."""
import argparse
import base64
import gzip
import os
import json
import math
from pathlib import Path
import re

from analyzer import ROOT, compressed, identity, member
from assess import require, sha
from screen import (CASE, JOBS, SUITE_WORKERS, INSTRUCTIONS, ALLOCATIONS, MINIMUM_GIB,
                    assessment as assess_rows, protocol_states, frozen_input_hash, launch_settings, command_for)
from suite_reports import read_report, validate_report, validate_runtime_limits

POLICIES = ['stable-cgu', 'stable-mono-cgu', 'cargo-info-cache', 'host-proc-macro-opt', 'host-library-opt', 'frontend-workers']


def saved_member(path):
    """Preserve binary qualification artifacts as well as existing UTF-8 evidence."""
    payload = path.read_bytes()
    result = dict(path=str(path), bytes=len(payload), sha256=sha(payload))
    try:
        result['utf8'] = payload.decode('utf-8')
    except UnicodeDecodeError:
        result['base64'] = base64.b64encode(payload).decode('ascii')
    return result


def member_bytes(item):
    require(('utf8' in item) != ('base64' in item), 'ambiguous archived member encoding')
    payload = item['utf8'].encode() if 'utf8' in item else base64.b64decode(item['base64'], validate=True)
    require(len(payload) == item['bytes'] and sha(payload) == item['sha256'], 'archived member differs')
    return payload


def markdown(s):
    title = {'stable-cgu': 'Stable code-generation groups', 'stable-mono-cgu': 'Stable per-MonoItem code-generation groups',
             'cargo-info-cache': 'Cargo compiler-info cache',
             'frontend-workers': 'Compiler frontend workers',
             'host-library-opt': 'Host-library code generation',
             'host-proc-macro-opt': 'Host proc-macro code generation'}[s['candidate_policy']]
    medians = s['complete_command_median_seconds']
    lines = ['# ' + title + ' mechanism screen', '',
        f"Candidate median: {medians['candidate']:.6f} s; baseline: {medians['baseline']:.6f} s; "
        f"independent baseline duplicate: {medians['duplicate']:.6f} s. "
        f"{s['candidate_observations_below_half_second']} of five edited candidate commands were below 0.500 s. "
        'This single-history screen does not qualify the final latency target or holdout generalization.', '',
        f"Median paired wall change: {(s['median_paired_wall_ratio'] - 1) * 100:+.3f}%; "
        f"CPU change: {(s['median_paired_cpu_ratio'] - 1) * 100:+.3f}%. "
        f"Maximum absolute A/A wall deviation: {s['maximum_aa_wall_deviation'] * 100:.3f}%; "
        f"CPU deviation: {s['maximum_aa_cpu_deviation'] * 100:.3f}%. "
        'These deviations describe the observed comparisons; they are not confidence intervals.', '',
        '| Edit | Baseline wall s | Candidate wall s | Duplicate wall s | Baseline CPU s | Candidate CPU s | Duplicate CPU s |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for pair in s['pairs']:
        values = [f"{pair[mode + suffix]:.6f}" for suffix in ['_seconds', '_cpu_seconds']
                  for mode in ['baseline', 'candidate', 'duplicate']]
        lines.append('| ' + pair['label'] + ' | ' + ' | '.join(values) + ' |')
    lines += ['', 'Wall time includes the entire launcher, Cargo, VM, all 14 original tests and receipt I/O. '
        'Waited-child CPU may exceed wall time because compilers run concurrently. Nested stages remain '
        'separate; nothing is subtracted from complete-command time.', '',
        '| Arm | Empty-target wall s | CPU s | All nine commands wall s |',
        '| --- | ---: | ---: | ---: |']
    for row in s['cold']:
        lines.append(f"| {row['mode']} | {row['seconds']:.6f} | {row['cpu']['total_seconds']:.6f} | "
                     f"{s['whole_session_command_seconds'][row['mode']]:.6f} |")
    lines += ['', 'The one cold observation per arm includes its empty project cache; installed tools '
        'and prepared std MIR are separate setup. One cold observation does not establish a repeatable '
        'cold-build gain or regression.', '',
        'All 27 commands, nine source states, five first-seen valid edited hashes per arm, all 14 original '
        'tests, deliberate wrong-result failures, compiled recovery and final restoration were checked. '
        'Outputs, outcomes, bytecode and entry catalogs agree across arms for every state. Source edits, '
        'manifests, features, units, profiles and checking requirements were preserved.', '',
        s['compiler_comparison'] + '. ' +
        ('The compiler binary, native std and exporter/VM are identical for off/on/off. '
         'This comparison does not attribute differences from a separately built public compiler to the patch.'
         if s['candidate_policy'] in ['stable-cgu', 'stable-mono-cgu'] else
         'The compiler, Cargo, exporter, VM and prepared standard library are identical for off/on/off. '
         'Only eligible host proc-macro targets receive the explicitly recorded code-generation policy; '
         'application profiles and checking remain unchanged.'
         if s['candidate_policy'] == 'host-proc-macro-opt' else
         'The compiler, Cargo, exporter, VM and prepared standard library are identical for off/on/off. '
         'Only eligible ordinary native host libraries receive O1 with original effective checks preserved. '
         'Actual three-history qualification, wrapper/compiler association and all saved input guards were verified. '
         'Application profiles, guest/build-script executable arguments and build-script environment are unchanged.'
         if s['candidate_policy'] == 'host-library-opt' else
         'Only explicit frontend worker counts change (1/2/1). Stock compiler, tool binaries, standard library, '
         'Cargo jobs, backend/linker policy and checking remain equal. The final public build identity and '
         'separate actual 30-command worker qualification were verified.' if s['candidate_policy'] == 'frontend-workers' else
         'The matched Cargo executables differ only by the qualified production-source change, with '
         'equal build settings and dynamic libraries. Cargo optimization is isolated from custom compiler policies.'), '',
        '[summary.json](summary.json) retains every pair, command, setup identity and artifact hash. '
        '[evidence.json.gz](evidence.json.gz) contains exact raw records, receipts, suites, source states, '
        'compiler/Cargo/tool provenance and frozen harness snapshots. All archive member hashes were checked. '
        'Compiler/tool binaries and project caches are not included in this compact archive. Linked '
        'qualification bytecode is retained where required. No adoption decision or '
        'fresh-project result is implied by packaging this screen.', '']
    return '\n'.join(lines)


def cargo_pair(baseline, candidate, snapshot):
    """Recheck the source-only build proof using archived provenance bytes."""
    from custom_compiler import digest
    require(baseline.identity['pinned_compiler'] == candidate.identity['pinned_compiler'] and
            baseline.identity['dynamic_libraries'] == candidate.identity['dynamic_libraries'],
            'Cargo compiler or dynamic-library closure differs')
    require(baseline.identity['files']['qualification'] == candidate.identity['files']['qualification'],
            'Cargo qualification identities differ')
    compositions = []
    for cargo, mode in [(baseline, 'stock'), (candidate, 'candidate')]:
        payloads = {}
        for name in ['source', 'qualification']:
            item = snapshot(cargo.directory / 'payload' / name)
            data = item['utf8'].encode()
            require(sha(data) == item['sha256'] == cargo.identity['files'][name],
                    'Cargo proof payload hash differs')
            payloads[name] = json.loads(data)
        manifest = payloads['source']; composition = manifest['composition']
        require(composition['mode'] == mode and digest(composition) == manifest['tool_key'] ==
                cargo.identity['provenance']['qualified_tool_key'] and
                composition['cargo_sha256'] == cargo.identity['files']['cargo'],
                'Cargo source/binary association differs')
        compositions.append(composition)
    stock, patched = compositions
    require(set(stock) == set(patched) and all(stock[k] == patched[k] for k in stock
            if k not in ['mode', 'source_inventory', 'cargo_sha256']),
            'Cargo build profile, features, compiler or settings differ')
    before, after = stock['source_inventory'], patched['source_inventory']
    require(set(before) == set(after), 'Cargo source inventory sets differ')
    changed = sorted(p for p in before if before[p] != after[p])
    require(changed == ['src/util/rustc.rs'], 'Cargo production source difference is not the qualified fix')
    report = payloads['qualification']
    require(report['status'] == 'passed' and report['candidate_source_restored'] is True and
            report['candidate_tests_passed'] == 3 and report['stock_existing_tests_passed'] == 2 and
            report['stock_expected_regression_failures'] == 1 and report['original_candidate_inventory'] == after
            and report['source_only_production_difference'] == changed[0], 'Cargo qualification outcomes differ')
    return dict(source_revision=stock['source_revision'], source_only_production_difference=changed,
        qualification_sha256=baseline.identity['files']['qualification'], source_inputs=len(before),
        baseline=baseline.receipt(), candidate=candidate.receipt())


def selection(plan, snapshot):
    """Reconstruct typed identities from frozen manifests without running tools."""
    from custom_compiler import Compiler, digest, POLICY as COMPILER_POLICY
    from custom_cargo import Cargo, POLICY as CARGO_POLICY
    policy = plan['candidate_policy']
    modes = ['baseline', 'candidate', 'duplicate']
    require(plan['case'] == json.loads(json.dumps(CASE)), 'original workflow and edit recipe differ')
    require(policy in POLICIES and set(plan['tools']) == set(modes)
            and len(set(plan['tools'].values())) == 1, 'owned screen requires one tool identity')
    require(set(plan['std_mir_by_mode']) == set(modes), 'missing per-arm std identities')
    if policy != 'host-library-opt':
        require(not any(k in plan for k in ['host_library_policy_by_mode', 'host_library_public_build_policy',
                'host_library_capability']), 'unexpected host-library screen policy')
    custom, cargos = None, dict.fromkeys(modes)
    if policy in ['stable-cgu', 'stable-mono-cgu']:
        require('cargo_comparison' not in plan and 'cargos_by_mode' not in plan, 'mixed compiler/Cargo policies')
        frozen = plan['custom_compiler']
        manifest = json.loads(snapshot(Path(frozen['manifest']))['utf8'])
        require(manifest['identity'] == frozen['identity'] and manifest['key'] == frozen['key']
                and digest(manifest['identity']) == frozen['key'] and manifest['owner'] == plan['owner']
                and manifest['identity']['policy'] == COMPILER_POLICY,
                'custom compiler manifest differs')
        custom = Compiler(frozen['key'], Path(frozen['sysroot']), frozen['identity'])
        require(Path(frozen['manifest']) == custom.sysroot.parent / 'ready.json'
                and custom.sysroot == Path(plan['owner']) / '.work/compilers' / custom.key / 'sysroot'
                and custom.identity['provenance']['stage'] == 2, 'compiler path or stage differs')
        require(plan['cgu_policy_by_mode'] == (dict.fromkeys(modes, 'off') if policy == 'stable-mono-cgu'
                else dict(baseline='off', candidate='on', duplicate='off')),
                'stable-CGU policy differs')
        if policy == 'stable-mono-cgu':
            from stable_mono_cgu import OPTION
            custom.require_option('stable-cgu-partitioning')
            custom.require_option(OPTION)
            require(plan.get('mono_cgu_policy_by_mode') == dict(baseline='off', candidate='on', duplicate='off')
                    and not any(k in plan for k in ['proc_macro_policy_by_mode', 'codegen_policy_amendment',
                        'public_input_guards', 'frontend_workers']), 'mixed or incorrect MonoItem policy')
            require(all(plan.get(k) == v for k, v in dict(cargo_jobs=JOBS, suite_workers=SUITE_WORKERS,
                instruction_limit=INSTRUCTIONS, allocation_limit=ALLOCATIONS, minimum_free_gib=MINIMUM_GIB,
                guest_rustflags=[], profile_overrides={}, final_qualification=False).items()),
                'MonoItem screen changes the frozen common workload settings')
    elif policy == 'cargo-info-cache':
        require('custom_compiler' not in plan and 'cgu_policy_by_mode' not in plan, 'mixed compiler/Cargo policies')
        for mode in modes:
            receipt = plan['cargos_by_mode'][mode]
            directory = Path(plan['owner']) / '.work/cargos' / receipt['key']
            manifest = json.loads(snapshot(directory / 'ready.json')['utf8'])
            require(manifest['key'] == receipt['key'] and digest(manifest['identity']) == receipt['key']
                    and manifest['owner'] == plan['owner'] and manifest['identity']['policy'] == CARGO_POLICY,
                    'Cargo manifest differs')
            cargos[mode] = Cargo(receipt['key'], directory, manifest['identity'])
            require(cargos[mode].receipt() == receipt, 'Cargo receipt differs from frozen manifest')
        require(cargos['baseline'] == cargos['duplicate'] and
                cargos['baseline'].identity['files']['cargo'] != cargos['candidate'].identity['files']['cargo'],
                'Cargo screen requires distinct actual candidate bytes and identical baseline/duplicate')
        require(cargo_pair(cargos['baseline'], cargos['candidate'], snapshot) == plan['cargo_comparison'],
                'Cargo matched pair differs')
    elif policy == 'host-library-opt':
        from host_library_screen import MODES as LIBRARY_MODES, BUILD_POLICY, CAMPAIGN_LOCK, amendment
        require(not any(k in plan for k in ['custom_compiler', 'cgu_policy_by_mode', 'mono_cgu_policy_by_mode',
                'cargo_comparison', 'cargos_by_mode', 'proc_macro_policy_by_mode', 'frontend_workers_by_mode',
                'worker_qualification', 'compiler_qualification', 'source_observables'])
                and plan['host_library_policy_by_mode'] == LIBRARY_MODES
                and plan['host_library_public_build_policy'] == BUILD_POLICY,
                'host-library policy is mixed or differs')
        require(plan['codegen_policy_amendment'] == amendment(plan['owner'])
                and Path(plan['workload_lock']) == CAMPAIGN_LOCK, 'host-library policy amendment or lock differs')
        require(all(plan.get(k) == v for k, v in dict(cargo_jobs=JOBS, suite_workers=SUITE_WORKERS,
            instruction_limit=INSTRUCTIONS, allocation_limit=ALLOCATIONS, minimum_free_gib=MINIMUM_GIB,
            guest_rustflags=[], profile_overrides={}, final_qualification=False).items()),
            'host-library screen changes the original workload settings')
        public = json.loads(snapshot(Path(plan['owner']) / '.work/interpreter-tools' / plan['tools']['baseline'] /
                                     'source.json')['utf8'])['composition']['public_compiler']
    elif policy == 'host-proc-macro-opt':
        require(not any(k in plan for k in ['custom_compiler', 'cgu_policy_by_mode',
                'cargo_comparison', 'cargos_by_mode']), 'mixed proc-macro/compiler/Cargo policies')
        require(plan['proc_macro_policy_by_mode'] == dict(baseline='off', candidate='on', duplicate='off'),
                'proc-macro policy differs')
        require(plan['codegen_policy_amendment'] == dict(
            path=str(Path(plan['owner']) / 'benchmarks/experiments/strict-warm-build/HOST_PROC_MACRO_OPT.md'),
            capability='host-proc-macro-opt-v1', optimized_role='unselected linked host proc-macro target',
            original_opt_level='0 (no explicit optimization flag)', opt_level='1', mir_opt_level=1,
            lto='off', preserve_effective_debug_assertions=True, preserve_effective_overflow_checks=True,
            application_profiles_changed=False, std_preparation_policy='unchanged and outside application wrapper'),
            'proc-macro code-generation amendment differs')
        key = plan['tools']['baseline']
        public = json.loads(snapshot(Path(plan['owner']) / '.work/interpreter-tools' / key /
                                     'source.json')['utf8'])['composition']['public_compiler']
    elif policy == 'frontend-workers':
        from frontend_worker_screen import COUNTS, BUILD_POLICY, CAMPAIGN_LOCK
        require(not any(k in plan for k in ['custom_compiler', 'cgu_policy_by_mode', 'cargo_comparison', 'cargos_by_mode'])
                and plan['frontend_workers_by_mode'] == COUNTS
                and plan['worker_public_build_policy'] == BUILD_POLICY, 'worker policy is mixed or differs')
        lock = Path(plan['workload_lock'])
        require(lock == CAMPAIGN_LOCK, 'worker lock identity differs')
        public = json.loads(snapshot(Path(plan['owner']) / '.work/interpreter-tools' / plan['tools']['baseline'] / 'source.json')['utf8'])['composition']['public_compiler']
    for mode in modes:
        from std_mir import FLAGS, POLICY
        std = plan['std_mir_by_mode'][mode]
        if policy == 'stable-mono-cgu':
            from owned_mono_screen import validate_std
            validate_std(std, plan['owner'], custom, plan['mono_cgu_policy_by_mode'][mode],
                         lambda path: member_bytes(snapshot(path)))
            continue
        retained = snapshot(Path(std['path']))
        ready = json.loads(retained['utf8'])
        identity = ready['identity']
        key = sha(json.dumps(identity, sort_keys=True).encode())
        path = Path(plan['owner']) / '.work/std-mir' / key / 'ready.json'
        require(key == std['key'] and Path(std['path']) == path and ready['owner'] == plan['owner']
                and sha(retained['utf8'].encode()) == retained['sha256'] == std['sha256']
                and std['sysroot'] == str(path.parent / 'sysroot') and identity['policy'] == POLICY
                and identity['flags'] == FLAGS and std['target'] == identity['target']
                and std['compiler'] == identity['compiler'], 'std manifest or actual routing differs')
        artifacts = {}
        for name, proof in ready['artifacts'].items():
            artifact = path.parent / name
            require(not Path(name).is_absolute() and artifact.is_relative_to(path.parent / 'sysroot')
                    and str(artifact) == os.path.normpath(str(artifact)), 'std artifact path escapes sysroot')
            artifacts[str(artifact)] = proof
        require(artifacts and artifacts == std['artifacts'], 'std artifact proof differs')
        for crate in ['core', 'alloc', 'std', 'test', 'proc_macro']:
            library = path.parent / 'sysroot/lib/rustlib' / identity['target'] / 'lib'
            require(sum(Path(p).parent == library and Path(p).match('lib' + crate + '-*.rmeta')
                        for p in artifacts) == 1, 'missing or ambiguous prepared std artifact')
        if custom:
            require(identity['compiler_key'] == custom.key and 'cargo' not in identity
                    and identity['namespace'] == 'stable-cgu:' + plan['cgu_policy_by_mode'][mode]
                    and identity['compiler'] == custom.identity['compiler']
                    and identity['target'] == custom.host
                    and identity['source_sha256'] == custom.identity['source_sha256']
                    and identity['lock_sha256'] == custom.identity['files'][
                        'lib/rustlib/src/rust/library/Cargo.lock'],
                    'std compiler/policy differs')
        elif policy == 'cargo-info-cache':
            require(identity['cargo'] == cargos[mode].receipt()
                    and identity['compiler'] == cargos[mode].identity['pinned_compiler']['compiler']
                    and identity['target'] == cargos[mode].identity['pinned_compiler']['host']
                    and not any(k in identity for k in ['compiler_key', 'namespace', 'source_sha256']),
                    'std Cargo differs')
        else:
            require(not any(k in identity for k in ['cargo', 'compiler_key', 'namespace', 'source_sha256'])
                    and sha(identity['compiler'].encode()) == public['version_stdout_sha256']
                    and identity['target'] == public['target'], 'std public compiler differs')
    stds = plan['std_mir_by_mode']
    if policy in ['host-proc-macro-opt', 'host-library-opt', 'frontend-workers']:
        require(stds['baseline'] == stds['candidate'] == stds['duplicate'] == plan['std_mir'],
                'proc-macro comparison requires one unchanged shared std')
    else:
        require(stds['baseline'] == stds['duplicate'] and stds['baseline']['key'] != stds['candidate']['key'],
                'std namespaces must match baseline/duplicate and isolate candidate')
    if policy == 'stable-mono-cgu':
        require(plan['std_mir'] == stds['baseline'], 'MonoItem default std differs from its baseline')
        before, after = [stds[mode]['identity'] for mode in ['baseline', 'candidate']]
        require(set(before) == set(after) and all(before[k] == after[k] for k in before
                if k not in ['namespace', 'build_environment_sha256']), 'MonoItem std preparation settings differ')
    return custom, cargos


def tool_identity(plan, key, custom, snapshot):
    """Bind the retained exporter capability to its physical compiler prefix."""
    if plan['candidate_policy'] == 'host-library-opt':
        from host_library_screen import public_build, standard_binding, runtime_harness
        tool = Path(plan['owner']) / '.work/interpreter-tools' / key
        read = lambda path: member_bytes(snapshot(path))
        validated = public_build(tool, key, read)
        require(set(plan['binaries']) == set(plan['tools'])
                and all(validated['composition']['binaries'] == proof for proof in plan['binaries'].values())
                and plan['host_library_capability'] == validated['capability'],
                'host-library screen differs from qualified actual binaries/capability')
        standard_binding(validated, plan['std_mir'])
        qualified_std(plan, validated, snapshot)
        runtime_harness(validated, plan['owner'], read)
        return validated
    if plan['candidate_policy'] == 'host-proc-macro-opt':
        from qualified_public_tools import validate_public_tool
        tool = Path(plan['owner']) / '.work/interpreter-tools' / key
        validated = validate_public_tool(tool, key, lambda path: snapshot(path)['utf8'].encode())
        require(all(validated['composition']['binaries'] == plan['binaries'][mode]
                    for mode in plan['tools']), 'qualified public tool binaries differ from screen')
        qualified_std(plan, validated, snapshot)
        return validated
    from custom_compiler import TOOL_POLICY, digest
    tool = Path(plan['owner']) / '.work/interpreter-tools' / key
    if plan['candidate_policy'] == 'frontend-workers':
        from frontend_worker_screen import public_build, standard_binding, validate_qualification
        read = lambda path: member_bytes(snapshot(path))
        validated = public_build(tool, key, read)
        from qualified_public_tools import validate_input_guard
        require(all(validated['composition']['binaries'] == manifest for manifest in plan['binaries'].values())
                and set(plan['binaries']) == set(plan['tools'])
                and validated['capability'] == plan['worker_capability'], 'worker tool composition differs')
        standard_binding(validated, plan['std_mir'])
        proof = validate_qualification(Path(plan['worker_qualification']['result_path']), key,
            validated, plan['std_mir'], read)
        require(proof == plan['worker_qualification'], 'worker qualification differs from screen admission')
        require(proof['workload_lock'] == plan['workload_lock'], 'worker qualification lock differs')
        validate_input_guard(validated, plan['public_input_guard'])
        return validated
    name = 'compiler.json' if custom else 'source.json'
    source = json.loads(snapshot(tool / name)['utf8'])
    composition = source if custom else source['composition']
    binaries = composition['binaries']
    require(digest(composition) == key and all(binaries == plan['binaries'][m] for m in plan['tools'])
            and binaries == json.loads(snapshot(tool / 'ready.json')['utf8']), 'tool composition differs')
    capability = json.loads(snapshot(tool / 'capabilities.json')['utf8'])
    require(capability['schema_version'] == 1 and capability['bytecode_version'] == 5
            and capability['tool_key'] == key
            and capability['exporter_sha256'] == binaries['rust-interp-mir-export'],
            'tool capability association differs')
    if custom:
        require(composition['kind'] == TOOL_POLICY and composition['compiler_key'] == custom.key
                and composition['compiler_sysroot'] == str(custom.sysroot)
                and capability['compiler_sysroot'] == str(custom.sysroot)
                and 'stable-cgu-partitioning' in capability['export_options'],
                'exporter compiler association differs')
        if plan['candidate_policy'] == 'stable-mono-cgu':
            from stable_mono_cgu import OPTION, POLICY, WRAPPER
            expected = dict(policy=POLICY, sha256=binaries[WRAPPER], compiler_sysroot=str(custom.sysroot))
            require(OPTION in capability['export_options']
                    and capability.get('stable_mono_cgu_wrapper') == expected == plan.get('mono_wrapper'),
                    'MonoItem exporter/wrapper capability differs')
            for std in plan['std_mir_by_mode'].values():
                cargo = std['identity']['cargo']
                require(composition['cargo'] == {k: cargo[k] for k in ['executable', 'sha256', 'toolchain', 'version']},
                        'MonoItem tool/std Cargo identities differ')


def qualified_std(plan, validated, snapshot):
    """Bind the measured shared std to the one used for public-tool qualification."""
    shared = validated['correctness']['shared_std']
    measured = plan['std_mir']
    ready = json.loads(snapshot(Path(measured['path']))['utf8'])
    require(shared['key'] == measured['key'] and shared['sysroot'] == measured['sysroot']
            and shared['ready_sha256'] == measured['sha256'] and shared['identity'] == ready['identity'],
            'measured std differs from public-tool qualification')


def public_screen_guards(plan, rows, summary, raw, validated, snapshot):
    """Check saved input guards without reopening compiler or library binaries."""
    from qualified_public_tools import validate_input_guard
    policy = 'qualified-public-input-guard-v1'
    directory = raw / 'public-input-guards'
    manifest = plan['public_input_guards']
    require(manifest['policy'] == policy and manifest['directory'] == str(directory)
            and manifest['final_path'] == str(directory / 'final.json')
            and manifest['boundaries_per_command'] == 2 and len(rows) == 27,
            'public input guard plan differs')

    def read(reference, expected, validation):
        require(reference['path'] == str(expected), 'public input guard path differs')
        item = snapshot(expected)
        require(sha(item['utf8'].encode()) == item['sha256'] == reference['sha256'],
                'public input guard bytes differ')
        guard = json.loads(item['utf8'])
        validate_input_guard(validated, guard)
        require(guard['validation'] in validation, 'public input guard verification mode differs')
        return guard

    admission = read(manifest['admission'], directory / 'admission.json', ['sha256'])
    guards = []
    for ordinal, row in enumerate(rows):
        require(set(row['public_input_guards']) == {'before', 'after'}, 'missing public input command boundary')
        for boundary in ['before', 'after']:
            guards.append(read(row['public_input_guards'][boundary],
                directory / f'{ordinal:03d}-{boundary}.json', ['stat', 'sha256']))
    guards.append(read(summary['final_public_input_guard'], directory / 'final.json', ['sha256']))
    require(all(all(guard[k] == admission[k] for k in ['schema_version', 'policy', 'tool_key',
                'platform', 'files', 'searches']) for guard in guards),
            'public compiler, Cargo, tools or dynamic inputs changed during history')
    return dict(records_verified=1 + len(guards), commands=len(rows),
                policy=policy, executable_or_dependency_bytes_read=False)


def workspace_identity(row, raw, workspaces):
    """Validate saved paths without requiring retired project caches to exist."""
    mode = row['mode']
    workspace = Path(row['launch']['workspace_path'])
    artifact = Path(row['launch']['artifact_path'])
    require(all(p.is_absolute() and str(p) == os.path.normpath(str(p)) for p in [workspace, artifact])
            and workspace.is_relative_to(raw / 'caches' / mode)
            and workspace != raw / 'caches' / mode and artifact.is_relative_to(workspace / 'target'),
            'actual workspace or artifact escapes its arm cache')
    require(workspaces.setdefault(mode, workspace) == workspace,
            'actual workspace changed within an arm')
    require(len(set(workspaces.values())) == len(workspaces), 'actual arm caches are not independent')


def command_identity(plan, row, raw, custom, cargo):
    expected = command_for(row['mode'], plan['tools'][row['mode']], Path(plan['source']), raw,
        plan['states'][row['index']], names=plan['case']['tests'], candidate_policy=plan['candidate_policy'],
        compiler_key=custom.key if custom else None, cargo_key=cargo.key if cargo else None,
        prepared_std=plan['std_mir_by_mode'][row['mode']] if plan['candidate_policy'] == 'stable-mono-cgu' else None)
    # Repackaging may use another Python installation; retain the original
    # interpreter spelling while checking every workload argument and its order.
    require(row['command'] and isinstance(row['command'][0], str), 'missing launcher interpreter')
    expected[0] = row['command'][0]
    require(row['command'] == [str(x) for x in expected], 'timed command differs from policy and original workload')
    for value in [row['seconds'], row['cpu']['user_seconds'], row['cpu']['system_seconds'],
                  row['cpu']['total_seconds']]:
        require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                'invalid complete-command wall or CPU duration')
    require(row['seconds'] > 0 and row['cpu']['total_seconds'] > 0 and
            math.isclose(row['cpu']['total_seconds'], row['cpu']['user_seconds'] + row['cpu']['system_seconds'],
                         rel_tol=1e-12, abs_tol=1e-12), 'inconsistent complete-command CPU duration')


def mono_launch_identity(plan, row, custom):
    """Validate every saved effective selector without resolving retired caches."""
    mode, launch = row['mode'], row['launch']
    expected = launch_settings(mode, plan['tools'][mode], 'stable-mono-cgu', custom,
                               mono_wrapper=plan['mono_wrapper'])
    require(all(launch.get(k) == v for k, v in expected.items())
            and launch.get('query_cache_retention', 'off') == 'off'
            and launch.get('host_proc_macro_opt', 'off') == 'off'
            and launch.get('frontend_workers') is None
            and launch.get('compiler_argv_record_dir') is None
            and 'custom_cargo' not in launch,
            'MonoItem effective launch mixes policies or qualification instrumentation')
    require(launch['toolchain_lookup']['mode'] == 'cached'
            and launch['toolchain_lookup']['outcome'] == 'owned-manifest',
            'MonoItem compiler lookup did not use its owned identity')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--snapshots-from', type=Path,
                        help='previous result summary with a verified exact source/harness archive')
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9][a-z0-9-]{0,95}', args.run_id), 'invalid run ID')
    raw = args.raw.resolve(strict=True)
    require(raw.is_relative_to(ROOT / '.work'), 'input escapes owned workspace')
    files = {str(raw / name): member(raw / name) for name in
             ['plan.json', 'records.json', 'summary.json', 'transitions.json']}
    plan, rows, original_summary, transitions = [json.loads(files[str(raw / n)]['utf8'])
        for n in ['plan.json', 'records.json', 'summary.json', 'transitions.json']]
    require(plan['owner'] == str(ROOT) and plan['kind'] == 'mechanism-screen' and
            plan['final_qualification'] is False and original_summary['source_restored'] is True and
            plan['candidate_policy'] == original_summary['candidate_policy'] and
            plan['candidate_policy'] in POLICIES,
            'expected completed owned mechanism screen')
    require(plan['guest_rustflags'] == [] and plan['profile_overrides'] == {} and
            len(plan['case']['tests']) == 14, 'workload profiles or original test count differ')
    prior_files, prior_summary = {}, None
    if args.snapshots_from:
        previous_result = args.snapshots_from.resolve(strict=True)
        prior_summary = json.loads(previous_result.read_bytes())
        prior_archive = previous_result.parent / prior_summary['archive']['path']
        require(identity(prior_archive)['sha256'] == prior_summary['archive']['sha256'] and
                prior_summary['frozen_inventory_verified'] is True and
                prior_summary['plan_sha256'] == original_summary['plan_sha256'] and
                prior_summary['records_sha256'] == original_summary['records_sha256'],
                'prior snapshots do not identify this verified screen')
        prior_bundle = json.loads(gzip.decompress(prior_archive.read_bytes()))
        for item in prior_bundle['files']:
            member_bytes(item)
            prior_files[item['path']] = item
        require(prior_files[str(raw / 'plan.json')]['sha256'] == original_summary['plan_sha256'] and
                prior_files[str(raw / 'records.json')]['sha256'] == original_summary['records_sha256'],
                'prior archived plan or records differ')

    def snapshot(path):
        path = str(path)
        return prior_files[path] if args.snapshots_from else saved_member(Path(path))

    def frozen_snapshot(path):
        item = snapshot(path)
        require(sha(b'file\0' + member_bytes(item)) == plan['frozen'][str(path)],
                'frozen snapshot differs: ' + str(path))
        files[str(path)] = item
        return item

    def linked_snapshot(path):
        # Qualification/setup paths are in the frozen screen inventory. Actual
        # standard source snippets are additionally bound by compiler/std file
        # hashes in the pure validator, and may survive a retired setup target.
        if str(path) in plan['frozen']:
            return frozen_snapshot(path)
        from std_mir_source_paths import SOURCE
        roots = [Path(plan['custom_compiler']['sysroot']) / SOURCE]
        roots += [Path(std['sysroot']) / SOURCE for std in plan['std_mir_by_mode'].values()]
        require(any(Path(path).is_relative_to(root) for root in roots),
                'linked qualification/setup evidence is absent from the frozen inventory')
        item = snapshot(path)
        member_bytes(item)
        files[str(path)] = item
        return item

    if not args.snapshots_from:
        require(all(frozen_input_hash(p) == digest for p, digest in plan['frozen'].items()),
                'frozen source/tool/harness differs; use an existing verified snapshot for repackaging')
    for name in ['plan', 'records']:
        require(files[str(raw / (name + '.json'))]['sha256'] == original_summary[name + '_sha256'],
                'screen source hash differs')
    calculated = assess_rows(rows)
    require(all(original_summary[k] == v for k, v in calculated.items()), 'saved screen assessment differs')
    source_file = Path(plan['source']) / plan['case']['file']
    source_member = snapshot(source_file)
    source_bytes = source_member['utf8'].encode()
    require(sha(source_bytes) == plan['original_source_sha256'], 'source is not restored')
    files[str(source_file)] = source_member
    expected_states = protocol_states(source_bytes, plan['case'])
    expected_plan = [{k: v for k, v in state.items() if k != 'source'} |
                     dict(source_sha256=sha(state['source'])) for state in expected_states]
    require(expected_plan == plan['states'], 'saved source sequence differs from original edits')
    for state in expected_states:
        path = str(source_file) + '#state=' + str(state['index'])
        files[path] = dict(path=path, bytes=len(state['source']), sha256=sha(state['source']),
                           utf8=state['source'].decode(), reconstructed_from='original source and exact plan edits')
    require([(r['index'], r['mode']) for r in rows] ==
            [(s['index'], m) for s in plan['states'] for m in s['modes']], 'command order differs')
    require(len(transitions) == len(plan['states']), 'source transition count differs')
    for index, transition in enumerate(transitions):
        require(transition['index'] == index and transition['after'] == plan['states'][index]['source_sha256'],
                'source transition differs')
        if index < len(transitions) - 1:
            expected_before = plan['states'][max(0, index - 1)]['source_sha256']
            require(transition['before'] == expected_before, 'source transition input differs')
    custom, cargos = selection(plan, linked_snapshot if plan['candidate_policy'] == 'stable-mono-cgu'
                              else frozen_snapshot)
    mono_qualification = None
    if plan['candidate_policy'] == 'stable-mono-cgu':
        from owned_mono_screen import qualification
        # Deliberately fail closed while the independent typed source-observable
        # validator is still being implemented; the 36-command receipt is not it.
        try:
            from std_source_observables import validate_source_observables
        except ImportError:
            validate_source_observables = None
        mono_qualification = qualification(plan, custom,
            lambda path: member_bytes(linked_snapshot(path)),
            source_observables_validator=validate_source_observables)
    worker_public = None
    if plan['candidate_policy'] == 'frontend-workers':
        worker_public = tool_identity(plan, plan['tools']['baseline'], None, frozen_snapshot)
    library_public = None
    if plan['candidate_policy'] == 'host-library-opt':
        library_public = tool_identity(plan, plan['tools']['baseline'], None, frozen_snapshot)
    artifacts, compact = {}, []
    previous = dict.fromkeys(plan['tools'])
    workspaces = {}
    for row in rows:
        index, mode = row['index'], row['mode']
        expected = plan['states'][index]
        command_identity(plan, row, raw, custom, cargos[mode])
        workspace_identity(row, raw, workspaces)
        require(row['phase'] == expected['phase'] and row['source_sha256'] == expected['source_sha256'] and
                row['previous_source_sha256'] == previous[mode], 'command source history differs')
        previous[mode] = row['source_sha256']
        receipt_path, suite_path = [raw / folder / f'{index}-{mode}.json' for folder in ['receipts', 'suites']]
        for p in [receipt_path, suite_path]:
            files[str(p)] = member(p)
        receipt = json.loads(files[str(receipt_path)]['utf8'])
        require(all(receipt[k] == row[k] for k in ['index', 'phase', 'mode', 'source_sha256', 'pid',
                'command', 'returncode']) and receipt['status'] == 'finished' and
                receipt['tool_key'] == plan['tools'][mode], 'command receipt differs')
        success = row['phase'] != 'wrong-edit'
        require((row['returncode'] == 0) == success, 'command status differs')
        suite, suite_sha = read_report(suite_path, row['suite_sha256'])
        outcomes = validate_report(suite, plan['case']['tests'], 'prepared', success)
        validate_runtime_limits(suite, plan['instruction_limit'], plan['allocation_limit'], required=True)
        require([list(x) for x in outcomes] == row['outcomes'] and
                suite['workers'] == suite['requested_workers'] == plan['suite_workers'], 'suite differs')
        launches = [json.loads(l.split(': ', 1)[1]) for l in row['stderr'].splitlines()
                    if l.startswith('rust-interp-launch: ')]
        require(launches == [row['launch']] and row['launch']['suite_report_sha256'] == suite_sha and
                row['launch']['tool_key'] == plan['tools'][mode] and
                'query_cache_retention' not in row['launch'],
                'launcher evidence differs')
        settings = launch_settings(mode, plan['tools'][mode], plan['candidate_policy'], custom, cargos[mode],
                                   mono_wrapper=plan.get('mono_wrapper'),
                                   worker_capability=worker_public['capability'] if worker_public else None,
                                   library_capability=library_public['capability'] if library_public else None)
        if library_public:
            from host_library_screen import validate_launch_policy
            validate_launch_policy(row['launch'], mode, library_public['capability'])
        else:
            require('host_library_opt' not in row['launch'], 'unexpected host-library launch policy')
        require(custom is not None or 'custom_compiler' not in row['launch'], 'unexpected custom compiler')
        require(cargos[mode] is not None or 'custom_cargo' not in row['launch'], 'unexpected custom Cargo')
        require(worker_public is not None or 'frontend_workers' not in row['launch'], 'unexpected worker policy')
        if worker_public:
            from qualified_public_tools import validate_input_guard
            for when in ['before', 'after']:
                path = raw / 'public-input-guards' / f'{index}-{mode}-{when}.json'
                item = member(path); files[str(path)] = item
                guard = json.loads(item['utf8'])
                require(guard['validation'] == 'stat', 'worker guard validation mode differs')
                validate_input_guard(worker_public, guard)
            require(row['launch'].get('host_proc_macro_opt', 'off') == 'off', 'worker launch mixes macro policy')
        require(math.isfinite(row['launch']['launcher_seconds']) and
                0 < row['launch']['launcher_seconds'] <= row['seconds'],
                'complete-command time excludes part of the launcher')
        require(all(row['launch'].get(k) == v for k, v in settings.items()) and
                '--query-cache-retention' not in row['command'] and
                row['launch']['compiler_wrapper']['sha256'] == plan['binaries'][mode]['rust-interp-rustc-wrapper']
                and 'Checking ' + plan['case']['package'] in row['stderr'] and
                sum(l.startswith('rust-interp-export: ') for l in row['stderr'].splitlines()) == 1,
                'compiler policy or selected fresh export evidence differs')
        std = plan['std_mir_by_mode'][mode]
        require(row['launch']['std_mir'] == {k: std[k] for k in ['key', 'sysroot', 'target']},
                'actual std identity differs')
        if cargos[mode]:
            require(receipt['cargo_key'] == cargos[mode].key, 'timed Cargo identity differs')
        if plan['candidate_policy'] == 'stable-mono-cgu':
            mono_launch_identity(plan, row, custom)
            require(receipt['finished_at'] >= receipt['started_at']
                    and type(row['free_bytes']) is int and row['free_bytes'] >= MINIMUM_GIB * 1024**3,
                    'MonoItem command lacks complete receipt or disk admission')
        if plan['candidate_policy'] == 'host-proc-macro-opt':
            require(receipt['host_proc_macro_opt'] == plan['proc_macro_policy_by_mode'][mode]
                    and not any(k in row['launch'] for k in ['custom_compiler', 'custom_cargo'])
                    and row['launch'].get('query_cache_retention', 'off') == 'off',
                    'timed proc-macro policy differs')
        if library_public:
            require(receipt['host_library_opt'] == plan['host_library_policy_by_mode'][mode]
                    and receipt['finished_at'] >= receipt['started_at']
                    and type(row['free_bytes']) is int and row['free_bytes'] >= MINIMUM_GIB * 1024**3,
                    'host-library timed policy, complete receipt or disk admission differs')
        for item in row['artifacts']:
            p = (ROOT / item['path']).resolve(strict=True)
            require(p.is_relative_to(raw / 'artifacts'), 'artifact snapshot escapes screen')
            actual = identity(p)
            require(actual['sha256'] == item['sha256'] and actual['bytes'] == item['bytes'],
                    'retained artifact differs')
            artifacts[item['path']] = item
            if p.suffix == '.json':
                files[str(p)] = member(p)
        bytecode, catalog_item, calls_item = row['artifacts']
        catalog, calls = [json.loads(files[str((ROOT / i['path']).resolve())]['utf8'])
                          for i in [catalog_item, calls_item]]
        require(bytecode['sha256'] == row['launch']['artifact_sha256'] == catalog['artifact_sha256'] ==
                calls['artifact_sha256'] and calls['strict_frontend'] is True and
                [e['name'] for e in catalog['entries']] == plan['case']['tests'] and
                [e['function'] for e in catalog['entries']] == [t['function'] for t in suite['tests']],
                'artifact-bound catalog/checking evidence differs')
        compact.append({k: row[k] for k in ['index', 'phase', 'label', 'mode', 'pid', 'seconds', 'cpu',
            'returncode', 'source_sha256', 'previous_source_sha256', 'suite_sha256', 'artifacts']} |
            dict(test_passed=suite['passed'], test_failed=suite['failed'],
                 stdout_sha256=sha(row['stdout'].encode()), stderr_sha256=sha(row['stderr'].encode()),
                 stages={k: row['launch'][k] for k in ['tools_seconds', 'std_mir_seconds', 'cargo_seconds',
                     'cargo_cpu', 'execution_seconds', 'build_to_ready_seconds', 'build_to_ready_cpu']},
                 failed_tests=[name for name, status in outcomes if status == 'failed']))
    for index in range(len(plan['states'])):
        group = [r for r in rows if r['index'] == index]
        require(len({json.dumps(r['outcomes']) for r in group}) == 1 and
                len({r['stdout'] for r in group}) == 1 and all(
                    len({r['artifacts'][slot]['sha256'] for r in group}) == 1 for slot in [0, 1]),
                'cross-arm suite, bytecode, catalog or output differs')
    provenance = []
    for key in sorted(set(plan['tools'].values())):
        tool = ROOT / '.work/interpreter-tools' / key
        for name in ['ready.json', 'capabilities.json', 'compiler.json' if custom else 'source.json']:
            p = tool / name
            frozen_snapshot(p)
            provenance.append({k: files[str(p)][k] for k in ['path', 'bytes', 'sha256']})
    for p in [Path(__file__).with_name('screen.py'), Path(__file__).with_name('PROTOCOL.md'),
              Path(plan['source']) / '.rust-interp-owned.json', Path(plan['std_mir']['path'])]:
        frozen_snapshot(p)
    for path in plan['frozen']:
        if Path(path).parent == ROOT / 'scripts' or path == str(ROOT / 'benchmarks/corpus.json'):
            frozen_snapshot(path)
    # Preserve the complete hash inventory in the exact plan, and spell out
    # symlink identity without copying or following directory/link fixtures.
    source_symlinks = prior_summary['source_symlinks'] if prior_summary else [
        dict(path=p, target=os.readlink(p), frozen_sha256=digest)
        for p, digest in plan['frozen'].items() if Path(p).is_symlink()]
    for link in source_symlinks:
        require(sha(b'symlink\0' + os.fsencode(link['target'])) ==
                plan['frozen'][link['path']] == link['frozen_sha256'], 'symlink inventory differs')
    for p in [Path(__file__).resolve(), Path(__file__).with_name('analyzer.py'),
              Path(__file__).with_name('assess.py')]:
        files[str(p)] = member(p)
    public_validation = None
    for key in set(plan['tools'].values()):
        public_validation = tool_identity(plan, key, custom, frozen_snapshot)
    public_guards = None
    if public_validation and plan['candidate_policy'] in ['host-proc-macro-opt', 'host-library-opt']:
        def guard_snapshot(path):
            item = snapshot(path)
            files[str(path)] = item
            return item
        public_guards = public_screen_guards(plan, rows, original_summary, raw,
                                             public_validation, guard_snapshot)
    if plan['candidate_policy'] == 'cargo-info-cache':
        for cargo in {c.key: c for c in cargos.values()}.values():
            for name, expected_hash in cargo.identity['files'].items():
                path = cargo.directory / 'payload' / name
                if name != 'cargo':
                    item = frozen_snapshot(path)
                    require(item['sha256'] == expected_hash, 'Cargo provenance input differs')
    if plan['candidate_policy'] == 'stable-mono-cgu':
        frozen_snapshot(Path(__file__).with_name('STABLE_MONO_CGU_SCREEN.md'))
    bundle = dict(schema_version=1,
                  encoding='exact UTF-8 or base64 members' if mono_qualification or worker_public else 'exact UTF-8 members',
                  files=list(files.values()),
                  source_symlinks=source_symlinks)
    payload = (json.dumps(bundle, separators=(',', ':'), ensure_ascii=False) + '\n').encode()
    archive = compressed(payload)
    for item in json.loads(gzip.decompress(archive))['files']:
        member_bytes(item)
    summary = dict(original_summary)
    summary.update(project=plan['project'], workflow=plan['workflow'], revision=plan['revision'],
        tools=plan['tools'], binaries=plan['binaries'], cargo_jobs=plan['cargo_jobs'],
        suite_workers=plan['suite_workers'], tests=plan['case']['tests'], states=plan['states'],
        original_source_sha256=plan['original_source_sha256'], compiler=plan['std_mir']['compiler'],
        std_mir=plan['std_mir'], environment_sha256=plan['environment_sha256'],
        command_summaries=compact, cold=[r for r in compact if r['phase'] == 'cold'],
        maximum_aa_cpu_deviation=max(abs(p['aa_cpu_ratio'] - 1) for p in summary['pairs']),
        artifact_inventory=list(artifacts.values()),
        tool_provenance=provenance, source_inventory_entries=len(plan['frozen']),
        archive=dict(path='evidence.json.gz', bytes=len(archive), sha256=sha(archive), gzip_mtime=0,
                     uncompressed_sha256=sha(payload), members=len(files), all_member_hashes_verified=True),
        packager_sha256=sha(Path(__file__).read_bytes()), source_restoration_rechecked=not bool(prior_summary),
        frozen_inventory_verified=True, frozen_inventory_verified_against_current_files=not bool(prior_summary),
        source_snapshot_fallback=identity(args.snapshots_from.resolve()) if prior_summary else None,
        source_symlinks=source_symlinks, archived_source_states=len(expected_states),
        compiler_comparison=plan['compiler_comparison'],
        std_mir_by_mode=plan['std_mir_by_mode'],
        candidate_observations_below_half_second=sum(p['candidate_seconds'] < .5 for p in summary['pairs']),
        adoption='not decided by this single-history mechanism screen', final_latency_gate_qualified=False,
        holdouts_evaluated=False)
    for key in ['custom_compiler', 'cgu_policy_by_mode', 'cargo_comparison', 'cargos_by_mode',
                'proc_macro_policy_by_mode', 'codegen_policy_amendment', 'mono_cgu_policy_by_mode',
                'mono_wrapper', 'compiler_qualification', 'source_observables',
                'frontend_workers_by_mode', 'worker_qualification', 'worker_public_build_policy',
                'worker_capability', 'public_input_guard', 'workload_lock', 'host_library_policy_by_mode',
                'host_library_public_build_policy', 'host_library_capability']:
        if key in plan:summary[key] = plan[key]
    if mono_qualification:
        summary['mono_qualification_assessment'] = mono_qualification
    if public_guards:
        summary['public_input_guard_assessment'] = public_guards
    for pair in summary['pairs']:
        for mode in plan['tools']:
            row = next(r for r in rows if r['index'] == pair['index'] and r['mode'] == mode)
            pair[mode + '_cpu_seconds'] = row['cpu']['total_seconds']
    output = ROOT / 'results' / args.run_id
    output.mkdir(exist_ok=False)
    (output / 'evidence.json.gz').write_bytes(archive)
    require(identity(output / 'evidence.json.gz')['sha256'] == summary['archive']['sha256'],
            'published archive differs')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output / 'assessment.md').write_text(markdown(summary))
    print(json.dumps(dict(output=str(output), archive=summary['archive'], commands=len(rows))))


if __name__ == '__main__':
    main()
