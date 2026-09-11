#!/usr/bin/env python3
"""Weight qualified new inventories with exact-artifact historical execution counts."""
import argparse
import fcntl
import json
import subprocess
import sys

from build import ROOT,HERE,read,require,sha,write,environment


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args()
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        collection_path=ROOT/'results/aggregate-byte-writes-collect-01/summary.json'
        collection=read(collection_path);require(collection['status']=='passed','collection incomplete')
        old_path=ROOT/'results/aggregate-reuse-collection-01/summary.json';old=read(old_path)
        require(old['status']=='passed','historical counts not qualified')
        target=ROOT/'.work/aggregate-byte-writes-weights-target'
        command=['cargo','+nightly-2026-09-08','test','--release','--offline','--jobs','2',
                 '--manifest-path',str(HERE/'Cargo.toml'),'--target-dir',str(target)]
        with (work/'tests.log').open('x') as log:
            subprocess.run(command,cwd=ROOT,env=environment(),stdout=log,stderr=subprocess.STDOUT,check=True)
        require('test result: ok. 2 passed; 0 failed;' in (work/'tests.log').read_text(),'missing join tests')
        command[2]='build'
        with (work/'build.log').open('x') as log:
            subprocess.run(command,cwd=ROOT,env=environment(),stdout=log,stderr=subprocess.STDOUT,check=True)
        binary=target/'release/aggregate-byte-write-weights'
        evidence={str(p.relative_to(ROOT)):sha(p) for p in [collection_path,old_path,binary,
            HERE/'weights.rs',HERE/'weight.py',HERE/'Cargo.toml',HERE/'Cargo.lock',work/'tests.log',work/'build.log']}
        cases=[]
        for case in collection['cases']:
            historical=next(c for c in old['cases'] if c['label']==case['label'])
            require(case['artifact_sha256']==historical['artifact_sha256'],'historical artifact differs')
            for c,fields in [(case,['artifact','inventory']),(historical,['artifact','profile'])]:
                for field in fields:
                    path=ROOT/c[field];require(sha(path)==c[field+'_sha256'],'input hash differs')
                    evidence[str(path.relative_to(ROOT))]=sha(path)
            output=work/(case['label']+'.json')
            with output.open('x') as out:
                subprocess.run([str(binary),str(ROOT/case['artifact']),str(ROOT/historical['profile']),str(ROOT/case['inventory'])],
                    cwd=ROOT,stdout=out,check=True)
            row=read(output)
            require(row['instructions']==historical['statistics']['instructions'],'historical instruction total differs')
            row.update(label=case['label'],historical_profile=historical['profile'],historical_profile_tool=old['tool_key'])
            evidence[str(output.relative_to(ROOT))]=sha(output)
            cases.append(row)
            print(json.dumps({k:row[k] for k in ['label','additional_frame_byte_percentage','unobserved_direct_frame_bytes','declined_direct_frame_bytes']}),flush=True)
        folded=next(c for c in cases if c['label']=='folded-literal-trie')
        scope=folded['additional_frame_byte_percentage']>=25
        result=dict(status='passed',tool_key=collection['tool_key'],parent_tool_key=collection['parent_tool_key'],
            cases=cases,folded_25_percent_scope_gate=scope,weighted_counts_are_historical=True,evidence=evidence,
            production_change=False,performance_measurement=False,
            decision='Scope warrants a separately qualified compiler transformation; byte/alias and relocation proof and fresh E2E gates remain required.' if scope else
                'Scope misses the predeclared bound; park this layout proposal and move to unfiltered-suite compatibility.')
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False);write(out/'summary.json',result)
        lines=['# Broader aggregate storage scope','','Fresh exports preserve original bytecode and pass the original assertions. The exact immutable current VM and wrapper are retained. These inventories estimate a compiler transformation; they do not implement it.','',
            '| Workflow | Additional weighted local-byte scope | Unobserved direct-frame bytes | Declined direct-frame bytes |',
            '| --- | ---: | ---: | ---: |']
        for c in cases:lines.append(f"| {c['label']} | {c['additional_frame_byte_percentage']:.2f}% | {c['unobserved_direct_frame_bytes']} | {c['declined_direct_frame_bytes']} |")
        lines += ['',result['decision'],'','Counts come from previously qualified executions of the exact same bytecode, not fresh timing. Typed opcode/profile identities and complete instruction totals reconcile. Estimates exclude final temporary/inline-bank layout, alignment effects, indirect targets and entry/TLS frames. No speedup is predicted.','']
        (out/'assessment.md').write_text('\n'.join(lines))


if __name__=='__main__':main()
