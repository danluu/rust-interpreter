#!/usr/bin/env python3
"""Freeze only diagnostic inputs; never compile or change a compiler checkout."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=(ROOT/'gate.rs').read_bytes()
(ROOT/'gate.snapshot').write_bytes(source)
(ROOT/'binding.rs').write_text('pub const GATE_SHA256: &str = "'+sha(ROOT/'gate.rs')+'";\n'
    'pub const PUBLIC_COMMIT: &str = "cea272fa356e94bd2ee2cadf376630aa0683867a";\n')
files=['gate.rs','main.rs','gate.snapshot','binding.rs','fixture.rs','external.rs','prepare.py','qualify.py','policy.json','CONTRACT.md']
result={'policy':'hir-body-input-coverage-v2','status':'source-prepared-unqualified','compiler_source_commit':'58e1e1f5311f4424ea81def4763081f6da62d9b3',
    'public_commit':'cea272fa356e94bd2ee2cadf376630aa0683867a','files':{p:sha(ROOT/p) for p in files},'cache_effects_qualified':False,'hir_ids_observed':False}
(ROOT/'diagnostic-source.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'gate_sha256':result['files']['gate.rs']}))
