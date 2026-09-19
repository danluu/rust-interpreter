"""One exact closed failed staging prefix; no chmod or other tree retirement."""
import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path
import stat
import sys
import tarfile
import time

HERE=Path(__file__).resolve().parent
OWNER=HERE.parents[1]
TARGET=OWNER/'.work/compilers/.install-8j_ugjr3'
PRESERVED=OWNER/'.work/compilers/60096d7efe02d38269c5694bfd046d4f9facfb65139b2d82173d12345a1c9c46'
PUBLISHED=OWNER/'.work/compilers/e48e40e180efbcad9366decdfef2f1152f0a54fb0e78fb865550a64056e84723'
COMPARISON=OWNER/'.work/root-old-compiler-copy-comparison-03.json'
HISTORY=OWNER/'.work/root-old-compiler-retirement-history-01'
WORK=OWNER/'.work/old-compiler-partial-retirement-01'
PACKET=HERE/'plan-01'
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
GIB,MIB=2**30,2**20
sys.path.insert(0,str(A/'experiments/runtime-application-admission'))
import runtime_platform
import bounded_probes
import fd_remove
owned=bounded_probes.owned


def require(ok,message):
    if not ok:raise RuntimeError(message)


def read(path):
    path=Path(path);require(path.stat().st_size<=96*MIB,'bounded JSON required')
    return json.loads(path.read_bytes())


def identity(path):return fd_remove.identity(Path(path).lstat())


def capacity():
    free=owned.disk(OWNER,9)
    if WORK.exists():require(bounded_probes.allocated(WORK)['bytes']<=256*MIB,'evidence allocation exceeds bound')
    return free


def sha(path):
    path=Path(path);before=identity(path)
    require(stat.S_ISREG(before['mode']) and path.resolve(strict=True)==path and before['size']<=512*MIB,'ordinary bounded input required: '+str(path))
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW);h=hashlib.sha256()
    with os.fdopen(fd,'rb') as stream:
        require(fd_remove.identity(os.fstat(stream.fileno()))==before,'opened file differs')
        for block in iter(lambda:stream.read(8*MIB),b''):
            owned.disk(OWNER,9);h.update(block)
        require(fd_remove.identity(os.fstat(stream.fileno()))==before,'file changed during hashing')
    require(identity(path)==before,'file path changed during hashing')
    return h.hexdigest()


def file(path):return dict(identity=identity(path),sha256=sha(path))


def inventory(root):
    root=Path(root);require(root.resolve(strict=True)==root and stat.S_ISDIR(root.lstat().st_mode),'ordinary root required')
    result={'.':dict(kind='directory',identity=identity(root))};total=0
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in sorted(dirs+files):
            path=Path(parent)/name;s=identity(path)
            require(path.resolve(strict=True)==path,'indirect inventory entry')
            if stat.S_ISDIR(s['mode']):row=dict(kind='directory',identity=s)
            else:
                require(stat.S_ISREG(s['mode']) and s['nlink']==1,'special or shared inventory file')
                row=dict(kind='file',**file(path));total+=s['size'];require(total<=2*GIB,'tree logical-byte bound')
            result[str(path.relative_to(root))]=row;require(len(result)<=10000,'tree entry bound')
    return result


def compared_rows():
    comparison=read(COMPARISON)
    require(comparison['status']=='verified-read-only-equal-payload-comparison-not-retirement'
        and comparison['all_payloads_retained_at_replacement'] is True and comparison['external_hardlinks']==comparison['deletions']==0,
        'historical comparison differs')
    require(comparison['preserved_replacement']==str(PRESERVED),'replacement route differs')
    target=comparison['targets'][str(TARGET)]
    require(not target['sole_metadata_to_retain'] and len(target['files'])==6982,'partial prefix has unique metadata')
    rows={'.':dict(kind='directory',identity=target['root_identity'])}
    for name,row in target['members'].items():
        row=json.loads(json.dumps(row))
        if row['kind']=='file':
            proof=target['files'][str(TARGET/name)];preserved=Path(proof['preserved_equal_payload'])
            require(preserved==PRESERVED/name and proof['identity']==row['identity'],'comparison relative association differs')
            keep=comparison['preserved_files'][str(preserved)]
            require(keep['sha256']==proof['sha256'] and keep['identity']['size']==row['identity']['size'],'preserved payload equality differs')
            require(bool(keep['identity']['mode']&0o111)==bool(row['identity']['mode']&0o111),'executable class differs')
            row['sha256']=proof['sha256']
        else:require(row['kind']=='directory' and stat.S_IMODE(row['identity']['mode'])==0o700,'unreviewed directory permission')
        rows[name]=row
    require(len(rows)==8388 and sum(row['kind']=='directory' for row in rows.values())==1406
        and stat.S_IMODE(rows['.']['identity']['mode'])==0o700,'unexpected partial-prefix shape')
    return rows


