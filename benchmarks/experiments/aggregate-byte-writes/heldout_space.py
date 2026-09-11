"""Reuse qualified full-cache estimates with the running floor included."""
import importlib.util
from build_relocation import ROOT,read,sha,require
from workflow_space import required_bytes

def estimate(label):
    if label=='nushell-type-relations':
        p=ROOT/'results/resumable-copy-heldout-01-case-01-preflight/summary.json'
        require(sha(p)=='acbfdd5dd8e7367e451bc5e6232f60f53f8006c246682c84e4e33df979e6dff2','Nushell reference changed')
        r=read(p);bound={str(p.relative_to(ROOT)):sha(p),**r['references']}
        require(all(sha(ROOT/k)==v for k,v in bound.items()),'Nushell reference evidence changed')
        total=r['historical_unique_native_before_object_reclaim_bytes']+sum(r['historical_other_cache_bytes'].values())
        require(total==r['historical_total_bytes'] and r['cache_growth_allowance_percent']==20,'Nushell cache arithmetic differs')
        return required_bytes(cache_bytes=total,growth_percent=20,command_floor_bytes=8*1024**3,
            archive_reserve_bytes=r['first_check_archive_reserve_bytes'],evidence_reserve_bytes=r['metadata_and_evidence_allowance_bytes']),bound
    if label in ['ruff','nushell']:
        p=ROOT/'benchmarks/experiments/resumable-native-calls/preflight_copy_heldout_case.py'
        spec=importlib.util.spec_from_file_location('prior_heldout_space',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        reports,bound=module.references(label)
        bound[str(p.relative_to(ROOT))]=sha(p)
        return module.estimate(reports),bound
    require(label in ['forward-anchored-tls','pgrust-sha1-inline8','pgrust','rg-aot'],'unplanned heldout')
    # Same conservative bounded-cache admission as the completed fre primaries.
    return required_bytes(cache_bytes=4*1024**3,growth_percent=20,command_floor_bytes=8*1024**3,
        archive_reserve_bytes=2*1024**3,evidence_reserve_bytes=256*1024**2),{}
