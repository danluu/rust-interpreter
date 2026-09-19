#!/usr/bin/env python3
"""Assemble source bindings from completed C13 prerequisites; never launch a child."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

P=Path("/Users/danluu/dev/rust-interp-buildtime-20260918/.work/optimization-20260918/std-mir-lazy-selection-probe")
BASE="050a7d2a1e9677bc467a49fdba7a2ab485566e97"
PINS={
 "unit-source-manifest.json":"db14ba649b5f51f9533e950e731a0fe3e5ecb4bf33a6403fde6b10e5b0702755",
 "decision-plan.json":"c432cb2dc3cb182e038a936c898e7d6a76c1270d6425629a4239ef1136838826",
 "unit-screen-01/result.json":"8cc032cc67a9b9880b130cb0449171f820982868bdf40190ca2be17946b670a0",
 "fixture-preparation-01/result.json":"9cb2f476727bf52cbc0f031cb6362d76f09a793be5ade8bc4d6600d7d38d592c",
 "fixture-preparation-01/fixture-descriptor.json":"41e0cd50eeddfdf63eb33674b508415b9f5c02ab79a6213731afff058f2ecde2",
 "fixture-prep-bindings.json":"383bc6585f95cdbe8dc3adaf13af1f09c8315a7c9dab42c504ecf4277f0c881f",
 "fixture-preparation-plan.json":"a25afbd41cc39574e1995949cfb218ca46d1dbe724466b5ee147341f58679949",
 "run-fixture-preparation.py":"5e0b6f0936d45e29284292e9017c20b3e316898455ed774d6cc8af25a7c3c74a",
 "fixture-prep.py":"27439f3feacb9dabb0baccfd9dfd5b19c4017e2660e106fbba00655367e31ac0",
 "timing-driver.py":"06ad506bd664dd6e2188bf4965869195e3dd6e2567f91ed313a2c3aca9ff1b6c",
 "run-screen.py":"891bb4415303e1ecb9260dbacda7aa3716a88b659ea82120216715f9990d545c",
 "TIMING-CONTROLLER-INDEPENDENT-REVIEW.md":"326814b3bfacdb8f0065d18a8a87adb92151993adf53411a5170d4cdd9b53548",
 "UNIT-INDEPENDENT-RAW-AUDIT.md":"225765236382835883b39081cf24edf40e42a75d0f0e4e4c986b6ee090de78e0",
 "UNIT-ROOT-RAW-AUDIT.json":"3387ec3430dabb3b68a393bffa63b293a89fd42432bb03da075965d1d127d219",
 "FIXTURE-ROOT-RAW-AUDIT.json":"45ffd730b323b6e771507b1b00e1b4197f556afa45b872be187684f8a94e1023",
 "FIXTURE-INDEPENDENT-RAW-AUDIT.md":"847e5517dacaf9fb36e6a9d6970341aab774b8f851db49890796d3739438f46c",
 "PROTOCOL-DRAFT.md":"ffcb79cf4b6782827d742bd5d1692012c8435abbb7b0948a01e86746a43301d6",
}
def require(ok,message):
 if not ok: raise RuntimeError(message)
def stamp(s):
 return [s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink]
def disk():
 s=os.statvfs(P); require(s.f_bavail*s.f_frsize>16*1024**3,"source-write disk admission")
def read(path):
 path=Path(path); before=path.lstat()
 require(stat.S_ISREG(before.st_mode) and before.st_size<=16*1024**2,"unsafe/oversized source")
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,"rb",buffering=0) as f:
  require(stamp(os.fstat(f.fileno()))==stamp(before),"opening identity changed")
  data=f.read(before.st_size+1)
  require(len(data)==before.st_size and stamp(os.fstat(f.fileno()))==stamp(before),"reading identity changed")
 require(stamp(path.lstat())==stamp(before),"path identity changed")
 return data,dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
def add(fixed,path,expected=None):
 data,proof=read(path)
 require(expected is None or proof=={k:expected[k] for k in ("bytes","sha256")},"proof mismatch: "+str(path))
 require(str(path) not in fixed or fixed[str(path)]==proof,"conflicting proof")
 fixed[str(path)]=proof
 return data
def main():
 require(sys.argv[1:]==["--assemble-completed-c13-fixture"],"explicit assembly command required")
 disk(); require(not (P/"screen-bindings.json").exists() and not (P/"screen-01").exists(),"output already exists")
 fixed={}; parsed={}
 for name,digest in PINS.items():
  data,pr=read(P/name); require(pr["sha256"]==digest,"frozen pin changed: "+name)
  if name!="run-screen.py": fixed[str(P/name)]=pr
  if name.endswith(".json"): parsed[name]=json.loads(data)
 u=parsed["unit-screen-01/result.json"]; f=parsed["fixture-preparation-01/result.json"]
 m=parsed["unit-source-manifest.json"]; prep=parsed["fixture-prep-bindings.json"]
 fixture=parsed["fixture-preparation-01/fixture-descriptor.json"]
 for result in (u,f):
  require(result["status"]=="passed" and result["error"] is None and result["post_binding_error"] is None
          and result["bindings"]==result["bindings_after"] and len(result["children"])==2
          and all(c["returncode"]==0 and c["error"] is None for c in result["children"]),"prerequisite failed")
 require(u["expected_tests"]==u["passed_tests"]==21 and len(u["tests"])==1,"unit count")
 require(f["prerequisites"]["sha256"]==PINS["unit-screen-01/result.json"]
         and f["prerequisites"]["passed_tests"]==21 and f["project_api_calls"]==0,"fixture prerequisite")
 require(f["fixtures_path"]==str(P/"fixture-preparation-01/fixture-descriptor.json")
         and f["fixtures_proof"]["sha256"]==PINS["fixture-preparation-01/fixture-descriptor.json"],"fixture descriptor")
 ids=sorted(i for row in m["tests"] for i in row["expected_ids"])
 require(len(ids)==21 and sorted(u["tests"][0]["report"]["discovered_ids"])==ids
         and sorted(u["tests"][0]["report"]["successful_ids"])==ids,"unit names")
 sources=dict(baseline=m["baseline_source_provenance"]["sources"],candidate=m["arms"]["candidate"]["sources"])
 roots=dict(baseline=m["baseline_root"],candidate=m["arms"]["candidate"]["root"])
 require(m["base_commit"]==prep["base_commit"]==BASE and sources==prep["sources"] and roots==prep["roots"],"source origins")
 changed=sorted(k for k in set(sources["baseline"])|set(sources["candidate"])
                if sources["baseline"].get(k)!=sources["candidate"].get(k))
 require(changed==["scripts/std_mir.py","tests/test_std_mir_selection.py"],"source delta")
 source_paths=set()
 for arm,rootname in roots.items():
  root=Path(rootname); require(root.resolve()==root,"source root")
  actual={str(x.relative_to(root)) for folder in ("scripts","tests") for x in (root/folder).glob("*.py")}
  require(actual==set(sources[arm]) and len(actual)=={"baseline":189,"candidate":190}[arm],"source membership")
  for relative,expected in sources[arm].items():
   path=root/relative; require(".." not in Path(relative).parts and not Path(relative).is_absolute(),"source escape")
   _,pr=read(path); require(pr==expected,"current source changed"); source_paths.add(str(path))
 # Reuse the completed qualification's full content proofs only with unchanged exact current identities.
 # The timing controller independently hashes every fixed file before and after its panel.
 for name,pr in f["bindings"].items():
  path=Path(name); info=path.lstat()
  require(stat.S_ISREG(info.st_mode) and stamp(info)==pr["stamp"] and str(path.resolve())==pr["resolved"],"qualified input changed: "+name)
  if name not in source_paths:
   value={k:pr[k] for k in ("bytes","sha256")}
   require(name not in fixed or fixed[name]==value,"qualified proof conflict"); fixed[name]=value
 require(len(m["runtime"]["files"])==1955 and len(m["runtime"]["links"])==8,"runtime closure")
 for name,pr in m["runtime"]["files"].items():
  require(stamp(Path(name).lstat())[:6]==pr["identity"]
          and fixed[name]=={k:pr[k] for k in ("bytes","sha256")},"runtime file mismatch")
 for row in m["runtime"]["links"]:
  path=Path(row["path"]); info=path.lstat()
  require(stat.S_ISLNK(info.st_mode) and stamp(info)[:6]==row["identity"]
          and os.readlink(path)==row["text"] and str(path.resolve())==row["resolved"],"runtime link mismatch")
 require(m["runtime"]["links"]==prep["runtime_links"],"runtime provenance changed")
 # Exact named retained evidence: no recursive output, target, registry, or peer walk.
 extras=["TIMING-ROOT-SOURCE-REVIEW.json","UNIT-FREEZE.json","FIXTURE-FREEZE.json","UNIT-SCREEN.md","UNIT-DERIVATION.json",
         "unit-controller.diff","FIXTURE-PREPARATION.md","TIMING-DRAFT.md",
         "TIMING-CONTROLLER-DERIVATION.json","timing-controller.diff",
         "assemble-screen-bindings.py","SCREEN-BINDINGS-ASSEMBLY.md"]
 for stage,labels,suffix in (("unit-screen-01",("candidate-selection-memory","candidate-selection"),"observations"),
                            ("fixture-preparation-01",("prepare-memory","prepare"),"disk")):
  extras.append(stage+"/inputs.json")
  for label in labels:
   extras.extend(stage+"/"+label+x for x in ("-planned.json","-start.json","-terminal.json",".stdout",".stderr","-"+suffix+".jsonl"))
 extras.extend(["unit-screen-01/candidate-selection-tests.json","unit-screen-01/test-inventory.json"])
 for name in extras: add(fixed,P/name)
 for result in (u,f):
  for child in result["children"]:
   for pr in child["logs"].values(): add(fixed,Path(pr["path"]),pr)
 # Full small synthetic-fixture bytes and stamps, with exact declared directory membership.
 fr=Path(fixture["fixture_output_root"]); inv=fixture["fixture_inventory"]; entries=inv["entries"]
 require(len(entries)==inv["entry_count"]==47 and inv["total_file_bytes"]==36370,"fixture shape")
 for relative,row in entries.items():
  path=fr/relative; require(stamp(path.lstat())==row["stamp"],"fixture stamp changed")
  if row["kind"]=="file": add(fixed,path,row)
  else:
   require(row["kind"]=="directory" and stat.S_ISDIR(path.lstat().st_mode),"fixture type")
   expected={str(Path(k).name) for k in entries if k!="." and str(Path(k).parent)==relative}
   require({x.name for x in path.iterdir()}==expected,"fixture directory membership changed")
 for stage,name in (("unit-screen-01","pycache"),("unit-screen-01","candidate-selection-tmp"),
                    ("fixture-preparation-01","qualification-pycache"),("fixture-preparation-01","prep-tmp")):
  path=P/stage/name
  require(path.is_dir() and not list(path.iterdir()),"private qualification directory changed: "+str(path))
 controller=ast.parse(read(P/"run-screen.py")[0])
 constants={n.targets[0].id:ast.literal_eval(n.value) for n in controller.body if isinstance(n,ast.Assign)
            and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant)}
 four=dict(UNIT_SHA=PINS["unit-screen-01/result.json"],QUALIFICATION_SHA=PINS["fixture-preparation-01/result.json"],
           FIXTURE_DESCRIPTOR_SHA=PINS["fixture-preparation-01/fixture-descriptor.json"])
 require(all(constants[k]=="UNBOUND" for k in list(four)+["BINDINGS_SHA"]),"timing template already changed")
 require(str(P/"run-screen.py") not in fixed and str(P/"screen-bindings.json") not in fixed,"hash cycle")
 d=dict(schema_version=1,state="frozen",base_commit=BASE,roots=roots,sources=sources,changed_files=changed,
        stdlib_root=str(Path(m["runtime"]["executable"]).parent.parent/"lib/python3.14"),
        fixed_files=dict(sorted(fixed.items())),runtime_links=m["runtime"]["links"],
        decision_sha256=PINS["decision-plan.json"],unit_result_sha256=four["UNIT_SHA"],
        fixture_qualification_result_sha256=four["QUALIFICATION_SHA"],fixture_descriptor_sha256=four["FIXTURE_DESCRIPTOR_SHA"],
        timing_driver_sha256=PINS["timing-driver.py"],
        freeze_provenance=dict(reviewed_unbound_controller_sha256=PINS["run-screen.py"],
          controller_excluded_to_avoid_hash_cycle=True,final_controller_records_own_proof_before_after=True,
          runtime_hashes_reused_only_after_exact_identity_checks=True,
          timing_controller_rehashes_all_fixed_files=True,
          source_only_assembly_no_project_imports_or_child_launches=True))
 raw=(json.dumps(d,sort_keys=True,indent=2)+"\n").encode(); require(len(raw)<2*1024**2,"descriptor unexpectedly large")
 disk()
 with (P/"screen-bindings.json").open("xb") as output: output.write(raw)
 four["BINDINGS_SHA"]=hashlib.sha256(raw).hexdigest()
 print(json.dumps(dict(descriptor_bytes=len(raw),fixed_files=len(fixed),sources={k:len(v) for k,v in sources.items()},
                       runtime_files=1955,runtime_links=8,controller_constants=four),sort_keys=True))
if __name__=="__main__": main()
