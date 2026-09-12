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
        from verify_workflow import EXPECTED_TOOLS, admit_tools
        import copy
        admit_tools(EXPECTED_TOOLS)
        tool_rejections=0
        for mode in EXPECTED_TOOLS:
            for field in EXPECTED_TOOLS[mode]:
                bad=copy.deepcopy(EXPECTED_TOOLS);bad[mode][field]='0'*64
                try: admit_tools(bad)
                except RuntimeError: tool_rejections+=1
                else: raise RuntimeError('changed tool component admitted')
        workflow.require(tool_rejections==8,'tool rejection matrix differs')
        # Prove the qualified compiler verifier's downstream checks are intact.
        # Only the explicit tool binding, VM equality policy, its error text,
        # and the permitted VM identity field differ.
        base=root/'benchmarks/experiments/aggregate-byte-writes/verify_relocation.py'
        qualifier=workflow.read(root/'results/aggregate-relocation-controls-01/summary.json')
        workflow.require(workflow.sha(base)==qualifier['sources'][str(base.relative_to(root))],
            'qualified base verifier differs')
        original_verify=next(n for n in ast.parse(base.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='verify')
        candidate_path=Path(workflow.__file__).with_name('verify_workflow.py')
        candidate_verify=next(n for n in ast.parse(candidate_path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='verify')
        binding=[n for n in candidate_verify.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
            and isinstance(n.value.func,ast.Name) and n.value.func.id=='admit_tools']
        workflow.require(len(binding)==1,'missing or duplicate exact-tool admission')
        candidate_verify.body.remove(binding[0])
        class AllowedChanges(ast.NodeTransformer):
            def __init__(self): self.changed=0
            def visit_Compare(self,node):
                if ast.unparse(node)=="a['vm_sha256'] == b['vm_sha256']":
                    node.ops=[ast.NotEq()];self.changed+=1
                return self.generic_visit(node)
            def visit_Constant(self,node):
                if node.value=='comparison does not isolate exporter':
                    node.value='comparison does not bind the planned compiler/runtime change';self.changed+=1
                return node
            def visit_Assign(self,node):
                if len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='ignored':
                    node.value.elts.append(ast.Constant(value='vm_sha256'));self.changed+=1
                return self.generic_visit(node)
        allowed=AllowedChanges();allowed.visit(original_verify)
        workflow.require(allowed.changed==3 and ast.dump(original_verify,include_attributes=False)==
            ast.dump(candidate_verify,include_attributes=False),'downstream verification changed outside exact admission')
        paths += [Path(__file__),Path(workflow.__file__),harness,
                  Path(workflow.__file__).with_name('PLAN.md'),Path(workflow.__file__).with_name('WORKFLOWS.md'),candidate_path,base,
                  root/'results/aggregate-relocation-controls-01/summary.json']
        out=root/'results/whole-call-workflow-controls-02';out.mkdir(exist_ok=False)
        workflow.write(out/'summary.json',dict(status='passed',key_routes_checked=cases,
            changed_guard_rejections=rejected,changed_tool_rejections=tool_rejections,
            qualified_verifier_body_preserved=True,original_assertions_preserved=True,tools=tools,
            frozen={str(p.relative_to(root)):workflow.sha(p) for p in paths},new_guest_executions=0))
        print('four exact key routes, two changed-guard rejections and component identities pass')


if __name__ == '__main__': main()
