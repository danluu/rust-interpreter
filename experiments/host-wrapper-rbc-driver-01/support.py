"""Finite saved binding and ordinary runtime/tool/std readers for this fixture."""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
H=ROOT/'experiments/host-wrapper-opt-01'
F=ROOT/'experiments/host-wrapper-exporter-01'
FIXTURE=ROOT/'experiments/host-wrapper-rbc-fixture-01/test_host_codegen_native.py'
WORK=ROOT/'.work/host-wrapper-rbc-fixture-01'
OUT=ROOT/'results/host-wrapper-rbc-fixture-01'
EXECUTION=ROOT/'.work/host-wrapper-rbc-execution-01'
LOCK=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
RUNTIME_KEY='f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70'
STD_KEY='f6366b5873636f47cdc3e9941a9b24ef612f94432baecb5d75ed5c4c54911928'
TESTS=('test_cargo_shared_library_macro_input_spans_error_and_restoration',
 'test_macro_cfg_debug_and_overflow_checks','test_native_debug_overflow_ub_cfg_generics_inline_and_drop_effects',
 'test_uncalled_macro_errors_and_restoration','test_uncalled_type_borrow_const_and_position_changes_reject_then_restore')


KNOWN_SAVED_PINS = {'/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/.work/runtime-compilers/f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70/ready.json': '115674c2737014d614a2334d62444ea684406042649ffe1d03c6d322ac937c5b', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/.work/std-mir/f6366b5873636f47cdc3e9941a9b24ef612f94432baecb5d75ed5c4c54911928/ready.json': 'beaa429fe14fdbc4619ba9072712a5ffd85c1de7185bede7a6a7b303abf968f9', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-std-after-installation07-01/launch.json': '91313c000f00a68929e0ef137286d707a7e2c4d5dddc84c64cb52d9374a29157', '/Users/danluu/dev/rust-interp-runtime-installation-r-20260918/.work/hir-options-hash-runtime-installation-independent-verification-07.json': '878a1f363e6ca5e3acdcb16645c79d8412a260e8721a9fe75eacd7823a481728', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/runtime13-saved-audit-installation-execution-01/record.json': '1f4d4a70657aa071fb85540f97b8ecbfeed3dcde85e340360b5065e7a3ed7d43', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/runtime-std07-closed-root-readback-01.json': 'f8486fc4b7b3620ee9278494c523b03ca50b92d5531736a3a00ed946c7dd7b01', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/host-wrapper-opt-fixture-02/binding.json': '001fbd0522facab8eb2423ca534b434177e4076f38d14ffd771ea08ed8dcf370', '/Users/danluu/dev/rust-interp-semantic-reuse-20260913/results/host-wrapper-opt-fixture-02/result.json': '5028027634eb73faf46d399f33fa2669395c7a6201f58115f05cd1cdddcddd6b'}


def require(ok,message):
    if not ok:raise RuntimeError(message)


def valid_key(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def file(path,expected=None):
    p=Path(path);s=p.lstat();fields=('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns','st_nlink')
    require(p.is_absolute() and p.resolve(strict=True)==p and stat.S_ISREG(s.st_mode),'canonical ordinary file required: '+str(p))
    h=hashlib.sha256();length=0
    with p.open('rb') as stream:
        while block:=stream.read(2**20):length+=len(block);h.update(block)
    t=p.lstat();require(length==s.st_size and all(getattr(s,n)==getattr(t,n) for n in fields),'file changed: '+str(p))
    require(expected is None or h.hexdigest()==expected,'file SHA differs: '+str(p))
    return dict(path=str(p),sha256=h.hexdigest(),bytes=length,identity=[getattr(s,n) for n in fields])


def read(path,expected=None):
    ref=file(path,expected);require(ref['bytes']<=16*2**20,'bounded metadata exceeded')
    data=Path(path).read_bytes();require(hashlib.sha256(data).hexdigest()==ref['sha256'],'metadata changed')
    return json.loads(data)


def write(path,value):
    data=(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    temporary=path.with_name('.'+path.name+'.write')
    with temporary.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)


def source_paths():
    paths={HERE/n for n in ('support.py','bind.py','run.py','suite.py','execute.py')}
    paths|={FIXTURE,F/'common.py',H/'host_codegen_opt.py',ROOT/'experiments/runtime-native-loader-probes-01/runtime_compiler.py',R/'experiments/stable-cgu/owned_stage.py'}
    paths|={R/'scripts'/(n+'.py') for n in ('custom_compiler','workflow_io','toolchain_lookup','runtime_tools','custom_cargo_libraries','workspace_cache','interpreter','std_mir','std_mir_source_paths','compare_saved_runtime','host_library_opt')}
    paths|={R/'tests'/(n+'.py') for n in ('test_host_library_native','test_host_proc_macro_native','test_borrowck_cache')}
    return paths


def binding(path,digest,tool_key):
    value=read(path,digest)
    require(value['policy']=='host-wrapper-rbc-binding-v1' and value['tool_key']==tool_key and valid_key(tool_key),'bound new tool key required')
    require(value['runtime_key']==RUNTIME_KEY and value['std_key']==STD_KEY,'fixed qualified runtime/std required')
    require(all(value['evidence'].get(p)==h for p,h in KNOWN_SAVED_PINS.items()),'qualified saved proof pins differ')
    require(set(value['sources'])=={str(p) for p in source_paths()},'complete exact dynamic source closure required')
    for p,h in value['sources'].items():file(p,h)
    return value


def load(path,name):
    require(name not in sys.modules,'unexpected preloaded fixture module: '+name)
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module


@contextmanager
def environment(values):
    previous=dict(os.environ);os.environ.clear();os.environ.update(values)
    try:yield
    finally:os.environ.clear();os.environ.update(previous)


@contextmanager
def readers(sources):
    common=load(F/'common.py','_rbc_common');mods=common.modules(sources)
    with common.aliases(mods.public):
        cache=load(R/'scripts/workspace_cache.py','_rbc_workspace_cache')
        std=load(R/'scripts/std_mir.py','_rbc_std_mir')
        compare=load(R/'scripts/compare_saved_runtime.py','_rbc_compare')
        with common.aliases(dict(workspace_cache=cache,std_mir=std,compare_saved_runtime=compare)):
            interpreter=load(R/'scripts/interpreter.py','_rbc_interpreter')
            stdpaths=load(R/'scripts/std_mir_source_paths.py','_rbc_stdpaths')
            helper=load(H/'host_codegen_opt.py','_rbc_host_policy')
            require(interpreter.ROOT==R,'ordinary reader lost original R root')
            yield common,mods,interpreter,stdpaths,helper


def authenticate(value,modules):
    common,mods,interpreter,stdpaths,helper=modules
    sources={p:file(p,h) for p,h in value['sources'].items()}
    evidence={p:file(p,h) for p,h in value['evidence'].items()}
    runtime_ready=read(R/'.work/runtime-compilers'/RUNTIME_KEY/'ready.json')
    std_ready=read(R/'.work/std-mir'/STD_KEY/'ready.json')
    directory=R/'.work/interpreter-tools'/value['tool_key']
    expected={str(directory/n):h for n,h in read(directory/'ready.json').items()}
    for root,files in [(R/'.work/runtime-compilers'/RUNTIME_KEY/'sysroot',runtime_ready['identity']['files']),
        (R/'.work/std-mir'/STD_KEY/'sysroot',std_ready['sysroot_files']),
        (R/'.work/std-mir'/STD_KEY/'library',std_ready['identity']['source_files']),
        (R/'.work/std-mir'/STD_KEY/'evidence',std_ready['evidence_files'])]:
        expected.update({str(root/n):h for n,h in files.items()})
    cargo=std_ready['identity']['cargo'];expected[cargo['executable']]=cargo['sha256']
    require(expected==value['payloads'],'complete runtime/std/tool/Cargo payload inventory differs')
    payloads={p:file(p,h) for p,h in expected.items()}
    compiler=mods.runtime.load_runtime_compiler(R,RUNTIME_KEY)
    directory,key=interpreter.installed_tools(value['tool_key'])
    require(directory==R/'.work/interpreter-tools'/key,'installed tool route differs')
    caps=read(directory/'capabilities.json');binaries=read(directory/'ready.json')
    receipt=helper.require_capability(directory,key,compiler,caps,binaries)
    sysroot,host,key,ready=stdpaths.load(R,STD_KEY,compiler,'immutable-source-paths-v2:shared',rehash=False)
    require(host=='aarch64-apple-darwin' and str(sysroot)==value['std_sysroot'],'prepared std association differs')
    require(value['cargo']==ready['identity']['cargo']['executable'],'explicit pinned Cargo differs')
    require(set(common.tree(directory))==set(binaries)|{'compiler.json','capabilities.json','ready.json'},'installed tool membership differs')
    return dict(sources=sources,evidence=evidence,payloads=payloads,capability=receipt),compiler,sysroot


def footprint():
    logical=allocated=entries=0
    for root in (WORK,OUT,EXECUTION):
        if not root.exists():continue
        for parent,dirs,files in os.walk(root,followlinks=False):
            for name in dirs+files:
                p=Path(parent)/name;s=p.lstat();entries+=1
                require(entries<=65536,'owned entry bound65536 exceeded')
                require(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode),'unexpected owned file kind')
                if stat.S_ISREG(s.st_mode):logical+=s.st_size;allocated+=s.st_blocks*512
    return dict(logical_bytes=logical,allocated_bytes=allocated,entries=entries)


def configuration_absent():
    for directory in (WORK,*WORK.parents):
        for name in ('config','config.toml'):
            require(not os.path.lexists(directory/'.cargo'/name),'ambient fixture ancestor Cargo configuration')
