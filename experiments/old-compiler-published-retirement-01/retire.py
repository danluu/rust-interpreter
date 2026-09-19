"""One exact superseded compiler prefix; qualified directory-only mode transition."""
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
PARTIAL=OWNER/'.work/compilers/.install-8j_ugjr3'
TARGET=OWNER/'.work/compilers/e48e40e180efbcad9366decdfef2f1152f0a54fb0e78fb865550a64056e84723'
PRESERVED=OWNER/'.work/compilers/60096d7efe02d38269c5694bfd046d4f9facfb65139b2d82173d12345a1c9c46'
MODE_SOURCE=OWNER/'experiments/old-compiler-directory-modes-01'
COMPARISON=OWNER/'.work/root-old-compiler-copy-comparison-03.json'
HISTORY=OWNER/'.work/root-old-compiler-retirement-history-01'
WORK=OWNER/'.work/old-compiler-published-retirement-01'
PACKET=HERE/'plan-01'
A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
X=Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
O=Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
GIB,MIB=2**30,2**20
sys.path.insert(0,str(A/'experiments/runtime-application-admission'))
import runtime_platform
import bounded_probes
import fd_remove
sys.path.insert(0,str(MODE_SOURCE))
import directory_modes
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
    require(target['sole_metadata_to_retain']==[str(TARGET/'ready.json')] and len(target['files'])==6983,'published unique metadata differs')
    rows={'.':dict(kind='directory',identity=target['root_identity'])}
    for name,row in target['members'].items():
        row=json.loads(json.dumps(row))
        if row['kind']=='file':
            proof=target['files'][str(TARGET/name)]
            if name=='ready.json':
                require(proof['identity']==row['identity'] and proof['sha256']=='ff93b6ae55e28406d6c88d0c1bc680f46ecae7f14014f54b83e84a8b34edaeda','unique ready metadata differs')
                row['sha256']=proof['sha256'];rows[name]=row;continue
            preserved=Path(proof['preserved_equal_payload'])
            require(preserved==PRESERVED/name and proof['identity']==row['identity'],'comparison relative association differs')
            keep=comparison['preserved_files'][str(preserved)]
            require(keep['sha256']==proof['sha256'] and keep['identity']['size']==row['identity']['size'],'preserved payload equality differs')
            require(keep['identity']['mode']==row['identity']['mode'],'published payload mode differs')
            row['sha256']=proof['sha256']
        else:require(row['kind']=='directory' and stat.S_IMODE(row['identity']['mode'])==0o555,'unreviewed directory permission')
        rows[name]=row
    require(len(rows)==8389 and sum(row['kind']=='directory' for row in rows.values())==1406
        and stat.S_IMODE(rows['.']['identity']['mode'])==0o700,'unexpected published-prefix shape')
    return rows


