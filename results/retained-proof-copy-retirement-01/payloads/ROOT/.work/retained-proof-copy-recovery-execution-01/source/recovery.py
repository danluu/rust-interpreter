"""Unrun bounded recovery reader for exactly 21 closed run-make proof copies.

No filesystem action occurs at import. verify() performs read-only full recovery;
its caller owns reviewed admission, time/CPU/output caps and retained execution.
No archive is extracted, no source helper is imported and no path is virtualized.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import tarfile
import time

R = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
O = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918')
X = Path('/Users/danluu/dev/rust-interp-runtime-exporter-20260918')
PROPOSAL = X/'.work/runtime04-retained-copy-retirement-proposal-01.json'
PROPOSAL_SHA = 'e0599d87ab842b9e18932fddb54bb63aaf850cd2366279f67507e875731b3481'
DESIGN_SHA = 'dc7965e9f7a21bdcb0ac31af4d7dce5f8a57e0d6f99e8890b7764ebb53dc13e0'
STAGE = R/'experiments/hir-options-hash-driver-stage-03'
STAGE_INPUTS_SHA = 'c06e016829f0c98e579aace635ded04858ac8890ebe43bb6014d1f4df52aa010'
TARGET = O/'.work/hir-options-hash-run-make-01/retained'
CONTROLS_AUDIT = R/'.work/retained-proof-copy-controls-independent-verification-01.json'
CONTROLS_AUDIT_SHA = 'c803f6e6e663c3fc8a081829e3c07deb9098692206a91269c36b2fe6fc08290a'
FIELDS = ('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
MIB = 2**20
LIMITS = dict(maximum_file_bytes=64*MIB, maximum_archive_bytes=64*MIB,
              maximum_archive_members=1536, maximum_archive_logical_bytes=384*MIB,
              maximum_archive_expanded_bytes=392*MIB, maximum_total_read_bytes=2**30,
              maximum_output_bytes=16*MIB, wall_seconds=600, cpu_seconds=300)

def require(ok, message):
    if not ok: raise RuntimeError(message)

def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()

def same(a,b): return encoded(a) == encoded(b)
def digest(raw): return hashlib.sha256(raw).hexdigest()
def identity(path): return stamp(Path(path).lstat())
def stamp(info): return {key:getattr(info,'st_'+key) for key in FIELDS}

def unique(pairs):
    value = {}
    for key,item in pairs:
        require(key not in value,'duplicate JSON key'); value[key] = item
    return value

class Reader:
    def __init__(self, guard):
        self.guard = guard; self.started = time.monotonic(); self.bytes = 0
        self.records = {}

    def tick(self, count=0):
        self.bytes += count
        require(self.bytes <= LIMITS['maximum_total_read_bytes'],'total recovery read bound')
        require(time.monotonic()-self.started <= LIMITS['wall_seconds'],'recovery wall bound')
        self.guard()

    def route(self,path):
        path=Path(path)
        require(path.is_absolute() and '..' not in path.parts and path.resolve(strict=True)==path,'ordinary canonical recovery route')
        for parent in reversed(path.parents):
            require(stat.S_ISDIR(parent.lstat().st_mode) and not parent.is_symlink(),'ordinary recovery ancestor')
        return path

    def opened(self,path,expected=None):
        self.tick(); path=self.route(path); before=identity(path)
        require(stat.S_ISREG(before['mode']) and before['size']<=LIMITS['maximum_file_bytes'],'bounded ordinary recovery file')
        if expected is not None:
            require(same(before,expected['identity']) and before['size']==expected['size'],'exact current recovery identity')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
        try: require(stamp(os.fstat(fd))==before,'opened recovery file differs')
        except BaseException: os.close(fd); raise
        return path,before,os.fdopen(fd,'rb')

    def final(self,path,before,stream):
        require(stamp(os.fstat(stream.fileno()))==before and identity(path)==before,'recovery source changed')
        self.route(path); self.tick()

    def file(self,path,expected=None,keep=False):
        path,before,stream=self.opened(path,expected); h=hashlib.sha256(); raw=[]
        with stream:
            while block:=stream.read(MIB):
                self.tick(len(block)); h.update(block)
                if keep:raw.append(block)
            self.final(path,before,stream)
        row=dict(identity=before,size=before['size'],sha256=h.hexdigest())
        if expected is not None:require(same(row,expected),'complete current recovery bytes differ')
        require(str(path) not in self.records or same(self.records[str(path)],row),'recovery file changed between reads')
        self.records[str(path)]=row
        return b''.join(raw) if keep else row

    def json(self,path,sha256=None):
        raw=self.file(path,keep=True)
        require(sha256 is None or digest(raw)==sha256,'bound recovery JSON differs')
        return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))

    def reference(self,ref):
        value=self.json(ref['path'],ref['sha256'])
        require(self.records[ref['path']]['size']==ref['bytes'],'bound metadata byte count differs')
        return value

    def gzip(self,path,expected,logical_sha256,logical_bytes):
        self.file(path,expected)
        path,before,stream=self.opened(path,expected); h=hashlib.sha256(); size=0
        with stream:
            with gzip.GzipFile(fileobj=stream,mode='rb') as logical:
                while block:=logical.read(MIB):
                    self.tick(len(block));size+=len(block)
                    require(size<=logical_bytes<=LIMITS['maximum_file_bytes'],'bounded exact logical gzip length')
                    h.update(block)
            self.final(path,before,stream)
        require(size==logical_bytes and h.hexdigest()==logical_sha256,'full gzip EOF/logical digest differs')
        return dict(path=str(path),compressed_sha256=expected['sha256'],compressed_bytes=expected['size'],
                    logical_sha256=logical_sha256,logical_bytes=size,full_gzip_eof=True)

    def archive(self,ref,manifest):
        path=Path(ref['path']); actual=self.file(path)
        require(actual['sha256']==ref['sha256'] and actual['size']==ref['bytes']<=LIMITS['maximum_archive_bytes'],'exact recovery archive bytes')
        members=manifest['members'];require(len(members)==1191<=LIMITS['maximum_archive_members'],'complete original archive membership')
        require(sum(v['bytes'] for v in members.values())==248356749<=LIMITS['maximum_archive_logical_bytes'],'complete original archive logical bytes')
        # First consume the entire compressed stream through its trailer with a
        # finite expanded bound. Tar's end marker alone never proves gzip EOF.
        path,before,stream=self.opened(path,actual);expanded=0
        with stream:
            with gzip.GzipFile(fileobj=stream,mode='rb') as logical:
                while block:=logical.read(MIB):
                    self.tick(len(block));expanded+=len(block)
                    require(expanded<=LIMITS['maximum_archive_expanded_bytes'],'expanded archive cap')
            self.final(path,before,stream)
        seen={};total=0
        path,before,stream=self.opened(path,actual)
        with stream:
            with tarfile.open(fileobj=stream,mode='r|gz') as archive:
                for member in archive:
                    self.tick()
                    require(member.isfile() and not member.issym() and not member.islnk() and member.name in members
                            and member.name not in seen and 0<=member.size<=LIMITS['maximum_file_bytes'],'exact ordinary archive member')
                    wanted=members[member.name];require(member.size==wanted['bytes'],'archive member size differs')
                    h=hashlib.sha256();n=0;payload=archive.extractfile(member)
                    require(payload is not None,'missing archive member data')
                    with payload:
                        while block:=payload.read(MIB):self.tick(len(block));n+=len(block);require(n<=member.size,'member overrun');h.update(block)
                    require(n==member.size and h.hexdigest()==wanted['sha256'],'full archive member hash differs')
                    seen[member.name]=dict(bytes=n,sha256=h.hexdigest());total+=n
                    require(len(seen)<=LIMITS['maximum_archive_members'] and total<=LIMITS['maximum_archive_logical_bytes'],'archive count/logical cap')
            self.final(path,before,stream)
        require(same(seen,members),'complete archive map differs')
        self.file(path,actual)
        return dict(sha256=actual['sha256'],bytes=actual['size'],members=len(seen),logical_bytes=total,
                    expanded_bytes=expanded,full_member_readback=True,full_gzip_eof=True)

def target_inventory(reader,expected):
    reader.route(TARGET);before=identity(TARGET)
    require(stat.S_ISDIR(before['mode']) and same(before,expected['.']['identity']),'exact retained directory identity')
    names=sorted(os.listdir(TARGET));require(names==sorted(set(expected)-{'.'}),'exact retained directory membership')
    for name in names:
        require('/' not in name and expected[name]['kind']=='file','only ordinary direct copies')
        row=expected[name]
        reader.file(TARGET/name,dict(identity=row['identity'],size=row['identity']['size'],sha256=row['sha256']))
    require(identity(TARGET)==before and sorted(os.listdir(TARGET))==names,'retained directory changed while hashing')
    return dict(root_identity=before,files=len(names),logical_bytes=sum(expected[n]['identity']['size'] for n in names))

def metadata(reader):
    p=reader.json(PROPOSAL,PROPOSAL_SHA);d=reader.reference(p['design'])
    require(p['design']['sha256']==DESIGN_SHA and p['target_root']==str(TARGET),'exact reviewed proposal/design')
    require(p['selected']==sorted(set(p['selected'])) and len(p['selected'])==21 and len(p['complete_inventory'])==62,'exact 61/21 scope')
    require(p['retained_ordinary_files']==40 and p['retained_directories']==1 and p['logical_bytes']==25677060,'exact retained scope')
    docs={r['path']:reader.reference(r) for r in d['references']}
    wire=docs[str(STAGE/'inputs.json')];require(reader.records[str(STAGE/'inputs.json')]['sha256']==STAGE_INPUTS_SHA,'original compact input binding')
    base=docs[wire['file_table_base']['path']]
    require(not set(base['files'])&set(wire['files']) and reader.records[wire['file_table_base']['path']]['sha256']==wire['file_table_base']['sha256'],'disjoint exact historical base')
    full=dict(base['files'],**wire['files']);integrity=dict(count=len(full),total_bytes=sum(r['size'] for r in full.values()),sha256=digest(encoded(full)))
    require(same(integrity,wire['file_table_integrity']) and len(full)==109343,'complete historical full table integrity')
    selected={str(TARGET/n) for n in p['selected']};require(selected<=set(wire['files']) and not selected&set(base['files']),'copies must remain delta-only')
    require(not selected&set(wire['snapshot_inputs']),'cannot retire original snapshot input')
    for name,doc in docs.items():
        if name.endswith('/source-snapshots.json') or name.endswith('/compiler-metadata-03/inputs.json'):
            require(not selected&set(doc['files']),'cannot retire live metadata or selected logical bytes')
    owner={k:reader.reference(v) for k,v in p['retention_owner'].items()}
    retained=owner['retained_inputs'];entries={r['retained']:r for r in retained['files']}
    require(retained['status']=='retained' and len(entries)==len(retained['files'])==61 and retained['logical_bytes']==27196941,'complete retained-inputs manifest')
    require({str(TARGET/n) for n in p['complete_inventory'] if n!='.'}==set(entries),'full manifest/target association')
    for name,entry in entries.items():
        item=p['complete_inventory'][Path(name).name]
        require(item['kind']=='file' and item['sha256']==entry['sha256']
                and item['identity']['size']==entry['bytes'],'all 61 manifest/inventory byte associations')
    require(owner['audit']['status']=='verified' and owner['receipt']['status']==owner['result']['status']=='passed','closed retention owner required')
    require(owner['audit']['receipt_sha256']==p['retention_owner']['receipt']['sha256']
            and owner['audit']['result_sha256']==owner['receipt']['result_sha256']==p['retention_owner']['result']['sha256']
            and owner['result']['retained_inputs_sha256']==p['retention_owner']['retained_inputs']['sha256'],'retention proof hash association')
    old_archive=reader.reference(p['archived_recovery']['manifest']);archive_audit=reader.reference(p['archived_recovery']['audit'])
    require(archive_audit['status']=='verified' and archive_audit['all_member_hashes_and_full_gzip_trailer_verified'] is True
            and archive_audit['archive_sha256']==p['archived_recovery']['archive']['sha256']
            and archive_audit['manifest_sha256']==p['archived_recovery']['manifest']['sha256'],'closed archive recovery proof')
    audit=reader.reference(p['hash_owner_audit']);require(audit['status']=='verified' and audit['hash_driver_qualified'] is True
            and audit['inputs_sha256']==STAGE_INPUTS_SHA,'successful hash02 proof retained')
    prior=docs[str(STAGE/'plan.json')]['remainder']['snapshot_reuse']
    require(len(prior['records'])==464,'exact nonrecursive predecessor catalog')
    catalog={r['path']:r for r in prior['records']};require(len(catalog)==464,'unique predecessor physical catalog')
    details={r['copy']:r for r in d['proposed_historical_copies']}
    require(set(details)==selected=={r['path'] for r in p['recovery']},'exact recovery selection')
    for item in p['recovery']:
        name=item['path'];old=full[name];entry=entries[name];detail=details[name]
        require(Path(name).parent==TARGET and old['identity']['nlink']==1 and old['identity']['mode']&0o111==0
                and stat.S_ISREG(old['identity']['mode']),'ordinary non-executable copy only')
        require(same(old,item['original_record']) and same(old,detail['historical_record'])
                and same(entry,item['retention_entry']) and same(entry,detail['retained_manifest_row']),'historical identity/mapping differs')
        require(entry['sha256']==old['sha256'] and entry['bytes']==old['size'],'copy retention bytes differ')
        original=full[entry['source']]
        require(entry['source'] not in selected and same(original,detail['current_original_record'])
                and original['sha256']==old['sha256'] and original['size']==old['size'],'current original source required')
        physical=item['physical_witness'];witness=catalog[physical]
        require(physical not in selected and same(witness['blob'],item['snapshot_witness'])
                and same(witness['blob'],detail['qualified_blob'])
                and same(detail['qualified_storage'],dict(kind='reused',path=physical)),'prior catalog witness association')
        require(same(full[physical],dict(identity=witness['identity'],size=witness['blob']['compressed_bytes'],sha256=witness['blob']['sha256'])),'physical witness current table association')
        require(witness['blob']['logical_sha256']==old['sha256'] and witness['blob']['logical_bytes']==old['size'],'full witness logical equality')
        require(same(old_archive['members'][name.lstrip('/')],dict(bytes=old['size'],sha256=old['sha256'])),'archive copy member association')
    return p,full,old_archive,catalog

def verify(guard):
    """Called only by a separately reviewed, explicitly recorded admission wrapper."""
    started=time.time();reader=Reader(guard);p,full,manifest,catalog=metadata(reader)
    require(identity(TARGET.parent)==p['outer_parent_identity'],'outer parent changed')
    target_inventory(reader,p['complete_inventory'])
    archive=reader.archive(p['archived_recovery']['archive'],manifest)
    witnesses=[]
    for item in p['recovery']:
        source=item['retention_entry']['source'];reader.file(source,full[source])
        path=item['physical_witness'];blob=catalog[path]['blob']
        witnesses.append(reader.gzip(path,full[path],blob['logical_sha256'],blob['logical_bytes']))
    target_inventory(reader,p['complete_inventory'])
    require(identity(TARGET.parent)==p['outer_parent_identity'],'outer parent changed after recovery')
    for name,row in reader.records.items():require(same(identity(name),row['identity']),'recovery input changed before return')
    return dict(status='verified-read-only-exact-copy-recovery',started_at=started,finished_at=time.time(),
                recovery_source_sha256=digest(Path(__file__).read_bytes()),
                proposal_sha256=PROPOSAL_SHA,historical_source_stage03_wire_sha256=STAGE_INPUTS_SHA,
                retention_files=61,selected_files=21,preserved_files=40,logical_bytes=25677060,
                archive=archive,witnesses=witnesses,full_current_copy_original_witness_bytes=True,
                current_file_records=reader.records,total_read_bytes=reader.bytes,
                complete_prior_catalog_records=464,retirement_authorized=False,allocation_credit_bytes=0)

if __name__=='__main__':
    raise SystemExit('Source-only recovery library: no approved recorded execution wrapper is bound.')
