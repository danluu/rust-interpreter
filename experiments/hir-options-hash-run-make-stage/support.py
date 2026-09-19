"""Source-bound, read-only discovery for a future direct run-make stage."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import producer as actual_producer

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[1]
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
N=X/'.work/hir-options-hash-compiler-01'
S=N/'source'
HOST='aarch64-apple-darwin'
BUILD=S/'build'/HOST
D2=BUILD/'stage0'
E2=BUILD/'stage1'
TOOLS=BUILD/'bootstrap-tools'
BASE=N/'run-make-01'
OUT=BASE/'rmake_out'
WORK=OWNER/'.work/hir-options-hash-run-make-01'
BUILT=X/'.work/hir-options-hash-compiler-build-02'
BHERE=X/'experiments/hir-options-hash/compiler-build-02'


def read(path):return json.loads(Path(path).read_bytes())
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def stamp(path):
    s=Path(path).lstat()
    return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
def ordinary(path,directory=False):
    p=Path(path);s=p.lstat()
    assert p.resolve(strict=True)==p and (stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode)),p
    return s
def file(path):
    ordinary(path);before=stamp(path);digest=sha(path);assert stamp(path)==before
    return dict(sha256=digest,stamp=before)
def write(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')
def absent(path):assert not Path(path).exists() and not Path(path).is_symlink(),path


def build_module():
    sys.path.insert(0,str(BHERE))
    spec=importlib.util.spec_from_file_location('qualified_run_make_build',BHERE/'build.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


def source_guard():
    proof=read(HERE/'source-bindings.json')
    assert proof['candidate_commit']=='4de35bdacef0e3cd18a66bc30b5459c19e09b118'
    for row in proof['source_files']:
        path=S/row['path'];ordinary(path)
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],path
    fixture=S/'tests/run-make/hir-body-cache-capture'
    assert sorted(p.name for p in fixture.iterdir())==proof['fixture_members']
    for name,row in read(HERE/'source-supplement.json')['files'].items():
        path=S/name;ordinary(path)
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],path
    return proof


def inventory(root):
    """Full file/link membership, without interpreting directory ctime as data."""
    ordinary(root,True);result={}
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            path=Path(parent)/name;state=path.lstat();key=str(path.relative_to(root))
            if stat.S_ISLNK(state.st_mode):
                target=path.resolve(strict=True);assert target.is_relative_to(N),path
                result[key]=dict(kind='link',target=os.readlink(path),resolved=str(target),stamp=stamp(path))
            elif stat.S_ISREG(state.st_mode):result[key]=dict(kind='file',**file(path))
            else:assert stat.S_ISDIR(state.st_mode);result[key]=dict(kind='directory')
    return result


def completed_build():
    terminal=read(BUILT/'receipt.json');compiled=read(BUILT/'compiled.json');plan=read(BHERE/'plan.json')
    assert terminal['status']=='passed' and terminal['compiler_stages_completed']==compiled['stages']==8
    assert compiled['status']=='compiled-awaiting-native-recipe-and-B3-qualification'
    assert terminal['compiled_sha256']==sha(BUILT/'compiled.json')
    assert compiled['candidate_revision']==plan['candidate_revision']=='4de35bdacef0e3cd18a66bc30b5459c19e09b118'
    assert compiled['source_identity']==plan['source_identity'] and compiled['all_lowering_tests']==27 and compiled['all_interface_tests']==18
    assert len(terminal['commands'])==len(plan['children'])==25
    previous=terminal['admitted_at']
    for index,(actual,expected) in enumerate(zip(terminal['commands'],plan['children'],strict=True)):
        directory=BUILT/'commands'/f'{index:03}';child=read(directory/'receipt.json')
        assert actual['path']==str(directory/'receipt.json') and actual['sha256']==sha(directory/'receipt.json')
        assert child['command']==actual['command']==expected['argv'] and child['cwd']==str(S)
        assert child['environment']==expected['environment'] and child['status']=='finished' and child['returncode']==0
        assert actual['pid']==child['pid'] and child['supervisor_pid']==terminal['pid']
        assert previous<=child['started_at']<=child['finished_at']<=terminal['finished_at'];previous=child['finished_at']
        for stream in ['stdout','stderr']:assert sha(directory/stream)==child[stream+'_sha256']
    for name,key in [('stage1-native-loader.json','native_loader_sha256'),('run-make-support-inventory.json','run_make_support_sha256')]:
        assert sha(BUILT/name)==compiled[key]
    return terminal,compiled,plan


def ancestor_guard(full):
    """Keep build02's explicit absent manifests absent as well as binding files."""
    plan=read(BHERE/'plan.json')
    for name,expected in plan['ancestor_manifests'].items():
        path=Path(name);assert not path.is_symlink(),name
        if expected is None:assert not path.exists(),name
        else:
            assert path.resolve(strict=True)==path and path.is_file() and stamp(path)==expected['stamp'],name
            if full:assert sha(path)==expected['sha256'],name


def ordered_out_dirs(root):
    """The exact three read_dir layers; retain order, never rglob or sort it."""
    ordinary(root,True);listings={};selected=[]
    def entries(path):
        ordinary(path,True)
        before=stamp(path)
        with os.scandir(path) as values: names=[entry.name for entry in values]
        assert stamp(path)==before
        listings[str(path)]=dict(names=names,stamp=before)
        paths=[]
        for name in names:
            child=path/name;value=child.lstat()
            assert child.resolve(strict=True)==child and (stat.S_ISDIR(value.st_mode) or stat.S_ISREG(value.st_mode)),child
            paths.append(child)
        return paths
    for package in entries(root):
        if not package.is_dir():continue
        for unit in entries(package):
            if not unit.is_dir():continue
            for candidate in entries(unit):
                if candidate.name=='out':ordinary(candidate,True);selected.append(str(candidate))
    return dict(root=str(root),directories=selected,listings=listings)