def archive_history():
    manifest_raw=(HISTORY/'members.json').read_bytes();manifest=json.loads(manifest_raw)
    summary=read(HISTORY/'summary.json');audit=read(HISTORY/'full-archive-verification-02.json')
    require(summary['retained_compiler_copy']==str(PARTIAL) and summary['installed_compiler_key']==TARGET.name and summary['archive_sha256']==sha(HISTORY/'evidence.tar.xz')
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
        mode=self.plan['mode_controls'];control=read(mode['receipt']);audit=read(mode['audit']);tested=read(mode['inputs'])
        require(control['status']=='passed' and control['controls_passed']==audit['controls']==10 and audit['status']=='verified'
            and audit['receipt_sha256']==sha(mode['receipt']) and audit['inputs_sha256']==control['inputs_sha256']==sha(mode['inputs']),
            'qualified directory-mode history differs')
        require(tested['files'][str(MODE_SOURCE/'directory_modes.py')]['sha256']==sha(MODE_SOURCE/'directory_modes.py')
            =='5767a2c81f76d6a53b26ba00851b09f10d439f358f387bf839c895b07ac341d6'
            and tested['files'][str(OWNER/'experiments/old-compiler-partial-retirement-01/fd_remove.py')]['sha256']==sha(HERE/'fd_remove.py'),
            'mode helper or tested removal helper differs')
        prior=self.plan['partial_retirement'];terminal=read(prior['receipt']);audit=read(prior['audit'])
        require(terminal['status']=='passed' and audit['status']=='verified' and audit['receipt_sha256']==sha(prior['receipt'])
            and audit['retired_entries']==8388 and audit['all_durable_events_replayed'] is True
            and not PARTIAL.exists() and not PARTIAL.is_symlink(),'closed partial retirement differs')
        require(sha(PACKET/'preserved-ready.json')==self.plan['ready']['sha256'],'durable unique ready copy differs')
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
                raw=(PACKET/'preserved-ready.json').read_bytes()
                require(hashlib.sha256(raw).hexdigest()==rows['ready.json']['sha256']==self.plan['ready']['sha256'],
                    'unique ready copy bytes differ')
                with (WORK/'preserved-ready.json').open('xb') as stream:
                    require(stream.write(raw)==len(raw),'short metadata retention write');stream.flush();os.fsync(stream.fileno())
                directory_fd=os.open(WORK,fd_remove.DIRECTORY_FLAGS)
                try:os.fsync(directory_fd)
                finally:os.close(directory_fd)
                require(sha(WORK/'preserved-ready.json')==rows['ready.json']['sha256'],'retained unique ready readback differs')
                with (WORK/'directory-modes.jsonl').open('xb'):pass
                writable,mode_result=directory_modes.make_writable(TARGET,rows,self.plan['outer_identity'],WORK/'directory-modes.jsonl',capacity)
                require(mode_result==dict(changed_directories=1405,chmod_calls=1405,changed_files=0,changed_root=False),
                    'mode transition scope differs')
                require(inventory(TARGET)==writable,'post-mode complete bytes or membership differ')
                owned.write(WORK/'writable-inventory.json',writable)
                self.record.update(mode_transition=mode_result,mode_ledger_sha256=sha(WORK/'directory-modes.jsonl'),
                    writable_inventory_sha256=sha(WORK/'writable-inventory.json'));self.save()
                self.protected();self.guard()
                with (WORK/'deleted.jsonl').open('xb'):pass
                try:removed=fd_remove.remove_tree(TARGET,writable,self.plan['outer_identity'],WORK/'deleted.jsonl',capacity)
                finally:self.record['ledger']=fd_remove.ledger_summary(WORK/'deleted.jsonl');self.save()
                require(not TARGET.exists() and not TARGET.is_symlink(),'target root remains')
                self.protected(retired=True);self.guard();ledger=self.record['ledger']
                require(all(set(ledger[k])==set(rows) and len(ledger[k])==len(rows) for k in ['intent','unlinked','validated'])
                    and not ledger['uncertain'] and ledger['readback_error'] is None,'incomplete durable removal ledger')
                require(removed==dict(removed_entries=8389,files=6983,directories=1406,root_absent=True),'removed scope differs')
                self.record.update(status='passed',removed=removed,ledger_sha256=sha(WORK/'deleted.jsonl'),transition_sha256=sha(WORK/'transition.json'),
                    free_bytes_after=capacity(),preserved_payload_files=6982,actual_readonly_probes=2,chmod_calls=1405,changed_files=0,changed_root=False,
                    unique_ready_sha256=sha(WORK/'preserved-ready.json'))
        except BaseException as error:self.record.update(status='failed',error=repr(error));raise
        finally:
            for name in ['directory-modes.jsonl','deleted.jsonl']:
                path=WORK/name
                if path.exists():self.record.setdefault('retained_ledgers',{})[name]=dict(path=str(path),bytes=path.stat().st_size)
            self.record['finished_at']=time.time();self.save()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--inputs-sha256',required=True)
    Retirement(parser.parse_args().inputs_sha256).run()
