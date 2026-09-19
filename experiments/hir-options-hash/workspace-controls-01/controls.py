"""Six offline Cargo metadata controls; caller owns admission and raw receipts.

No compiler build or application edit. Use a fresh sibling fixture outside any
enclosing Cargo workspace so its two explicit fixture workspaces are the only
workspace-discovery inputs. Never alter an existing parent manifest here.
"""
import hashlib
import json
from pathlib import Path
import tomllib


BEFORE = '[workspace]\nmembers = ["member"]\nresolver = "2"\nexclude = [".work/sources/cg-clif", ".work/sources/rg-aot"]\n'
AFTER = '[workspace]\nmembers = ["member"]\nresolver = "2"\nexclude = [".work"]\n'
INNER = '[workspace]\nmembers = ["compiler", "src/build_helper"]\nresolver = "2"\nexclude = ["src/bootstrap"]\n'
LABELS = ['outer-before', 'bootstrap-before', 'outer-after', 'bootstrap-after', 'inner-after', 'outside-work-after']


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(data)


def package(root, name, dependencies=''):
    write(root/'Cargo.toml', '[package]\nname = '+json.dumps(name)+'\nversion = "0.0.0"\nedition = "2024"\n'+dependencies)
    write(root/'src/lib.rs', 'pub fn value() -> u32 { 1 }\n')


def exercise(*, cargo, rustc, work, environment, invoke):
    """invoke(label, argv, cwd, env, expected_rc) returns raw stdout, stderr.

    Require actual passed frozen provider qualification in the caller. Each
    call must retain exact argv/environment/cwd and complete raw output. The
    caller also guards compiler source and providers before and after this
    history. This function does not launch subprocesses itself.
    """
    cargo, rustc, work = map(Path, (cargo, rustc, work))
    assert cargo.is_absolute() and rustc.is_absolute() and work.is_absolute()
    assert not work.exists() and work.parent.resolve(strict=True) == work.parent
    for parent in work.parents:
        assert not (parent/'Cargo.toml').exists(), ('fixture has an unadmitted outer manifest', parent)
    work.mkdir()
    outer = work/'outer'
    inner = outer/'.work/generated/source'
    bootstrap = inner/'src/bootstrap'
    member = outer/'member'
    orphan = outer/'orphan'
    package(member, 'outer_member')
    package(inner/'compiler', 'inner_compiler')
    package(inner/'src/build_helper', 'build_helper')
    package(bootstrap, 'bootstrap', '\n[dependencies]\nbuild_helper = { path = "../build_helper" }\n')
    package(orphan, 'unlisted_orphan')
    write(outer/'Cargo.toml', BEFORE)
    write(inner/'Cargo.toml', INNER)
    write(work/'before-Cargo.toml', BEFORE)
    write(work/'after-Cargo.toml', AFTER)
    (work/'cargo-home').mkdir()
    env = dict(environment, CARGO_NET_OFFLINE='true', CARGO_HOME=str(work/'cargo-home'),
               CARGO_TARGET_DIR=str(work/'target'), RUSTC=str(rustc))
    assert not any(name in env for name in ['RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS'])
    original_sources = {str(p.relative_to(work)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in work.rglob('*') if p.is_file() and p != outer/'Cargo.toml'}
    rows = []

    def call(label, path, expected_root, expected_members=None):
        rc = 101 if expected_root is None else 0
        argv = [str(cargo), 'metadata', '--offline', '--no-deps', '--format-version', '1',
                '--manifest-path', str(path/'Cargo.toml')]
        stdout, stderr = invoke(label, argv, path, env, rc)
        if rc:
            assert not stdout
            text = stderr.decode()
            assert 'current package believes it\'s in a workspace when it\'s not' in text
            assert 'current:   '+str(path/'Cargo.toml') in text
            assert 'workspace: '+str(outer/'Cargo.toml') in text
            result = dict(rejected_by=str(outer/'Cargo.toml'))
        else:
            assert not stderr, stderr
            metadata = json.loads(stdout)
            assert metadata['workspace_root'] == str(expected_root)
            actual = {package['name']: package['manifest_path'] for package in metadata['packages']
                      if package['id'] in metadata['workspace_members']}
            assert actual == {name: str(root/'Cargo.toml') for name, root in expected_members.items()}, actual
            result = dict(workspace_root=metadata['workspace_root'], members=actual)
        rows.append(dict(label=label, expected_returncode=rc, result=result,
                         stdout_sha256=hashlib.sha256(stdout).hexdigest(),
                         stderr_sha256=hashlib.sha256(stderr).hexdigest()))

    call('outer-before', outer, outer, {'outer_member': member})
    call('bootstrap-before', bootstrap, None)
    # The sole mutation is the generated outer fixture's workspace exclusion.
    # Before/after bytes are separate retained files. Compiler inputs are fixed.
    assert (outer/'Cargo.toml').read_text() == BEFORE
    (outer/'Cargo.toml').write_text(AFTER)
    call('outer-after', outer, outer, {'outer_member': member})
    call('bootstrap-after', bootstrap, bootstrap, {'bootstrap': bootstrap})
    call('inner-after', inner, inner, {'inner_compiler': inner/'compiler', 'build_helper': inner/'src/build_helper'})
    call('outside-work-after', orphan, None)
    assert [row['label'] for row in rows] == LABELS
    assert (outer/'Cargo.toml').read_text() == AFTER
    for name, digest in original_sources.items():
        assert hashlib.sha256((work/name).read_bytes()).hexdigest() == digest, name
    assert not (work/'target').exists(), 'metadata control unexpectedly created compiler output'
    return dict(status='passed', metadata_commands=6, compiler_builds=0,
                candidate_workspace=tomllib.loads(AFTER)['workspace'], rows=rows)