def discover_support():
    """Bind the sole actual support producer; never pick a newest glob."""
    inventory=read(BUILT/'run-make-support-inventory.json')
    assert inventory['root']==str(TOOLS)
    child=read(BUILT/'commands/022/receipt.json')
    streams={name:(BUILT/'commands/022'/name).read_bytes() for name in ['stdout','stderr']}
    cargo_catalog=[];running=[]
    for name,raw in streams.items():
        assert hashlib.sha256(raw).hexdigest()==child[name+'_sha256']
        for number,line in enumerate(raw.splitlines(keepends=True),1):
            coord=dict(stream=name,line=number,line_sha256=hashlib.sha256(line).hexdigest())
            if line.startswith(b'running: ') and b'CARGO_TARGET_DIR=' in line:
                cargo=actual_producer.bootstrap_line(raw,coord,S)
                if cargo['environment'].get('CARGO_TARGET_DIR')==str(TOOLS):
                    cargo_catalog.append(dict(coordinate=coord,parsed=cargo))
            if b'--crate-name run_make_support ' in line and line.strip().startswith(b'Running `'):
                running.append((coord,actual_producer.running_line(raw,coord)))
    assert cargo_catalog,'missing actual bootstrap-tool Cargo context'
    matches=[]
    for coordinate,row in running:
        tokens=row['argv'];position=tokens.index('--crate-name')
        assert tokens[position+1]=='run_make_support'
        args=tokens[position:]
        effective=actual_producer.unambiguous_environment(row,
            [dict(cargo=entry['parsed'],inherited=child['environment']) for entry in cargo_catalog],S)
        def value(flag):assert args.count(flag)==1;return args[args.index(flag)+1]
        crate_types=[args[i+1] for i,x in enumerate(args) if x=='--crate-type']
        assert crate_types==['lib','dylib'] and value('--target')==HOST
        source=S/'src/tools/run-make-support/src/lib.rs'
        assert str(source) in args or str(source.relative_to(S)) in args, 'support source differs'
        out=Path(value('--out-dir'));ordinary(out,True);assert out.is_relative_to(TOOLS)
        extras=[arg.removeprefix('extra-filename=') for arg in args if arg.startswith('extra-filename=')]
        assert len(extras)==1 and re.fullmatch(r'-[0-9a-f]+',extras[0])
        stem='run_make_support'+extras[0]
        rlib=out/('lib'+stem+'.rlib');depinfo=out/(stem+'.d')
        # Separate-metadata builds may place the rmeta in another directory.
        # Every matching producer stem must have the same bytes; no mtime pick.
        metadata=[TOOLS/name for name in inventory['selected'] if Path(name).name=='lib'+stem+'.rmeta']
        assert not metadata or len({sha(path) for path in metadata})==1
        rmeta=(out/('lib'+stem+'.rmeta') if out/('lib'+stem+'.rmeta') in metadata else metadata[0]) if metadata else None
        ordinary(rlib);ordinary(depinfo)
        assert b'src/tools/run-make-support/src/lib.rs' in depinfo.read_bytes()
        matches.append(dict(coordinate=coordinate,parsed=row,argv=tokens,cargo_catalog=cargo_catalog,
            effective_environment=effective,child_receipt_sha256=sha(BUILT/'commands/022/receipt.json'),
            out=str(out),rlib=str(rlib),rmeta=str(rmeta) if rmeta else None,depinfo=str(depinfo)))
    assert len(matches)==1, 'missing or ambiguous actual support rustc command'
    producer=matches[0];artifacts={}
    for extension in ['rlib','rmeta']:
        original=producer[extension]
        variants=[TOOLS/name for name in inventory['selected'] if name.endswith('.'+extension)]
        if original is None:assert not variants;continue
        source=Path(original);assert source in variants
        expected=sha(source)
        assert variants and all(sha(path)==expected for path in variants), 'distinct support variants require explicit producer discovery'
        top=TOOLS/HOST/'release'/('librun_make_support.'+extension)
        chosen=top if top in variants else source
        artifacts[extension]=dict(path=str(chosen),sha256=expected,aliases={str(path):file(path) for path in variants})
    return dict(producer=producer,artifacts=artifacts,depinfo=file(Path(producer['depinfo'])),inventory_sha256=sha(BUILT/'run-make-support-inventory.json'))


def directory_contract():
    host=ordered_out_dirs(TOOLS/HOST/'release/build')
    dependencies=ordered_out_dirs(TOOLS/'release/build')
    # The second bootstrap enumeration is separate and retains its own order.
    loader=ordered_out_dirs(TOOLS/HOST/'release/build');selected=[];contents={}
    for name in loader['directories']:
        path=Path(name)
        with os.scandir(path) as entries:rows=list(entries)
        contents[name]=[row.name for row in rows]
        for row in rows:
            child=path/row.name;s=child.lstat()
            assert child.resolve(strict=True)==child and (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode))
        if any(Path(row.name).suffix=='.dylib' for row in rows):selected.append(name)
    return dict(host=host,dependencies=dependencies,loader=loader,loader_contents=contents,loader_directories=selected)
