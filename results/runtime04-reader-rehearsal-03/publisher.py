"""Bounded lossless Reader03 publication; pending final audit05 scope.

Source draft for review. No imports from task sources, subprocess, archive extraction,
provider payload access, source mutation, cleanup or retry. Partial output remains.
Held route/leaf read and membership functions derive byte-for-byte from the
actually executed driver02 publication copier.
"""
from contextlib import contextmanager
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time
import zlib

A=Path('/Users/danluu/dev/rust-interp-runtime-application-admission-20260918')
ROOT=Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
PROPOSAL=A/'.work/runtime04-reader03-publication-scope-02.json'
EXPECTED='5c7cbfc79cc6b01466e2aa0a703ac66b902390fa28cd45422876231384d08729'  # Exact proposed scope02; execution still requires root source review.
DEST=ROOT/'results/runtime04-reader-rehearsal-03'
REPORT=A/'.work/runtime04-reader03-publication-verification-01.json'
H=ROOT/'experiments/runtime04-historical-copy-reader-rehearsal-03'
WORK=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-03'
PREP=ROOT/'.work/runtime04-historical-copy-reader-preparation-execution-03'
EXEC=ROOT/'.work/runtime04-historical-copy-reader-rehearsal-execution-03'
AUDIT=ROOT/'.work/runtime04-historical-copy-reader-independent-verification-05.json'
AUDIT_EXEC=ROOT/'.work/runtime04-historical-copy-reader-verification-execution-05'
FIELDS=('dev','ino','mode','nlink','size','mtime_ns','ctime_ns')
LIMITS=dict(maximum_logical_files=256,maximum_logical_bytes=32*2**20,
    maximum_member_bytes=8*2**20,maximum_blob_bytes=16*2**20,
    maximum_metadata_bytes=4*2**20,maximum_metadata_file_bytes=2*2**20)
GENERATED={'scope.json','manifest.json','STATUS.md','publisher.py'}
START=time.monotonic()

def require(value, message):
    if not value:
        raise RuntimeError(message)

def stamp(info):
    return {key:getattr(info, 'st_'+key) for key in FIELDS}

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def unique(pairs):
    answer = {}
    for key, value in pairs:
        require(key not in answer, 'duplicate JSON member')
        answer[key] = value
    return answer

def parsed(data):
    return json.loads(data, object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))

def canonical(path):
    path = Path(path)
    require(path.is_absolute() and str(path).startswith('/') and not str(path).startswith('//')
            and '..' not in path.parts and not any(ord(c) < 32 or ord(c) == 127 for c in str(path)),
            'canonical absolute source/destination required')
    return path

def directory_key(info):
    return info.st_dev, info.st_ino, info.st_mode

@contextmanager
def held_directory(path):
    """Keep every no-follow ancestor open until the caller finishes its read."""
    path = canonical(path); descriptors = []; links = []
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        descriptors.append(os.open('/', flags))
        for component in path.parts[1:]:
            parent = descriptors[-1]
            child = os.open(component, flags, dir_fd=parent)
            descriptors.append(child); expected = directory_key(os.fstat(child))
            require(stat.S_ISDIR(expected[2]), 'ordinary directory required')
            links.append((parent, component, child, expected))
        def check():
            for parent, name, child, expected in links:
                require(directory_key(os.fstat(child)) == expected
                        and directory_key(os.stat(name, dir_fd=parent, follow_symlinks=False)) == expected,
                        'held ordinary directory route changed')
        check()
        yield descriptors[-1], check
        check()
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)

