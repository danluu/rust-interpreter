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
import tomllib
from . import adapter

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
BUILT=X/'.work/hir-options-hash-compiler-build-continuation-03'
BHERE=X/'experiments/hir-options-hash/compiler-build-continuation-03'
ORIGINAL_HERE=X/'experiments/hir-options-hash/compiler-build-02'


MAX_FILE_BYTES=2**30
MAX_JSON_BYTES=128*2**20
MAX_TREE_ENTRIES=50000
DISCOVERY=None

def capacity():return adapter.monitor().owned.disk(OWNER,9)
def account(path,size):
    capacity()
    assert 0<=size<=MAX_FILE_BYTES, 'bounded file read required'
    if DISCOVERY is not None:
        DISCOVERY['files'].add(str(path));DISCOVERY['read_bytes']+=size
        assert len(DISCOVERY['files'])<=150000 and DISCOVERY['read_bytes']<=64*2**30,'discovery read bound exceeded'
def read(path):
    path=Path(path);before=stamp(path);assert before[3]<=MAX_JSON_BYTES
    account(path,before[3])
    with path.open('rb') as stream:raw=stream.read(MAX_JSON_BYTES+1)
    assert len(raw)==before[3] and stamp(path)==before, 'JSON changed or exceeded bound'
    return json.loads(raw)
def sha(path):
    path=Path(path);before=stamp(path);account(path,before[3]);digest=hashlib.sha256();size=0
    with path.open('rb') as stream:
        while block:=stream.read(min(8*2**20,MAX_FILE_BYTES-size+1)):
            capacity();size+=len(block);assert size<=MAX_FILE_BYTES;digest.update(block)
    assert size==before[3] and stamp(path)==before,'file changed during bounded hash'
    return digest.hexdigest()
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
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode();assert len(raw)<=MAX_JSON_BYTES;capacity()
    with Path(path).open('xb') as stream:stream.write(raw)
def absent(path):assert not Path(path).exists() and not Path(path).is_symlink(),path


def metadata_module():
    return adapter.metadata()


def completed_build(frozen=None):
    from . import prerequisite
    return prerequisite.completed(frozen)


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
            assert len(result)<MAX_TREE_ENTRIES,'tree entry bound exceeded'
            capacity();path=Path(parent)/name;state=path.lstat();key=str(path.relative_to(root))
            if stat.S_ISLNK(state.st_mode):
                target=path.resolve(strict=True);assert target.is_relative_to(N),path
                result[key]=dict(kind='link',target=os.readlink(path),resolved=str(target),stamp=stamp(path))
            elif stat.S_ISREG(state.st_mode):result[key]=dict(kind='file',**file(path))
            else:assert stat.S_ISDIR(state.st_mode);result[key]=dict(kind='directory')
    return result



def ancestor_guard(full):
    """Keep build02's explicit absent manifests absent as well as binding files."""
    plan=read(ORIGINAL_HERE/'plan.json')
    assert read(BHERE/'plan.json')['ancestor_manifests']==plan['ancestor_manifests']
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
        names=[]
        with os.scandir(path) as values:
            for entry in values:
                assert len(names)<MAX_TREE_ENTRIES,'directory entry bound exceeded'
                if len(names)%256==0:capacity()
                names.append(entry.name)
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
    """Replay the admitted actual ToolBootstrap test producer; no newest glob."""
    modules=adapter.support_modules()
    plan=read(BHERE/'plan.json')
    assert modules.source.derive(S)==plan['support_route']
    inventory=read(BUILT/'run-make-support-inventory.json')
    assert inventory['root']==str(TOOLS) and not inventory['recipe_compiled'] and not inventory['recipe_executed']
    directory=BUILT/'commands/000'
    child=read(directory/'receipt.json')
    assert child['command']==plan['remaining_children'][0]['argv']
    assert child['cwd']==str(S) and child['returncode']==0 and child['status']=='finished'
    assert sum((directory/name).stat().st_size for name in ['stdout','stderr'])<=256*2**20, 'bounded support producer streams required'
    streams={name:(directory/name).read_bytes() for name in ['stdout','stderr']}
    assert all(hashlib.sha256(raw).hexdigest()==child[name+'_sha256'] for name,raw in streams.items())
    proof=modules.producer.validate(streams['stdout'],streams['stderr'],child['environment'],
        tomllib.loads((S/'bootstrap.toml').read_text()),child['command'],S,inventory,
        modules.timing,modules.parsers)
    assert proof==read(BUILT/'run-make-support-producer.json')
    producer=proof['library_producer'];output=Path(producer['output_directory'])
    ordinary(output,True)
    args=producer['parsed']['argv'];source=S/'src/tools/run-make-support/src/lib.rs'
    assert str(source) in args or str(source.relative_to(S)) in args, 'support source differs'
    assert set(modules.parsers.single(args,'--emit').split(','))=={'dep-info','metadata','link'}
    originals={Path(path).suffix:Path(path) for path in producer['artifacts']}
    assert set(originals)=={'.rlib','.rmeta','.dylib'} and len(producer['artifacts'])==3
    for path in originals.values():
        row=inventory['selected'][str(path.relative_to(TOOLS))]
        assert row['kind']=='file' and file(path)=={key:row[key] for key in ['sha256','stamp']}
    stem=originals['.rlib'].name.removeprefix('lib').removesuffix('.rlib')
    depinfo=output/(stem+'.d');ordinary(depinfo)
    assert b'src/tools/run-make-support/src/lib.rs' in depinfo.read_bytes()
    artifacts={}
    for extension in ['rlib','rmeta']:
        source=originals['.'+extension]
        variants=[TOOLS/name for name in inventory['selected'] if name.endswith('.'+extension)]
        assert source in variants
        expected=sha(source)
        assert variants and all(sha(path)==expected for path in variants), 'distinct support variants need separate admission'
        # Bind the actual producer's output, never an unproved newest alias.
        artifacts[extension]=dict(path=str(source),sha256=expected,aliases={str(path):file(path) for path in variants})
    return dict(producer=proof,artifacts=artifacts,depinfo=dict(path=str(depinfo),**file(depinfo)),
        child_receipt=dict(path=str(directory/'receipt.json'),sha256=sha(directory/'receipt.json')),
        inventory_sha256=sha(BUILT/'run-make-support-inventory.json'),
        producer_sha256=sha(BUILT/'run-make-support-producer.json'))


def directory_contract():
    host=ordered_out_dirs(TOOLS/HOST/'release/build')
    dependencies=ordered_out_dirs(TOOLS/'release/build')
    # The second bootstrap enumeration is separate and retains its own order.
    loader=ordered_out_dirs(TOOLS/HOST/'release/build');selected=[];contents={}
    for name in loader['directories']:
        path=Path(name)
        rows=[]
        with os.scandir(path) as entries:
            for entry in entries:
                assert len(rows)<MAX_TREE_ENTRIES,'loader directory entry bound exceeded'
                if len(rows)%256==0:capacity()
                rows.append(entry)
        contents[name]=[row.name for row in rows]
        for row in rows:
            child=path/row.name;s=child.lstat()
            assert child.resolve(strict=True)==child and (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode))
        if any(Path(row.name).suffix=='.dylib' for row in rows):selected.append(name)
    return dict(host=host,dependencies=dependencies,loader=loader,loader_contents=contents,loader_directories=selected)
