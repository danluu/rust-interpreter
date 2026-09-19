"""Source-only draft for one exact read-only recovery packet preparation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import types

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[1]
PACKET=HERE/'recovery-plan-01.json'
RECOVERY_SHA='572907bc8ebd093b33cbe82906e8ed5c1409eadd9de3adbe27bf8c3604009474'  # Exact reviewed source binding, filled before preparation.

def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    require(type(RECOVERY_SHA) is str and len(RECOVERY_SHA)==64,'unbound reviewed recovery source')
    require(Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize,'fixed read-only preparation')
    require(not PACKET.exists() and not PACKET.is_symlink(),'fresh recovery packet')
    path=HERE/'recovery.py';raw=path.read_bytes();require(sha(raw)==RECOVERY_SHA,'reviewed recovery source changed')
    module=types.ModuleType('_copy_recovery_prepare');module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    def guard():require(shutil.disk_usage(OWNER).free>=9*2**30,'read-only preparation live capacity')
    reader=module.Reader(guard);proposal,full,manifest,catalog=module.metadata(reader)
    module.target_inventory(reader,proposal['complete_inventory'])
    require(module.identity(module.TARGET.parent)==proposal['outer_parent_identity'],'outer parent changed')
    # Compressed bytes may be hashed during preparation; no gzip/tar is opened.
    archive=reader.file(proposal['archived_recovery']['archive']['path'])
    require(archive['sha256']==proposal['archived_recovery']['archive']['sha256']
            and archive['size']==proposal['archived_recovery']['archive']['bytes'],'recovery archive current bytes')
    for item in proposal['recovery']:
        for name in [item['retention_entry']['source'],item['physical_witness']]:reader.file(name,full[name])
    audit=reader.json(module.CONTROLS_AUDIT,module.CONTROLS_AUDIT_SHA)
    require(audit['status']=='verified' and type(audit['controls']) is int and audit['controls']==40,'actual40 helper qualification')
    sources={}
    # The outer dispatcher is retained in its execution source capsule, not
    # frozen here: its later actual-packet pin cannot become its own input hash.
    for name in ['recovery.py','prepare_recovery.py','recover.py']:
        source=HERE/name;sources[str(source)]=reader.file(source)
    require(sources[str(path)]['sha256']==RECOVERY_SHA,'same reviewed recovery implementation')
    for name,row in reader.records.items():require(module.identity(name)==row['identity'],'recovery input changed before packet publication')
    packet=dict(status='prepared-unrun-read-only-recovery',proposal_sha256=module.PROPOSAL_SHA,
        source=str(HERE),output=str(OWNER/'.work/retained-proof-copy-recovery-01.json'),
        recovery_source_sha256=RECOVERY_SHA,sources=sources,files=reader.records,
        target=str(module.TARGET),selected_files=21,preserved_files=40,archive_members=1191,
        helper40_audit=dict(path=str(module.CONTROLS_AUDIT),sha256=module.CONTROLS_AUDIT_SHA),
        limits=module.LIMITS,capacity=dict(entry_gib=16,live_gib=9,floor_gib=8),
        canonical_lock='/Users/danluu/dev/rust-interp/.work/benchmark.lock',wait_seconds=600,
        creates_archive=False,extracts_archive=False,retirement=False,source_imports_only=True)
    payload=(json.dumps(packet,sort_keys=True,indent=2)+'\n').encode();require(len(payload)<=16*2**20,'finite recovery packet')
    with PACKET.open('xb') as out:out.write(payload);out.flush();os.fsync(out.fileno())
    require(PACKET.read_bytes()==payload,'full recovery packet readback')
    fd=os.open(HERE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
    print(json.dumps(dict(status='prepared-unrun-read-only-recovery',packet=str(PACKET),sha256=sha(payload),
        files=len(reader.records),logical_bytes=sum(r['size'] for r in reader.records.values()),retirement=False)))

if __name__=='__main__':main()
