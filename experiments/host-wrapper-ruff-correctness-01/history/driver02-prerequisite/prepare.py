#!/usr/bin/env python3
"""Prepare one correctness-only history from actual publication and five-test RBC proofs."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
R=Path('/Users/danluu/dev/rust-interp-runtime-installation-r-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
H=ROOT/'experiments/host-wrapper-opt-01'
F=ROOT/'experiments/host-wrapper-exporter-01'
RBC=ROOT/'experiments/host-wrapper-rbc-driver-02'
OWNED=A/'experiments/stable-cgu/owned_stage.py'
SUPERVISOR=R/'scripts/supervise_experiment.py'
LOCK=Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock')
PACKET=HERE/'packet-01'
NAME='host-wrapper-ruff-correctness-01'
RUNTIME='f031d981666f450f760ccf303dccba986053ec6b9a143a60f3d26680f9ac7c70'
STD='f6366b5873636f47cdc3e9941a9b24ef612f94432baecb5d75ed5c4c54911928'
GIB=2**30
MIB=2**20


def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def stamp(path):
    s = Path(path).lstat()
    return [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]

def data(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path, 'indirect input: ' + str(path))
    before = stamp(path)
    require(stat.S_ISREG(before[2]) and before[3] <= 32*MIB, 'unbounded input')
    raw = path.read_bytes()
    require(len(raw) == before[3] and stamp(path) == before, 'input changed')
    return raw

def sha(path):
    return hashlib.sha256(data(path)).hexdigest()

def ref(path):
    return dict(path=str(path), sha256=sha(path))

def pinned(reference, checked=None, *, raw=False):
    require(type(reference) is dict and set(reference) == {'path', 'sha256'}
            and type(reference['sha256']) is str
            and re.fullmatch('[0-9a-f]{64}', reference['sha256']), 'unbound reference')
    payload = data(reference['path'])
    require(hashlib.sha256(payload).hexdigest() == reference['sha256'], 'changed input: ' + reference['path'])
    if checked is not None:
        row = dict(sha256=reference['sha256'], size=len(payload), stamp=stamp(reference['path']))
        require(reference['path'] not in checked or checked[reference['path']] == row, 'input overlap changed')
        checked[reference['path']] = row
        require(len(checked) <= 1024 and sum(r['size'] for r in checked.values()) <= 96*MIB,
                'finite metadata closure exceeded')
    return payload if raw else json.loads(payload)

def write(path, value):
    payload = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    require(len(payload) <= 32*MIB, 'packet output too large')
    with Path(path).open('xb') as output:
        output.write(payload)

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def absent(path):
    path = Path(path)
    require(not path.exists() and not path.is_symlink(), 'namespace must be fresh/absent: ' + str(path))


def source_paths():
    return sorted({*R.joinpath('scripts').glob('*.py'),
        *(H/n for n in ('bench_e2e_workflow.py','verify_repeated_workflow.py','interpreter.py',
                        'host_codegen_opt.py','workflow_runtime_arms.py','workflow_placement.py')),
        OWNED,*(HERE/n for n in ('prepare.py','observe.py','proofs.py','command-template.json','workload.json'))})


def authenticate(reference, checked):
    sources=pinned(reference,checked)
    require(set(sources)=={'policy','files'} and sources['policy']=='host-wrapper-ruff-correctness-sources-v1'
        and len(list(R.joinpath('scripts').glob('*.py')))==112
        and set(sources['files'])==set(map(str,source_paths())), 'complete held source closure differs')
    for name,digest in sources['files'].items():pinned(dict(path=name,sha256=digest),checked,raw=True)
    return sources


def routes():
    return dict(run_id=NAME,work=str(R/'.work/runs'/NAME),results=str(R/'results'/NAME),
        observer=str(R/'.work'/(NAME+'-observer')),outer=str(R/'.work/experiments'/(NAME+'-supervisor')),
        parent=str(R/'.work'/(NAME+'-execution')),native_cache=str(R/'.work/runs'/NAME/'native'),
        summary=str(R/'results'/NAME/'summary.json'),records=str(R/'.work/runs'/NAME/'records.json'),
        verification=str(R/'results'/NAME/'verification.json'))


def cache_path(tool, mode):
    require(mode in ('baseline','candidate'),'exact custom mode required')
    text=('custom-compiler-v1\0'+RUNTIME+'\0off\0shared-entries-v1\0'
          +str(R/'.work/sources/ruff/Cargo.toml')+'\0ruff_linter\0True\0std-mir:'+STD+'\0'+NAME+':'+mode)
    if mode=='candidate':text='host-codegen-opt-v1\0on\0'+text
    return str(R/'.work/interpreter-workspaces'/tool/hashlib.sha256(text.encode()).hexdigest()[:24])


def prerequisites(binding, checked):
    return load(HERE/'proofs.py','_host_correctness_proofs').validate(SimpleNamespace(**globals()),binding,checked)


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ('sources-sha256','tool-key','publication-receipt-sha256','published-tools-sha256',
                 'publication-execution-sha256','rbc-binding-sha256','rbc-record-sha256',
                 'rbc-result-sha256','rbc-execution-sha256'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    require(Path.cwd()==R and sys.dont_write_bytecode and not sys.flags.optimize,'exact R cwd/Python -B required')
    require(all(re.fullmatch('[0-9a-f]{64}',v) for v in vars(args).values()),'actual SHA/key arguments required')
    checked={};sources_ref=dict(path=str(HERE/'sources.json'),sha256=args.sources_sha256)
    authenticate(sources_ref,checked)
    binding=dict(policy='host-wrapper-ruff-correctness-binding-v1',tool_key=args.tool_key,
        runtime_key=RUNTIME,std_key=STD,sources=sources_ref,preparation_environment=dict(os.environ),
        proofs={
          'publication':dict(path=str(X/'.work/host-wrapper-exporter-publication-01/receipt.json'),sha256=args.publication_receipt_sha256),
          'published_tools':dict(path=str(X/'.work/host-wrapper-exporter-publication-01/published-tools.json'),sha256=args.published_tools_sha256),
          'publication_execution':dict(path=str(ROOT/'.work/host-wrapper-exporter-publication-execution-01/record.json'),sha256=args.publication_execution_sha256),
          'rbc_binding':dict(path=str(RBC/'binding.json'),sha256=args.rbc_binding_sha256),
          'rbc_record':dict(path=str(ROOT/'results/host-wrapper-rbc-fixture-02/record.json'),sha256=args.rbc_record_sha256),
          'rbc_result':dict(path=str(ROOT/'results/host-wrapper-rbc-fixture-02/suite-result.json'),sha256=args.rbc_result_sha256),
          'rbc_execution':dict(path=str(ROOT/'.work/host-wrapper-rbc-execution-02/record.json'),sha256=args.rbc_execution_sha256)})
    owned=load(OWNED,'_host_correctness_owned')
    with owned.workload_lock(LOCK,600):
        prerequisite=prerequisites(binding,checked)
        h=routes();template=pinned(ref(HERE/'command-template.json'),checked)
        require(template['status']=='unbound' and template['tool_key_slots']==2
            and template['command'].count(None)==2,'fixed same-tool command template differs')
        command=[args.tool_key if item is None else item for item in template['command']]
        environment=dict(prerequisite['environment'],CARGO_NET_OFFLINE='true',CARGO_TERM_COLOR='never',
            CARGO_TERM_VERBOSE='true',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',
            RUSTUP_TOOLCHAIN='nightly-2026-09-08',RUSTUP_DIST_SERVER='file:///dev/null',
            RUST_INTERP_LAUNCH_STATS='1',TMPDIR=h['observer']+'/tmp/')
        require(not any(k.startswith(('LD_','DYLD_','CARGO_PROFILE_')) or k in
            ('RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER',
             'CARGO_TARGET_DIR','CARGO_INCREMENTAL') or k.startswith('RUST_INTERP_') and k!='RUST_INTERP_LAUNCH_STATS'
            for k in environment),'unexpected compiler/profile/loader policy environment')
        require(environment['__CF_USER_TEXT_ENCODING'].split(':')[0].lower()==hex(os.getuid()),
                'actual Darwin user environment required')
        h.update(command=command,environment=environment,
            custom_caches={mode:cache_path(args.tool_key,mode) for mode in ('baseline','candidate')},
            verifier=['/opt/homebrew/bin/python3','-B',str(H/'verify_repeated_workflow.py'),h['summary'],'--wait-for-lock','600'])
        require(len(set(h['custom_caches'].values()))==2,'custom cache collision')
        absent(PACKET)
        for path in [h[k] for k in ('work','results','observer','outer','parent')]+list(h['custom_caches'].values()):absent(path)
        workload=pinned(ref(HERE/'workload.json'),checked)
        # Metadata-only preparation; history admission separately requires21GiB.
        free=owned.disk(R,9)
        for name,row in checked.items():
            require(sha(name)==row['sha256'] and stamp(name)==row['stamp'],'prerequisite changed during preparation')
        plan=dict(policy='host-wrapper-ruff-correctness-plan-v1',status='prepared-unexecuted',
            prepared_at=time.time(),preparation_pid=os.getpid(),preparation_parent_pid=os.getppid(),
            binding=binding,sources=sources_ref,history=h,workload=workload,
            allocation=dict(entry_free_bytes=21*GIB,command_floor_bytes=16*GIB,
                per_history_allocated_byte_limit=7*GIB,retained_evidence_byte_limit=512*MIB,
                scope='Boundary observations; no hard continuous allocation/CPU/wall/memory cap.'),
            preparation_free_bytes=free,canonical_lock=str(LOCK),canonical_wait_seconds=600,
            active_child_stop_gib=9,running_floor_gib=8,application_correctness_qualified=False,
            timing_used=False,performance_qualified=False,retirement='Separate review after normal closure; no cleanup here.')
        PACKET.mkdir();write(PACKET/'plan.json',plan);write(PACKET/'inputs.json',dict(files=checked))
        outer=Path(h['outer']);outer.mkdir()
        command=['/opt/homebrew/bin/python3','-B',str(HERE/'observe.py'),
            '--plan-sha256',sha(PACKET/'plan.json'),'--inputs-sha256',sha(PACKET/'inputs.json'),
            '--sources-sha256',args.sources_sha256]
        write(outer/'plan.json',dict(owner=str(R),supervisor_sha256=sha(SUPERVISOR),command=command))
        write(PACKET/'launch.json',dict(argv=['/opt/homebrew/bin/python3','-B',str(SUPERVISOR),'--supervise',str(outer/'plan.json')],
            cwd=str(R),plan=ref(outer/'plan.json'),environment=environment))
        write(PACKET/'preparation.json',dict(status='passed',pid=os.getpid(),parent_pid=os.getppid(),
            finished_at=time.time(),plan=ref(PACKET/'plan.json'),inputs=ref(PACKET/'inputs.json'),launch=ref(PACKET/'launch.json')))
        print(json.dumps(ref(PACKET/'preparation.json')))


if __name__=='__main__':main()