def read_file(path, expected=None, limit=2*2**20):
    """Complete bounded bytes/hash and seven-field identity before/after read."""
    path = canonical(path)
    with held_directory(path.parent) as (parent, check):
        before = stamp(os.stat(path.name, dir_fd=parent, follow_symlinks=False))
        require(stat.S_ISREG(before['mode']) and 0 <= before['size'] <= limit,
                'bounded ordinary file required: '+str(path))
        if expected is not None:
            require(before == expected['identity'] and before['size'] == expected['size'],
                    'exact source identity changed: '+str(path))
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            require(stamp(os.fstat(descriptor)) == before, 'file changed while opening')
            pieces = []; total = 0
            while True:
                block = os.read(descriptor, min(65536, limit+1-total))
                if not block:
                    break
                total += len(block); require(total <= limit, 'bounded file grew')
                pieces.append(block)
            data = b''.join(pieces)
            require(total == before['size'] and stamp(os.fstat(descriptor)) == before
                    and stamp(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) == before,
                    'file bytes or route changed during read')
            check()
        finally:
            os.close(descriptor)
    if expected is not None:
        require(digest(data) == expected['sha256'], 'exact source SHA changed: '+str(path))
    return data, dict(path=str(path), size=len(data), sha256=digest(data), identity=before)

def membership(root):
    """Read every member without following links, retaining every directory FD."""
    answer = {}
    with held_directory(root) as (descriptor, check):
        def walk(fd, relative):
            before = stamp(os.fstat(fd))
            answer[relative] = dict(kind='directory', identity=before)
            names = sorted(os.listdir(fd))
            for name in names:
                entry = name if relative == '.' else relative+'/'+name
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), 'tree contains special member')
                require(len(answer) < 1024, 'finite complete tree membership')
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        require(stamp(os.fstat(child)) == stamp(info), 'child directory changed on open')
                        walk(child, entry)
                        require(stamp(os.stat(name, dir_fd=fd, follow_symlinks=False)) == stamp(info),
                                'directory route changed')
                    finally:
                        os.close(child)
                else:
                    answer[entry] = dict(kind='file', identity=stamp(info))
            require(names == sorted(os.listdir(fd)) and stamp(os.fstat(fd)) == before, 'tree changed during enumeration')
        walk(descriptor, '.')
        check()
    return answer


def guard():
    require(time.monotonic()-START<=120,'finite120s publication bound')
    require(shutil.disk_usage(ROOT).free>=9*2**30,'live9GiB publication floor')


def row_shape(row):
    require(set(row)=={'source','sha256','size','identity','blob','roles'}
        and set(row['identity'])==set(FIELDS) and all(type(v) is int for v in row['identity'].values())
        and type(row['size']) is int and 0<=row['size']<=LIMITS['maximum_member_bytes']
        and row['identity']['size']==row['size'] and row['identity']['nlink']==1
        and stat.S_ISREG(row['identity']['mode']) and type(row['sha256']) is str
        and re.fullmatch('[a-f0-9]{64}',row['sha256']) and row['blob']=='blobs/'+row['sha256']+'.gz'
        and type(row['roles']) is list and row['roles']==sorted(set(row['roles']))
        and all(type(v) is str for v in row['roles']),'complete typed lossless logical row required')
    canonical(row['source'])


def gzip_payload(data):
    buffer=io.BytesIO()
    with gzip.GzipFile(filename='',mode='wb',fileobj=buffer,mtime=0,compresslevel=9) as stream:
        stream.write(data)
    return buffer.getvalue()


def gzip_readback(data,row):
    # A bounded single gzip member must finish with no trailing or unused bytes.
    stream=zlib.decompressobj(16+zlib.MAX_WBITS)
    payload=stream.decompress(data,row['size']+1)
    require(len(payload)==row['size'] and stream.eof and not stream.unused_data
        and not stream.unconsumed_tail and digest(payload)==row['sha256'],
        'complete bounded gzip EOF/CRC/logical digest readback required')