def archive_history():
    manifest_raw=(HISTORY/'members.json').read_bytes();manifest=json.loads(manifest_raw)
    summary=read(HISTORY/'summary.json');audit=read(HISTORY/'full-archive-verification-02.json')
    require(summary['retained_compiler_copy']==str(TARGET) and summary['archive_sha256']==sha(HISTORY/'evidence.tar.xz')
        ==audit['archive_sha256']=='97898061418b8a1f9e078e26418c9f45f14e566773f33af34c0425718c93b908', 'closed failure archive association differs')
    require(audit['status']=='verified-read-only-old-task-archive' and audit['full_member_bytes_and_xz_eof_verified'] is True,'full prior archive audit required')
    seen={};total=0
    with tarfile.open(HISTORY/'evidence.tar.xz','r|xz') as archive:
        for member in archive:
            capacity();require(member.isfile() and member.name not in seen and member.size<=16*MIB,'unexpected archive member')
            raw=archive.extractfile(member).read(member.size+1);require(len(raw)==member.size,'truncated member')
            if member.name=='MEMBERS.json':require(raw==manifest_raw,'embedded member manifest differs')
            else:require(member.name in manifest and member.size==manifest[member.name]['size']
                    and hashlib.sha256(raw).hexdigest()==manifest[member.name]['sha256'],'archive payload differs')
            seen[member.name]=raw;total+=len(raw);require(total<=32*MIB and len(seen)<=128,'archive logical bound')
    require(set(seen)==set(manifest)|{'MEMBERS.json'} and len(seen)==52 and total==audit['logical_bytes'],'archive membership differs')
    expanded=0
    with lzma.open(HISTORY/'evidence.tar.xz','rb') as stream:
        for block in iter(lambda:stream.read(MIB),b''):
            capacity();expanded+=len(block);require(expanded<=40*MIB,'expanded archive bound')
    require(expanded==audit['expanded_bytes']==6021120,'archive full EOF length differs')
    decode=lambda name:json.loads(seen[name])
    history=[];pids=set()
    for label,rc in [('pipeline-01/custom-compiler-install-01',1),('pipeline-02/custom-compiler-install-02',0),('pipeline-02/custom-compiler-tools-01',1)]:
        child,result,plan=[decode(label+suffix+'.json') for suffix in ['-child','-result','-plan']]
        require(child['status']=='finished' and result['status']==('passed' if rc==0 else 'failed')
            and child['returncode']==result['returncode']==rc and child['pid']==result['pid']
            and child['parent_pid']==result['supervisor_pid'] and child['command']==plan['command']
            and child['cwd']==str(OWNER) and result['root']==str(OWNER)
            and result['started_at']<=child['started_at']<=child['finished_at']<=result['finished_at']
            and hashlib.sha256(seen[label+'-plan.json']).hexdigest()==result['plan_sha256'],'closed installer history differs')
        pids.update([child['pid'],child['parent_pid'],result['parent_pid']])
        history.append(dict(label=label,child=child,result=result,plan_sha256=result['plan_sha256'],
            stdout_sha256=hashlib.sha256(seen[label+'.stdout']).hexdigest(),stderr_sha256=hashlib.sha256(seen[label+'.stderr']).hexdigest()))
    require(history[0]['child']['pid']==92592 and history[0]['child']['returncode']==1,'original failed installer differs')
    return dict(archive_sha256=audit['archive_sha256'],members=52,expanded_bytes=expanded,full_member_and_xz_eof=True,
        closed_histories=history,closed_pids=sorted(pids),limitation='Historical PID numbers are used only for read-only absence checks; no process control or inferred identity reuse.')


def contains_target(value):
    if isinstance(value,str):return str(TARGET) in value
    if isinstance(value,dict):return any(contains_target(k) or contains_target(v) for k,v in value.items())
    if isinstance(value,list):return any(contains_target(v) for v in value)
    return False


