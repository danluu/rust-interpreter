"""One pinned read-only recovery child; no cleanup or other process creation."""
import argparse
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
OUTPUT=OWNER/'.work/retained-proof-copy-recovery-01.json'

def require(ok,message):
    if not ok:raise RuntimeError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main(expected):
    require(Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize,'fixed recovery child route')
    raw=PACKET.read_bytes();require(sha(raw)==expected and len(raw)<=16*2**20,'exact reviewed recovery packet')
    packet=json.loads(raw)
    require(packet['status']=='prepared-unrun-read-only-recovery' and packet['output']==str(OUTPUT)
            and not OUTPUT.exists() and not OUTPUT.is_symlink(),'fresh exact recovery result')
    source=HERE/'recovery.py';body=source.read_bytes()
    require(sha(body)==packet['recovery_source_sha256']==packet['sources'][str(source)]['sha256'],'frozen recovery source')
    module=types.ModuleType('_exact_copy_recovery');module.__file__=str(source)
    exec(compile(body,str(source),'exec'),module.__dict__)
    require(module.same(packet['limits'],module.LIMITS),'unchanged recovery limits')
    packet_identity=module.identity(PACKET)
    def guard():
        require(shutil.disk_usage(OWNER).free>=9*2**30,'recovery live capacity')
        require(module.identity(PACKET)==packet_identity and PACKET.resolve(strict=True)==PACKET,'recovery packet changed')
    for name,row in packet['files'].items():
        require(module.identity(name)==row['identity'] and Path(name).resolve(strict=True)==Path(name),'exact recovery input route/identity')
    # The verifier hashes every recovery payload itself. Only bounded executable
    # sources and the helper-control audit are extra packet rows.
    reader=module.Reader(guard)
    for name,row in packet['sources'].items():reader.file(name,row)
    audit=reader.json(packet['helper40_audit']['path'],packet['helper40_audit']['sha256'])
    require(audit['status']=='verified' and audit['controls']==40,'actual40 qualification retained')
    report=module.verify(guard)
    combined={**reader.records,**report['current_file_records']}
    require(module.same(combined,packet['files']),'complete actual recovery/file freeze equality')
    setup_read_bytes=2*len(raw)+len(body)
    require(report['total_read_bytes']+reader.bytes+setup_read_bytes<=module.LIMITS['maximum_total_read_bytes'],'complete child cumulative read bound')
    require(sha(PACKET.read_bytes())==expected,'recovery packet changed at closure')
    for name,row in packet['files'].items():require(module.identity(name)==row['identity'],'recovery inputs changed before closure')
    report.update(inputs_sha256=expected,pid=os.getpid(),parent_pid=os.getppid(),
        helper40_audit=packet['helper40_audit'],extra_source_read_bytes=reader.bytes,setup_read_bytes=setup_read_bytes,
        current_file_records=combined,complete_frozen_input_readback=True,compiler_calls=0,child_processes=0)
    payload=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode();require(len(payload)<=module.LIMITS['maximum_output_bytes'],'finite recovery report')
    with OUTPUT.open('xb') as out:out.write(payload);out.flush();os.fsync(out.fileno())
    require(OUTPUT.read_bytes()==payload,'complete recovery report readback')
    fd=os.open(OUTPUT.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)
    print(json.dumps(dict(status=report['status'],result=str(OUTPUT),result_sha256=sha(payload),selected_files=21,
        preserved_files=40,archive_members=1191,full_gzip_eof=True,retirement=False)))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True)
    main(parser.parse_args().inputs_sha256)