def publish(relative,data,metadata=False):
    guard();path=DEST/relative
    require(type(relative) is str and relative in GENERATED or type(relative) is str
        and re.fullmatch(r'blobs/[a-f0-9]{64}\.gz',relative),'exact publication name')
    maximum=LIMITS['maximum_metadata_file_bytes'] if metadata else LIMITS['maximum_blob_bytes']
    require(len(data)<=maximum,'bounded individual output')
    with held_directory(path.parent) as (parent,check):
        fd=os.open(path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
        with os.fdopen(fd,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        check();os.fsync(parent)
    saved,record=read_file(path,limit=maximum)
    require(saved==data and record['identity']['nlink']==1,'exact independent ordinary output bytes')
    return record


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-sha256',required=True);args=parser.parse_args()
    require(Path.cwd()==ROOT and sys.dont_write_bytecode and not sys.flags.optimize,'ROOT Python-B context')
    require(type(EXPECTED) is str and re.fullmatch('[a-f0-9]{64}',EXPECTED),'final actual scope remains unbound')
    require(type(args.source_sha256) is str and re.fullmatch('[a-f0-9]{64}',args.source_sha256),'explicit reviewed copier source pin')
    scope_raw,scope_row=read_file(PROPOSAL)
    source_raw,source_row=read_file(Path(__file__).absolute())
    require(scope_row['sha256']==EXPECTED and source_row['sha256']==args.source_sha256,'exact reviewed sources')
    p=parsed(scope_raw)
    require(p['status']=='reviewed-reader03-publication-scope-with-audit05'
        and p['destination']==str(DEST) and encoded(p['limits'])==encoded(LIMITS)
        and type(p['files']) is list and 0<len(p['files'])<=LIMITS['maximum_logical_files']
        and p['logical_files']==len(p['files']) and p['logical_bytes']==sum(row['size'] for row in p['files'])
        and p['logical_bytes']<=LIMITS['maximum_logical_bytes'],'final bounded complete scope')
    rows=p['files'];indexed={};digests={}
    for row in rows:
        row_shape(row);require(row['source'] not in indexed,'duplicate logical source')
        indexed[row['source']]=row
        require(row['sha256'] not in digests or digests[row['sha256']]==row['size'],'inconsistent logical alias')
        digests[row['sha256']]=row['size']
    require(p['unique_payloads']==len(digests) and p['unique_payload_bytes']==sum(digests.values()),'exact logical dedup accounting')
    def current(path):
        path=str(path);require(path in indexed,'required selected evidence omitted: '+path);guard()
        data,_=read_file(path,indexed[path],limit=LIMITS['maximum_member_bytes']);return data
    def doc(path):return parsed(current(path))
    def reference(path):return dict(path=str(path),sha256=indexed[str(path)]['sha256'])
    def trees():
        for root,expected in p['complete_source_trees'].items():
            guard();require(encoded(membership(root))==encoded(expected),'closed complete source tree changed: '+root)
            require({str(Path(root)/name) for name,row in expected.items() if row['kind']=='file'}<=set(indexed),
                'tree member omitted from logical publication')
    def recheck():
        trees()
        for row in rows:current(row['source'])
        read_file(PROPOSAL,scope_row);read_file(source_row['path'],source_row)
    prep=doc(PREP/'record.json');actual=doc(EXEC/'record.json');result=doc(WORK/'result.json')
    report=doc(AUDIT);execution=doc(AUDIT_EXEC/'record.json')
    require(p['final_audit']==reference(AUDIT) and p['final_audit_execution']==reference(AUDIT_EXEC/'record.json'),
        'actual05 proof pins required')
    require(prep['status']==actual['status']==execution['status']=='finished'
        and all(type(row['returncode']) is int and row['returncode']==0 and row['observation_errors']==[]
            and 'execution_error' not in row for row in [prep,actual,execution])
        and prep['canonical_released_at']<=actual['started_at']<=actual['canonical_released_at']
        <=execution['started_at']<=execution['finished_at']<=execution['canonical_released_at'],
        'actual preparation/Reader/auditor closed chronology')
    require(report['status']=='verified-strict-callback-rehearsal'
        and report['pid']==execution['pid'] and report['parent_pid']==execution['parent_pid']
        and execution['report_sha256']==reference(AUDIT)['sha256']
        and execution['source_sha256']==report['auditor_sha256']==reference(AUDIT_EXEC/'source.py')['sha256']
        and execution['execution_source_sha256']==reference(AUDIT_EXEC/'execution.py')['sha256'],
        'actual independent05 source/process/report association')
    for record,directory in [(prep,PREP),(actual,EXEC),(execution,AUDIT_EXEC)]:
        for stream in ['stdout','stderr']:require(record[stream+'_sha256']==digest(current(directory/stream)),'exact actual raw association')
        require(current(directory/'stderr')==b'','passed reader/preparation/auditor stderr')
    require(report['result']==reference(WORK/'result.json') and actual['result_sha256']==reference(WORK/'result.json')['sha256']
        and report['preparation_execution']==reference(PREP/'record.json')
        and report['rehearsal_execution']==reference(EXEC/'record.json'), 'same original Reader03 evidence owner')
    for name in ['launch','inputs','plan']:require(report[name]==reference(H/(name+'.json')),'exact original packet association')
    require(result['status']=='passed-strict-callback-rehearsal-awaiting-independent-audit'
        and report['runtime_admission'] is report['retirement_authorized'] is False
        and result['runtime_admission'] is result['retirement_authorized'] is False
        and all(type(report[k]) is int and report[k]==v for k,v in dict(complete_original_rows=109343,
            current_context_rows=109322,historical_copies=21,prior_catalog_records=464,completed_catalog_records=518,
            compiler_calls=0,provider_probes=0,retired_files=0).items()),'qualified rehearsal only, no runtime or performance claim')
    for number in ['03','04']:
        previous=ROOT/('.work/runtime04-historical-copy-reader-verification-execution-'+number)
        failed=doc(previous/'record.json')
        require(failed['status']=='finished' and type(failed['returncode']) is int and failed['returncode']==1,
            'both actual failed auditor attempts preserved')
        for stream in ['stdout','stderr']:require(failed[stream+'_sha256']==digest(current(previous/stream)),'failed audit raw association')
        require(failed['source_sha256']==reference(previous/'source.py')['sha256']
            and failed['execution_source_sha256']==reference(previous/'execution.py')['sha256'],'failed audit exact source retained')
    native=p['external_native_base'];base=native['association'];archive=native['archive']
    require(doc(H/'inputs.json')['file_table_base']==base['reference'],'unchanged native file-table base')
    m=doc(archive['manifest']['path']);q=doc(archive['independent_audit']['path'])
    member=base['archived']['logical_member'];row=m[member]
    require(row['source']==base['reference']['path'] and row['sha256']==base['reference']['sha256']==base['archived']['sha256']
        and row['bytes']==base['archived']['size'] and q['status']=='verified'
        and q['archive_sha256']==archive['sha256']==base['archived']['archive_sha256']
        and q['manifest_sha256']==archive['manifest']['sha256']==reference(archive['manifest']['path'])['sha256'],
        'exact prior native member/archive/audit recovery association')
    require(not DEST.exists() and not DEST.is_symlink() and not REPORT.exists() and not REPORT.is_symlink(),'fresh exclusive publication/report; no retry')
    require(shutil.disk_usage(ROOT).free>=16*2**30,'fresh16GiB before publication')
    recheck()
    with held_directory(DEST.parent) as (parent,check):
        os.mkdir(DEST.name,0o700,dir_fd=parent);check();os.fsync(parent)
    with held_directory(DEST) as (parent,check):
        os.mkdir('blobs',0o700,dir_fd=parent);check();os.fsync(parent)
    physical={};outputs={};compressed=0
    for row in rows:
        data=current(row['source'])
        if row['sha256'] not in physical:
            payload=gzip_payload(data);require(compressed+len(payload)<=LIMITS['maximum_blob_bytes'],'aggregate compressed cap')
            gzip_readback(payload,row);out=publish(row['blob'],payload);compressed+=len(payload)
            physical[row['sha256']]=dict(path=row['blob'],sha256=out['sha256'],bytes=out['size'],logical_sha256=row['sha256'],logical_bytes=row['size'])
            outputs[row['blob']]=out
        current(row['source'])
    status=('Reader03 passed once and independent audit05 verified the saved evidence.\n'
        'The two earlier independent audit failures and earlier preparation/Reader failures remain retained.\n'
        'This publication preserves logical source/raw bytes in deterministic gzip blobs, with every path and original identity in manifest.json.\n'
        'No runtime installation, retirement, application or performance qualification is granted.\n'
        'The native file-table base remains an explicit authenticated reference to its existing published archive; live provider payloads are not copied.\n').encode()
    manifest=dict(policy='deterministic-gzip-blobs-with-complete-logical-alias-manifest-v1',logical_files=len(rows),
        logical_bytes=p['logical_bytes'],unique_payloads=len(physical),unique_payload_bytes=sum(digests.values()),
        compressed_bytes=compressed,files=rows,blobs=physical,complete_source_trees=p['complete_source_trees'],
        source_scope=reference(PROPOSAL) if str(PROPOSAL) in indexed else dict(path=str(PROPOSAL),sha256=scope_row['sha256']),
        independent_rehearsal_audit=reference(AUDIT),external_native_base=native,runtime_admission=False,
        retirement_authorized=False,performance_measurement=False)
    metadata={'scope.json':scope_raw,'publisher.py':source_raw,'STATUS.md':status,'manifest.json':encoded(manifest)}
    require(sum(map(len,metadata.values()))<=LIMITS['maximum_metadata_bytes'],'aggregate metadata cap')
    for name,data in metadata.items():outputs[name]=publish(name,data,metadata=True)
    final=membership(DEST)
    require({name for name,row in final.items() if row['kind']=='file'}==set(outputs)
        and {name for name,row in final.items() if row['kind']=='directory'}=={'.','blobs'},'exact output membership')
    source_inodes={(row['identity']['dev'],row['identity']['ino']) for row in rows}
    for name,out in outputs.items():
        data,current_row=read_file(DEST/name,out,limit=LIMITS['maximum_blob_bytes'] if name.startswith('blobs/') else LIMITS['maximum_metadata_file_bytes'])
        require((out['identity']['dev'],out['identity']['ino']) not in source_inodes and current_row==out,'independent output identity')
        if name.startswith('blobs/'):
            logical=name[len('blobs/'):-3];gzip_readback(data,dict(size=digests[logical],sha256=logical))
    recheck();guard()
    verification=dict(status='verified-lossless-reader03-publication',finished_at=time.time(),logical_files=len(rows),
        logical_bytes=p['logical_bytes'],unique_payloads=len(physical),compressed_bytes=compressed,
        output_files=len(outputs),output_bytes=sum(row['size'] for row in outputs.values()),outputs=outputs,
        manifest_sha256=outputs['manifest.json']['sha256'],scope_sha256=scope_row['sha256'],
        source_sha256=source_row['sha256'],audit=reference(AUDIT),all_source_identities_and_bytes_rechecked=True,
        all_output_gzip_EOF_CRC_logical_hashes=True,exact_output_membership=True,source_mutations=0,
        runtime_admission=False,retirement_authorized=False,performance_measurement=False)
    data=encoded(verification);require(len(data)<=2*2**20,'bounded publication verification report')
    with held_directory(REPORT.parent) as (parent,check):
        fd=os.open(REPORT.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        check();os.fsync(parent)
    require(read_file(REPORT)[0]==data,'durable exact verification report')
    print(encoded(dict(report=str(REPORT),sha256=digest(data),destination=str(DEST),output_files=len(outputs))).decode(),end='')


if __name__=='__main__':main()
