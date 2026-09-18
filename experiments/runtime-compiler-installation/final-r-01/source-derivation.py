"""Source-only R proposal derivation; no child processes or runtime inventories."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sys

OWNER = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
HERE = OWNER / 'experiments/runtime-compiler-installation/final-r-01'
OLD = Path('/Users/danluu/dev/rust-interp-runtime-source-qualification-20260913')
META = Path('/Users/danluu/dev/rust-interp-runtime-installation-metadata-20260913')
SOURCE = Path('/Users/danluu/dev/rustc-hir-capture-check-20260913')
WORK = OWNER / '.work/runtime-installation-r-01'
sys.path.insert(0, str(OWNER / 'scripts'))
import runtime_compiler as runtime
import std_mir_source_paths as std


def sha(path):
    path = Path(path)
    assert path.resolve(strict=True) == path and path.is_file() and not path.is_symlink()
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def ref(path):
    return dict(path=str(path), sha256=sha(path))


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


old_plan = read(OLD / 'experiments/runtime-compiler-installation/source-preflight-plan-01.json')
old_freeze = read(OLD / '.work/runtime-source-preflight-source-01/inputs.json')
metadata = read(META / '.work/runtime-installation-inspection-03/receipt.json')
candidate_path = META / '.work/runtime-installation-inspection-03/candidate-specification.json'
assert sha(candidate_path) == '1c0ec4abd1432baa8ba5fe24498af99dd8ae1975a0b3ceece4124409d235de33'
candidate = read(candidate_path)
commit = candidate['provenance']['source_commit']
prior = read(old_plan['evidence']['stage2_plan']['path'])['previous']
review_path = OWNER / 'experiments/stable-cgu/source-paths-review.json'
review = read(review_path)
assert prior['source']['files']['src/tools/cargo'] == dict(kind='gitlink', object=std.CARGO_COMMIT)
assert review['cargo_gitlink_commit'] == std.CARGO_COMMIT
build_dir = Path('/Users/danluu/dev/rust-interp-hir-arena-native-20260913/.work/hir-arena-native-01/stages/native-01/commands/005')
receipt = read(build_dir / 'receipt.json')
assert sha(build_dir / 'receipt.json') == candidate['provenance']['build_receipt_sha256']
assert sha(build_dir / 'stdout') == receipt['stdout_sha256']
rows = []
for index, line in enumerate((build_dir / 'stdout').read_text().splitlines(), 1):
    if line.startswith('running: ') and '__CARGO_RUSTC_BOOTSTRAP_WS_REMAP=' in line:
        tokens = shlex.split(line)
        compiler = f'CFG_VIRTUAL_RUST_SOURCE_BASE_DIR=/rustc/{commit}' in tokens
        expected = [f'-Zroot-dir={SOURCE}', '-Ztrim-paths', "profile.release.trim-paths='all'", "profile.dev.trim-paths='all'",
                    '__CARGO_RUSTC_BOOTSTRAP_WS_REMAP=' + ('/rustc-dev/' if compiler else '/rustc/') + commit]
        if compiler:
            expected += [f'CFG_VIRTUAL_RUST_SOURCE_BASE_DIR=/rustc/{commit}',
                         f'CFG_VIRTUAL_RUSTC_DEV_SOURCE_BASE_DIR=/rustc-dev/{commit}']
        assert all(token in tokens for token in expected)
        rows.append(dict(line=index, sha256=hashlib.sha256(line.encode()).hexdigest(),
                         kind='compiler' if compiler else 'standard-library', required_tokens=expected))
assert len(rows) == 4 and [r['kind'] for r in rows].count('compiler') == 2
unchanged = {}
for relative, digest in review['rust_files'].items():
    if relative in ('compiler/rustc_session/src/config.rs', 'compiler/rustc_session/src/options.rs'):
        continue  # Feature option additions; never relabel as byte-equal.
    current = ref(SOURCE / relative)
    assert current['sha256'] == digest
    assert prior['source']['files'][relative] == dict(kind='file', sha256=digest)
    unchanged[relative] = current
proof = dict(schema_version=1, status='source-only-proposal', source_commit=commit,
    capability=std.source_capability(commit), bootstrap=ref(SOURCE / 'bootstrap.toml'),
    build_receipt=ref(build_dir / 'receipt.json'), build_stdout=ref(build_dir / 'stdout'),
    expanded_commands=rows, cargo_policy_review=ref(review_path), cargo_recipe_files=review['cargo_files'],
    unchanged_remap_sources=unchanged,
    cargo_source_commit_means='Reviewed recipe source pin; no Cargo execution or binary identity is inferred.',
    rustc_dev_source_installation=False, all_diagnostics_qualified=False,
    original_candidate=ref(candidate_path))
assert proof['bootstrap']['sha256'] == candidate['provenance']['bootstrap_sha256']
write(HERE / 'source-policy-proof.json', proof)
refs = dict(old_plan['evidence'])
refs.update(source_preflight=ref(OLD / '.work/runtime-source-preflight-01/receipt.json'),
    source_preflight_outer=ref(OLD / '.work/experiments/runtime-source-preflight-supervisor-01/status.json'),
    source_policy=ref(HERE / 'source-policy-proof.json'))
assert refs['source_preflight']['sha256'] == '8bd341a23550e0d77c0bf7f6472811bb1586cad1af9a214a7be1d5684a7af4dc'
spec = json.loads(json.dumps(candidate))
spec['provenance'].update(std_source_paths=proof['capability'], source_preflight_sha256=refs['source_preflight']['sha256'],
                          source_policy_proof_sha256=refs['source_policy']['sha256'])
spec['prepublication_qualification'] = dict(policy='native-runtime-installed-source-v1')
write(HERE / 'specification.json', spec)
identity = runtime.identity_for(spec)
key = runtime.digest(identity)
sysroot = OWNER / '.work/runtime-compilers' / key / 'sysroot'
env = dict(old_plan['environment'], __CF_USER_TEXT_ENCODING='0x1F5:0x0:0x0')
compiler_env = runtime.RuntimeCompiler(key, sysroot, identity).environment(env)
executors = {}
for kind, path in [('git','/usr/bin/git'),('selection','/usr/bin/xcrun'),('loader','/usr/bin/otool')]:
    p = Path(path)
    executors[kind] = dict(path=path, sha256=sha(p), stamp=runtime.stamp(p.lstat()))
route = dict(metadata['selected_otool'])
assert sha(route['resolved']) == route['sha256']
assert os.readlink(route['selected']) == route['link_text']
assert str(Path(route['selected']).resolve(strict=True)) == route['resolved']
route['link_stamp'] = runtime.stamp(Path(route['selected']).lstat())
route['resolved_stamp'] = runtime.stamp(Path(route['resolved']).lstat())
route['parents'] = {p: runtime.stamp(Path(p).lstat()) for p in route['parents']}
children = []
def add(kind, argv, cwd=OWNER, expected=(0,), out=None):
    index = len(children)
    children.append(dict(kind=kind, argv=argv, cwd=str(cwd), expected=list(expected),
                         out=str(out or WORK / 'commands' / f'{index:03}')))
for row in old_plan['git_commands']:
    add('git',row['argv'],row['cwd'])
add('selection',['/usr/bin/xcrun','--find','otool'])
for name in sorted(spec['loader']):
    add('loader',['/usr/bin/otool','-l',str(sysroot/name)])
for args in [['-vV'],['--print','sysroot'],['-Zhelp']]:
    add('identity',[str(sysroot/'bin/rustc'),*args])
probe = WORK / 'source-probe'
common = [str(sysroot/'bin/rustc'), str(probe/'source.rs'),'--crate-type=lib','--edition=2024',
          '--emit=metadata','--error-format=json','--sysroot',str(sysroot)]
for index, args in enumerate([['-o',str(probe/'local.rmeta')],
    ['-Ztranslate-remapped-path-to-local-path=no','-o',str(probe/'virtual.rmeta')]]):
    add('source',common+args,probe,(1,),probe/'commands'/str(index))
for row in old_plan['git_commands']:
    add('git',row['argv'],row['cwd'])
add('selection',['/usr/bin/xcrun','--find','otool'])
assert len(children) == 28
bounds = dict(runtime_logical_bytes=650879912, runtime_files=3709,
    runtime_block_rounding_bytes=3709*4096, retained_input_bytes=64*2**20,
    receipts_and_diagnostics_bytes=64*2**20, directory_and_metadata_reservation_bytes=128*2**20,
    entry_free_gib=10, active_child_stop_gib=9, running_floor_gib=8)
assert sum(bounds[k] for k in ['runtime_logical_bytes','runtime_block_rounding_bytes','retained_input_bytes',
                              'receipts_and_diagnostics_bytes','directory_and_metadata_reservation_bytes']) < 2**30
plan = dict(schema_version=1,status='prepared-unrun', policy='native-runtime-installation-with-source-prepublication-v1',
    owner=str(OWNER), work=str(WORK), runtime_key=key, sysroot=str(sysroot), canonical_lock=old_plan['canonical_lock'],
    wait_seconds=600, bounds=bounds, environment=env, compiler_environment=compiler_env, executors=executors,
    selected_otool=route, children=children, evidence=refs, guard_script=old_plan['guard_script'],
    guard_inputs=old_plan['guard_inputs'], old_plan_sha256=old_plan['old_plan_sha256'],
    application_qualified=False, benchmark=False, b2_or_pthread_admission_changed=False,
    final_root_source_policy='native-runtime-installed-source-v1',
    immutable_scope='Native runtime with materialized standard sources; no rustc-dev metadata/source or toolset claim.')
write(HERE/'plan.json', plan)
print(json.dumps(dict(key=key, sysroot=str(sysroot), source_policy_sha256=sha(HERE/'source-policy-proof.json'),
                     specification_sha256=sha(HERE/'specification.json'), plan_sha256=sha(HERE/'plan.json')),indent=2))
