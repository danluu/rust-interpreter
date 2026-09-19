#!/opt/homebrew/bin/python3 -B
"""Bind existing qualified tools and completed source copies; never build or probe."""
import hashlib
import json
from pathlib import Path
import stat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
H = ROOT/'experiments/host-wrapper-opt-01'
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
R = Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')


def digest(path):
    path = Path(path)
    before = path.stat()
    assert path.is_absolute() and stat.S_ISREG(before.st_mode)
    result = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(2**20):
            result.update(block)
    assert path.stat() == before
    return result.hexdigest()


def main():
    out = HERE/'binding.json'
    assert not out.exists()
    manifest = H/'wrapper-sources.json'
    assert digest(manifest) == '79339f177fcb9b9936e91c2863349ffda07940fafa5bd3cfe08f1be955e059b2'
    wrapper_sources = json.loads(manifest.read_text())['files']
    built_path = X/'.work/hir-options-hash-exporter-build-02/built-tools.json'
    assert digest(built_path) == '96322038c5c10a88fc3461129bdc87a4930d984db612b19a08812673e85d2fa0'
    built = json.loads(built_path.read_text())
    roles = built['compiler_roles']
    generated, = built['generated']
    assert digest(generated['path']) == generated['sha256']
    private_path = Path(roles['private_sysroot_manifest']['path'])
    assert digest(private_path) == roles['private_sysroot_manifest']['sha256']
    private = json.loads(private_path.read_text())
    assert private['runtime_source_commit'] == roles['runtime_source_commit']
    assert private['build_compiler_sha256'] == roles['build']['executable']['sha256']
    sources = {str(manifest):digest(manifest),str(built_path):digest(built_path),
        str(private_path):digest(private_path),generated['path']:generated['sha256']}
    for row in wrapper_sources.values():
        assert digest(row['path']) == row['sha256']
        sources[row['path']] = row['sha256']
    for rel, expected in private['files'].items():
        path = Path(private['sysroot'])/rel
        assert path.is_relative_to(private['sysroot']) and not path.is_symlink()
        assert digest(path) == expected
        sources[str(path)] = expected
    originals = ROOT/'experiments/host-build-opt-01'
    old_sources_path = originals/'qualification-sources-02.json'
    old_sources = json.loads(old_sources_path.read_text())['files']
    named = [HERE/'qualify.py',HERE/'capture.py',HERE/'prepare_binding.py',HERE/'README.md',
        originals/'qualify-fixture-02.py',R/'scripts/workflow_io.py',R/'scripts/workflow_controls.py',
        old_sources_path,ROOT/'results/host-build-opt-fixture-02/cargo-version/stdout',
        ROOT/'results/host-build-opt-fixture-02/tools-before.json']
    named.extend(p for p in (originals/'qualification-fixture').rglob('*') if p.is_file())
    for path in named:
        assert not path.is_symlink()
        sha = digest(path)
        if str(path) in old_sources:
            assert sha == old_sources[str(path)]
        sources[str(path)] = sha
    old_tools = json.loads((ROOT/'results/host-build-opt-fixture-02/tools-before.json').read_text())
    cargo = old_tools['cargo']
    assert digest(cargo['resolved']) == cargo['sha256']
    tools = {cargo['resolved']:cargo['sha256']}
    for row in [roles['build']['executable'],roles['runtime']['executable'],roles['runtime_driver']]:
        assert digest(row['path']) == row['sha256']
        tools[row['path']] = row['sha256']
    linkers = [arg.partition('=')[2] for arg in roles['build_rustflags'] if arg.startswith('-Clinker=')]
    assert len(linkers) == 1
    tools[linkers[0]] = digest(linkers[0])
    binding = dict(schema_version=1,policy='host-codegen-opt-v1',sources=sources,tools=tools,
        compiler_roles=roles,generated_roles=generated['path'],build_sysroot=private['sysroot'],
        wrapper_main=wrapper_sources['wrapper_main.rs']['path'],cargo=cargo['resolved'],
        cargo_version=(ROOT/'results/host-build-opt-fixture-02/cargo-version/stdout').read_text(),
        capability=dict(schema_version=1,policy='host-codegen-opt-v1',
            roles=['proc-macro','lib','rlib'],opt_level=3,mir_opt_level=1,lto='off',preserve_checks=True),
        status='bound-unrun-native-fixture',benchmark=False,bytecode_qualified=False,
        process_calls=0,held_sources_unchanged=True)
    payload = (json.dumps(binding,sort_keys=True,indent=2)+'\n').encode()
    with out.open('xb') as stream:
        stream.write(payload)
    print(json.dumps(dict(binding=str(out),sha256=hashlib.sha256(payload).hexdigest(),
        source_files=len(sources),tool_files=len(tools),bytes=len(payload),process_calls=0)))


if __name__ == '__main__':
    main()
