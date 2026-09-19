"""Retain a finite saved-metadata build/recipe route, without provider reads."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
N = X / '.work/hir-options-hash-compiler-01'
S = N / 'source'
HOST = 'aarch64-apple-darwin'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, value):
    with (HERE / name).open('xb') as out:
        out.write(value if isinstance(value, bytes) else
            (json.dumps(value, sort_keys=True, indent=2) + '\n').encode())


def main():
    assert sys.dont_write_bytecode and not sys.flags.optimize
    refs = {}

    def read(path):
        path = Path(path)
        assert not path.is_symlink() and path.is_file()
        data = path.read_bytes()
        refs[str(path)] = dict(path=str(path), sha256=sha(data), bytes=len(data))
        return data

    def document(path):
        return json.loads(read(path))

    resource_path = X / '.work/hir-probe-single-walk-saved-compiler-build-resource-route-01.json'
    resource_bytes = read(resource_path)
    assert sha(resource_bytes) == '323b15dd1d65b7b5dcd5122628bace04f7f5ec334dc527dfcffe7deb4332fc7d'
    resources = json.loads(resource_bytes)
    write('saved-build-resources.json', resource_bytes)
    original_build = X / 'experiments/hir-options-hash/compiler-build-02/plan.json'
    build = document(original_build)
    metadata_path = X / 'experiments/hir-options-hash/compiler-metadata-03/plan.json'
    metadata = document(metadata_path)
    assert metadata['candidate_revision'] == build['candidate_revision'] == resources['candidate_revision']
    recipe_path = O / 'experiments/hir-options-hash-run-make-stage-02/plan.json'
    recipe = document(recipe_path)
    assert refs[str(recipe_path)]['sha256'] == '0b8e7e2eddded33a8a6fc6eaf284e6de65e57a8057fa235d08afa1d33d51b5dc'
    work = O / '.work/hir-options-hash-run-make-01'
    result = document(work / 'result.json')
    terminal = document(work / 'receipt.json')
    assert result['status'] == terminal['status'] == 'passed'
    assert terminal['result_sha256'] == refs[str(work / 'result.json')]['sha256']
    assert result['plan_sha256'] == refs[str(recipe_path)]['sha256']
    assert result['native_recipe_qualified'] is True and result['nested_commands'] == 230
    assert len(result['actual_commands']) == len(recipe['children']) == 2
    for row, ref in zip(recipe['children'], result['actual_commands'], strict=True):
        child = document(ref['path'])
        assert refs[ref['path']]['sha256'] == ref['sha256']
        assert child['status'] == 'finished' and child['returncode'] == 0
        assert child['command'] == row['argv'] and child['environment'] == row['environment'] and child['cwd'] == row['cwd']
    recipe_refs = {name: value for name, value in refs.items() if name.startswith(str(O))}
    write('historical-recipe.json', dict(status='saved-passed-route-only',
        children=recipe['children'], references=recipe_refs,
        limitation='Saved command associations only; no present provider bytes, future compiler identity or new qualification is asserted.'))
    comparison = document(HERE / 'source-comparison.json')
    performance = document(ROOT / 'experiments/hir-probe-single-walk-01/source-comparison.json')
    config = read(S / 'bootstrap.toml')
    assert sha(config) == build['tests']['source_files'][str(S / 'bootstrap.toml')]
    write('bootstrap.toml', config)
    variants = {}
    for variant, source_proof in [('audit', comparison), ('performance', performance)]:
        namespace = X / f'.work/hir-probe-single-walk-{variant}-compiler-01'
        source = namespace / 'source'
        env = {key: value.replace(str(N), str(namespace)) for key, value in build['environment'].items()}
        stages = []
        # The support library is D2-produced and unchanged: reuse its actual
        # provider after revalidation; never repeat the known-invalid build verb.
        for row in build['stages'][:7]:
            stages.append(dict(argv=[value.replace(str(N), str(namespace)) for value in row['argv']],
                cwd=str(source), environment=env))
        # Keep only test-name/source expectations. Historical version assertions
        # contain the old commit and must never masquerade as new-build pins.
        expected = json.loads(json.dumps({key: build['tests'][key]
            for key in ['source_files', 'lowering', 'interface']}))
        expected['source_revision'] = None  # set only from the new actual source commit
        expected['source_files'] = {name.replace(str(S), str(source)): digest
            for name, digest in expected['source_files'].items()}
        expected['source_files'][str(source / 'compiler/rustc_ast_lowering/src/body_cache/mod.rs')] = (
            source_proof['audit_hashes'] if variant == 'audit' else source_proof['candidate_hashes'])[
                'compiler/rustc_ast_lowering/src/body_cache/mod.rs']
        variants[variant] = dict(namespace=str(namespace), source=str(source),
            target=str(source / 'build'), cargo_home=str(namespace / 'cargo-home'),
            source_identity=source_proof['source_identity'], source_commit=None,
            source_overlay=str(HERE / 'candidate') if variant == 'audit' else str(ROOT / 'experiments/hir-probe-single-walk-01/candidate'),
            stages=stages, source_test_expectations=expected,
            actual_build=None, actual_native_identity=None, actual_qualification=None)
    seeds = {}
    for name, row in metadata['seeds'].items():
        if row['active']:
            assert row['component'] and row['output_root']
        seeds[name] = dict(sha256=row['sha256'], active=row['active'],
            component=row.get('component'), output_root=row.get('output_root'),
            members=len(row['members']))
    route = dict(status='source-only-unprepared-unrun', variants=variants,
        source_base_revision=build['candidate_revision'], current_N_immutable=True,
        source_materialization='Fresh local snapshot of the pinned source commit and its qualified submodule closure, then exactly three overlay files, a new local source commit and its actual observed revision. No old source/build/cache inode is writable through the new tree.',
        seed_policy='Independently copy the admitted active archives and private Cargo inputs into each fresh namespace; retained D2/support providers may only be read by the direct recipe. Revalidate archive contents/stamps and block all network/LLVM source-build paths using the existing metadata guards.',
        seeds=seeds, llvm=metadata['llvm'],
        canonical_lock=build['canonical_lock'], wait_seconds=600, capacity=build['capacity'],
        scheduling='Audit first; performance only after audit qualification and a separate capacity check. No overlapping builds, implicit cleanup or reuse of old mutable targets.',
        reused_sources=[str(X / 'experiments/hir-options-hash/compiler-build-continuation-03/bounded_command_v2.py'),
            str(O / 'experiments/hir-options-hash-run-make-stage-02/bounded_recipe.py'),
            str(O / 'experiments/hir-options-hash-run-make-stage-02/prepare.py'),
            str(O / 'experiments/hir-options-hash-run-make-stage-02/run.py')],
        prerequisites=[
            'Review the current source/audit deltas and complete the fresh source/seed membership and allocation projection before materialization.',
            'Keep inherited ancestor Cargo/config/SDK/source/provider guards. X .work exclusion must be checked, not assumed from the old pass.',
            'Freeze the actual new source commit, full source and provider inputs. Record source_identity separately; no old version override or old compiler claim.',
            'Bind the existing monitor to only the fresh namespace and finite evidence roots; retain 24/14/256/9/8 bounds and one canonical owner with normal parent wait.',
            'Run the ordinary lowering check, 27 lowering tests, compiler/library build, identity/sysroot/help and 18 interface tests; source-derive full names using current_compiler_test_source.py and exact future hashes.',
            'Authenticate current D2/support and the new audit stage1 native closure, then prepare the two rendered recipe rows and copy all 12 non-runner fixtures into the fresh rmake_out directory.',
            'Require actual complete unfiltered diagnostics, gate messages, original 230-call history and all added real-AST cases. Retain a failed qualification without dropping cases or automatic retries.',
            'After audit success, build and qualify the distinct performance compiler with the unchanged ordinary run-make and strict application controls before any measurement.'
        ], resource_assessment=refs[str(resource_path)],
        measurement_limits=resources['limitations'],
        all_future_artifact_pins_unset=True, compiler_builds=0, tests_run=0,
        dependency_references=refs,
        remaining_implementation='The existing bounded build/native preparers need their finite current-input and fresh-route binding after source review. This document and the command renderer are not a frozen executable admission packet.')
    write('build-route.json', route)
    assert all(sha(Path(path).read_bytes()) == row['sha256'] for path, row in refs.items())
    print(json.dumps(dict(status=route['status'], saved_recipe_children=2,
        variants=list(variants), metadata_references=len(refs),
        prior_sampled_namespace_peak=resources['allocation']['maximum_sampled_namespace_allocated_bytes']), indent=2))


if __name__ == '__main__':
    main()
