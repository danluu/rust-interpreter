#!/usr/bin/env python3
"""Verify the direct emitter's new words with platform assembly; no guest code."""
import json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        work=ROOT/'.work/guarded-ranges-encoding-01';work.mkdir(exist_ok=False)
        source=work/'probe.s'
        source.write_text('.text\n.p2align 2\n_probe:\n fmov d16, x11\n fmov x11, d16\n fmov x12, d16\n adds x12, x11, x10\n ldr x11, [x11]\n ret\n')
        paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),source,ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']
        frozen={str(p.relative_to(ROOT)):sha(p) for p in paths};records=[]
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_executions=0))
        commands=[('assemble',['xcrun','clang','-arch','arm64','-c',str(source),'-o',str(work/'probe.o')]),
            ('disassemble',['otool','-tvV',str(work/'probe.o')]),('bytes',['otool','-t',str(work/'probe.o')])]
        for label,command in commands:
            require_space(ROOT,8)
            child,out,err=capture(command,cwd=ROOT,env=os.environ.copy(),receipt_path=work/'active.json',receipt=dict(label=label))
            for suffix,text in [('stdout',out),('stderr',err)]:(work/(label+'.'+suffix)).write_text(text)
            records.append(dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                stdout_sha256=sha(work/(label+'.stdout')),stderr_sha256=sha(work/(label+'.stderr'))))
            write(work/'records.json',records);assert child.returncode==0,err
        words=[]
        for line in (work/'bytes.stdout').read_text().splitlines():
            if re.match(r'^[0-9a-f]{16} ',line):words.extend(int(w,16) for w in line.split()[1:])
        assert words==[0x9e670170,0x9e66020b,0x9e66020c,0xab0a016c,0xf940016b,0xd65f03c0],words
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results/guarded-ranges-encoding-01';out.mkdir(exist_ok=False)
        result=dict(status='passed',guest_executions=0,words=[f'{w:08x}' for w in words],raw=str(work.relative_to(ROOT)),
            frozen=frozen,plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            scope='Platform assembler verifies direct words only; it is not a guest execution backend.')
        write(out/'summary.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