class Retirement:
    def __init__(self,digest):
        require(Path.cwd()==OWNER and sys.dont_write_bytecode and not sys.flags.optimize,'fixed owner/Python flags required')
        require(sha(PACKET/'inputs.json')==digest,'freeze hash differs')
        self.freeze=read(PACKET/'inputs.json');self.plan=read(PACKET/'plan.json')
        require(self.freeze['plan_sha256']==sha(PACKET/'plan.json'),'plan hash differs')
        require(self.plan['root']==str(TARGET) and str(Path(sys.executable).resolve(strict=True))==self.plan['python']
            and dict(os.environ)==self.plan['environment'],'fixed root/environment differs')
        self.guard();require(not WORK.exists() and not WORK.is_symlink(),'fresh evidence required');WORK.mkdir()
        self.record=dict(status='waiting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),children=[],
            inputs_sha256=digest,plan_sha256=sha(PACKET/'plan.json'),compiler_calls=0,benchmark=False)
        self.save()

    def save(self):owned.write(WORK/'receipt.json',self.record)

    def guard(self):
        runtime_platform.validate(list(os.uname()),self.plan['platform_identity'])
        for path,row in self.freeze['files'].items():require(file(path)==row,'frozen preservation/input changed: '+path)
        for path,row in self.plan['routes'].items():
            require(str(Path(path).resolve(strict=True))==row['resolved'] and identity(path)==row['identity'],'frozen route differs')
        for path in self.plan['consumer_absences']:require(not Path(path).exists() and not Path(path).is_symlink(),'consumer packet appeared')
        for path in self.plan['consumer_records']:require(not contains_target(read(path)),'current consumer references retired prefix')
        control=read(self.plan['controls']['receipt']);audit=read(self.plan['controls']['audit'])
        require(control['status']=='passed' and control['controls_passed']==12 and audit['status']=='verified'
            and audit['receipt_sha256']==sha(self.plan['controls']['receipt'])
            and control['inputs_sha256']==sha(self.plan['controls']['inputs']),'qualified removal fixture history differs')
        tested=read(self.plan['controls']['inputs'])['files'][self.plan['controls']['tested_helper']]['sha256']
        require(tested==sha(self.plan['controls']['tested_helper'])==sha(HERE/'fd_remove.py')
            =='0b154792e3b393bdc018a6ee4337347535be466db64aa3fa40cd6a3899be6041','actual tested removal helper differs')
        require(archive_history()==self.plan['closed_history'],'closed historical archive differs')

    def protected(self,retired=False):
        require(set(os.listdir(TARGET.parent))==set(self.plan['outer_children'])-({TARGET.name} if retired else set()),'compiler parent membership differs')
        require(all(identity(TARGET.parent)[k]==self.plan['outer_identity'][k] for k in ['dev','ino','mode']),'compiler parent route differs')
        for path,row in self.plan['protected_directories'].items():
            require(identity(path)==row['identity'] and sorted(os.listdir(path))==row['children'],'protected directory changed: '+path)

    def probe(self,spec,fd):
        output=WORK/'commands'/spec['label']
        try:
            child=bounded_probes.run(spec['argv'],cwd=OWNER,environment=self.plan['environment'],output=output,canonical_fd=fd,expected=tuple(spec['expected']))
        finally:
            if (output/'receipt.json').exists():
                child=read(output/'receipt.json');self.record['children'].append(dict(path=str(output/'receipt.json'),sha256=sha(output/'receipt.json'),pid=child.get('pid'),label=spec['label']));self.save()
        require(child['returncode']==1 and not (output/'stdout').read_bytes() and not (output/'stderr').read_bytes(),
            'quiescence refused: open handles, live historical PID, or probe diagnostic')

    def run(self):
        try:
            with owned.workload_lock(owned.CANONICAL_LOCK,600) as fd:
                free=capacity();require(free>=9*GIB+256*MIB,'entry reservation unavailable')
                self.record.update(status='running',admitted_at=time.time(),free_bytes_before=free);self.save()
                self.guard();self.protected();rows=inventory(TARGET)
                require(rows==compared_rows()==read(PACKET/'inventory.json') and identity(TARGET.parent)==self.plan['outer_identity'],'current target differs')
                owned.write(WORK/'admitted-inventory.json',rows);owned.write(WORK/'transition.json',self.plan['transition'])
                (WORK/'commands').mkdir()
                for spec in self.plan['commands']:self.probe(spec,fd)
                self.guard();self.protected();require(inventory(TARGET)==rows and identity(TARGET.parent)==self.plan['outer_identity'],'target drift after quiescence')
                with (WORK/'deleted.jsonl').open('xb'):pass
                try:removed=fd_remove.remove_tree(TARGET,rows,self.plan['outer_identity'],WORK/'deleted.jsonl',capacity)
                finally:self.record['ledger']=fd_remove.ledger_summary(WORK/'deleted.jsonl');self.save()
                require(not TARGET.exists() and not TARGET.is_symlink(),'target root remains')
                self.protected(retired=True);self.guard();ledger=self.record['ledger']
                require(all(set(ledger[k])==set(rows) and len(ledger[k])==len(rows) for k in ['intent','unlinked','validated'])
                    and not ledger['uncertain'] and ledger['readback_error'] is None,'incomplete durable removal ledger')
                require(removed==dict(removed_entries=8388,files=6982,directories=1406,root_absent=True),'removed scope differs')
                self.record.update(status='passed',removed=removed,ledger_sha256=sha(WORK/'deleted.jsonl'),transition_sha256=sha(WORK/'transition.json'),
                    free_bytes_after=capacity(),preserved_payload_files=6982,actual_readonly_probes=2,chmod_calls=0)
        except BaseException as error:self.record.update(status='failed',error=repr(error));raise
        finally:self.record['finished_at']=time.time();self.save()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True)
    Retirement(parser.parse_args().inputs_sha256).run()
