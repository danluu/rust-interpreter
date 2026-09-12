"""Qualify the staged A/A guard and exact tool routes before timed commands."""
import ast
import fcntl
from pathlib import Path
import workflows as workflow


def main():
    root=workflow.ROOT
    with (root/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        paths=workflow.qualifications()
        harness=root/'scripts/bench_e2e_workflow.py'
        original=harness.read_text();staged=workflow.stage_aa(original)
        guards=[n for n in ast.walk(ast.parse(staged)) if isinstance(n,ast.If) and
            any(isinstance(c,ast.Constant) and c.value == 'A/A requires the exact qualified control on both sides'
                for child in n.body for c in ast.walk(child))]
        # Several enclosing if-statements may contain the same literal; the
        # exact replacement has two disjuncts comparing only the tool keys.
        guards=[n for n in guards if isinstance(n.test,ast.BoolOp) and
                {v.id for v in ast.walk(n.test) if isinstance(v,ast.Name)} == {'baseline_key','key'}]
        workflow.require(len(guards)==1,'staged guard identity differs')
        expression=compile(ast.Expression(guards[0].test),'staged-guard','eval')
        cases=0
        for left in [workflow.CONTROL,workflow.CANDIDATE]:
            for right in [workflow.CONTROL,workflow.CANDIDATE]:
                rejected=eval(expression,{'__builtins__':{}},{'baseline_key':left,'key':right})
                workflow.require(rejected == (left != workflow.CONTROL or right != workflow.CONTROL),'A/A key routing differs')
                cases+=1
        rejected=0
        for invalid in [original+original, original.replace(
            'baseline and candidate must differ in tool build, guest settings, or Cargo worker count','changed admission guard')]:
            try: workflow.stage_aa(invalid)
            except RuntimeError: rejected+=1
            else: raise RuntimeError('changed/duplicate guard accepted')
        tools={phase:workflow.tools_for(phase) for phase in ['aa','e2e']}
        workflow.require(tools['aa']['baseline'] == tools['aa']['candidate'],'A/A components differ')
        workflow.require(tools['e2e']['baseline']['vm_sha256'] != tools['e2e']['candidate']['vm_sha256'],'VM did not change')
        paths += [Path(__file__),Path(workflow.__file__),harness,
                  root/'benchmarks/experiments/call-slot-census/FAST-PATH-NEXT.md']
        out=root/'results/call-slot-workflow-controls-01';out.mkdir(exist_ok=False)
        workflow.write(out/'summary.json',dict(status='passed',key_routes_checked=cases,
            changed_guard_rejections=rejected,original_assertions_preserved=True,tools=tools,
            frozen={str(p.relative_to(root)):workflow.sha(p) for p in paths},new_guest_executions=0))
        print('four exact key routes, two changed-guard rejections and component identities pass')


if __name__ == '__main__': main()
