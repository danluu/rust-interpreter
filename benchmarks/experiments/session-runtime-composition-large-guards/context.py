"""Original project selection and conservative per-namespace cache admission."""
import json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
from workflow_cases import WORKFLOW_VARIANTS
from std_mir import checked_std_mir
PINS={'rg-aot':'474782386e976f80f7bcbc2643eaaeac1d787ad3','nushell':'9d3157963241cf89447119d34d6e887859f5e7e8'}
STD='bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef'
def disk_need(project,unique_bytes=None):
    assert project in PINS
    if project=='rg-aot':return 12*1024**3
    assert type(unique_bytes) is int and unique_bytes>0
    # Five custom, three ordinary Cargo namespaces, and an early-error namespace.
    return max(47*1024**3,8*1024**3+(unique_bytes*9*120+99)//100)
def require_admission(root,needed):
    assert shutil.disk_usage(root).free>=needed,'insufficient pre-edit cache admission'
def context(project):
    assert project in PINS
    std=checked_std_mir('nightly-2026-09-08');assert std[2]==STD
    paths=[ROOT/'.work/std-mir'/STD/'ready.json']
    if project=='rg-aot':
        p=ROOT/'.work/private/workflow-rg-aot.json';adapter=json.loads(p.read_text());paths.append(p)
        assert adapter['owner']==str(ROOT) and adapter['revision']==PINS[project]
        case=adapter['case'];assert case['private'] and len(case['tests'])==1
        needed=disk_need(project)
    else:
        case=WORKFLOW_VARIANTS['nushell','type-relations'];assert len(case['tests'])==14
        p=ROOT/'results/aggregate-relocation-space-nu-native-01/summary.json';estimate=json.loads(p.read_text());paths.append(p)
        assert estimate['status']=='completed'
        needed=disk_need(project,estimate['unique_original_bytes'])
    names=sorted(case['tests']);assert len(names)==len(set(names)) and len(case['edits'])==5
    reference=dict(revision=PINS[project],instruction_limit=100_000_000_000,allocation_limit=150_000,
        inline_leaves=True,trap_unsupported_calls=True,run_try_callbacks=True,guest_rustflags=[])
    return case,reference,names,paths,needed
