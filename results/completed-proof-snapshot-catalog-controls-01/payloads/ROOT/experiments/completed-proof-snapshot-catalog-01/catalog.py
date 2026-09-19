"""Pure extension of an authenticated catalog with one completed v2 owner.

Callbacks authenticate frozen ordinary files/directories and the owner's full
recipe/result. This module neither imports snapshot writers nor performs I/O.
The original v1 beta/native catalog and its producer remain unchanged.
"""
import hashlib
import json
from pathlib import PurePosixPath as Path
import re
import stat

POLICY = 'completed-proof-snapshot-catalog-v1'
ANCESTOR_POLICY = 'hash-proof-reference-selection-v1'
SNAPSHOT_POLICY = 'bounded-gzip-proof-snapshots-v2'
FIELDS = {'dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink'}
BLOB_FIELDS = {'filename', 'logical_sha256', 'logical_bytes', 'sha256', 'compressed_bytes'}
LIMIT_CAPS = dict(maximum_files=1024, maximum_file_bytes=64*2**20,
                  maximum_logical_bytes=512*2**20, maximum_compressed_bytes=128*2**20,
                  maximum_manifest_bytes=4*2**20)


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def same(left, right):
    return encoded(left) == encoded(right)


def clone(value):
    """Callbacks cannot rewrite the authenticated values compared afterwards."""
    return json.loads(encoded(value))


def sha(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def token(value):
    return type(value) is str and re.fullmatch('[a-f0-9]{64}', value) is not None


def path(value):
    require(type(value) is str and value.startswith('/') and not value.startswith('//')
            and str(Path(value)) == value and '..' not in Path(value).parts
            and not any(ord(c) < 32 for c in value), 'canonical absolute proof path required')
    return Path(value)


def identity(value, kind):
    require(type(value) is dict and set(value) == FIELDS
            and all(type(v) is int and v >= 0 for v in value.values())
            and value['ino'] > 0 and value['nlink'] > 0 and kind(value['mode']),
            'complete typed ordinary identity required')
    return value


def ordinary(row, name, *, single_link=True):
    require(type(row) is dict and set(row) == {'path', 'size', 'sha256', 'identity'}
            and row['path'] == str(name) and token(row['sha256'])
            and type(row['size']) is int and 0 <= row['size'] <= 2**30,
            'bounded exact frozen ordinary file required')
    identity(row['identity'], stat.S_ISREG)
    require((not single_link or row['identity']['nlink'] == 1) and row['identity']['size'] == row['size'],
            'single-link file size/identity differs')
    return row


def bounded_limits(limits):
    require(type(limits) is dict and set(limits) == set(LIMIT_CAPS)
            and all(type(v) is int and 0 < v <= LIMIT_CAPS[k] for k,v in limits.items()),
            'exact bounded integer snapshot limits required')


def blob(value, key, size, limits):
    require(type(value) is dict and set(value) == BLOB_FIELDS and token(key)
            and value['logical_sha256'] == key and value['filename'] == key+'.gz'
            and type(value['logical_bytes']) is int and 0 <= value['logical_bytes'] == size <= limits['maximum_file_bytes']
            and token(value['sha256']) and type(value['compressed_bytes']) is int
            and 0 < value['compressed_bytes'] <= limits['maximum_compressed_bytes'],
            'exact bounded compressed blob descriptor required')


def validate_catalog(prior, accounted_roots, limits, *, file_record, directory_record):
    """Caller rebuilds original owner qualification; recheck all physical rows."""
    bounded_limits(limits)
    require(set(prior) == {'policy', 'priority', 'predecessors', 'records', 'evidence_roots'}
            and prior['policy'] in [ANCESTOR_POLICY, POLICY]
            and type(prior['priority']) is list and prior['priority']
            and len(prior['priority']) == len(set(prior['priority']))
            and [p['role'] for p in prior['predecessors']] == prior['priority'],
            'complete authenticated predecessor catalog required')
    roots = prior['evidence_roots']; names = {}; inodes = set()
    require(type(roots) is dict and len(roots) <= 32, 'bounded explicit physical roots required')
    require(type(prior['records']) is list and len(prior['records']) <= 32*limits['maximum_files'],
            'bounded complete predecessor records required')
    for root, stamp in roots.items():
        require(str(path(root).parent) in accounted_roots, 'blob root is outside counted stage evidence')
        identity(stamp, stat.S_ISDIR)
        require(not any(path(root) in path(other).parents or path(other) in path(root).parents
                        for other in roots if other != root), 'overlapping physical roots')
        names[root] = []
    paths = set()
    for row in prior['records']:
        require(set(row) == {'path', 'identity', 'blob', 'evidence_root'}
                and row['evidence_root'] in roots, 'complete inherited reference required')
        p = path(row['path']); b = row['blob']; key = b['logical_sha256']
        blob(b, key, b['logical_bytes'], limits)
        require(p.parent == path(row['evidence_root']) and p.name == b['filename'], 'blob escaped exact root')
        actual = ordinary(file_record(p), p)
        require(same(actual['identity'], row['identity']) and actual['sha256'] == b['sha256']
                and actual['size'] == b['compressed_bytes'], 'inherited physical file changed')
        inode = (actual['identity']['dev'], actual['identity']['ino'])
        require(str(p) not in paths and inode not in inodes, 'duplicate physical ancestor credit')
        paths.add(str(p)); inodes.add(inode); names[row['evidence_root']].append(p.name)
    for root, stamp in roots.items():
        actual = directory_record(path(root))
        require(set(actual) == {'identity', 'children'} and same(actual['identity'], stamp)
                and actual['children'] == sorted(names[root]), 'complete ancestor directory changed')


def select(records, catalog):
    """Keep every logical alias; choose one physical row per requested digest."""
    require(catalog['policy'] in [ANCESTOR_POLICY, POLICY], 'unknown catalog policy')
    wanted = {}; names = set()
    for row in records:
        ordinary(row, path(row['path']), single_link=False)
        require(row['path'] not in names, 'duplicate logical pathname')
        require(row['sha256'] not in wanted or wanted[row['sha256']] == row['size'], 'logical alias size differs')
        wanted[row['sha256']] = row['size']; names.add(row['path'])
    require(names, 'complete nonempty logical selection required')
    selected = {}; paths = set(); inodes = set(); used = set()
    for row in catalog['records']:
        key = row['blob']['logical_sha256']
        if key not in wanted or key in selected:
            continue
        inode = (row['identity']['dev'], row['identity']['ino'])
        require(row['blob']['logical_bytes'] == wanted[key] and row['identity']['nlink'] == 1
                and row['path'] not in paths and inode not in inodes
                and row['evidence_root'] in catalog['evidence_roots'], 'ambiguous physical selection')
        selected[key] = row; paths.add(row['path']); inodes.add(inode); used.add(row['evidence_root'])
    return dict(records=[selected[k] for k in sorted(selected)],
                evidence_roots={r:catalog['evidence_roots'][r] for r in sorted(used)})


def extend(prior, owner, accounted_roots, limits, *, read_json, file_record,
           directory_record, expand_inputs, validate_owner):
    """Add one closed v2 owner; callbacks perform only authenticated reads.

    owner supplies role/source/evidence/audit plus an explicit result_path and
    result_digest_field. validate_owner must separately validate that exact
    successful recipe and return True. expand_inputs returns the authenticated
    full file table, retaining the input's other metadata and logical selection.
    """
    require(type(accounted_roots) is list and accounted_roots == sorted(set(accounted_roots)),
            'complete sorted counted evidence owners required')
    for root in accounted_roots:
        path(root)
        require(not any(path(root) in path(other).parents for other in accounted_roots if root != other),
                'overlapping aggregate evidence owners')
    validate_catalog(prior, accounted_roots, limits, file_record=file_record, directory_record=directory_record)
    require(set(owner) == {'role', 'source', 'evidence', 'audit', 'result_path', 'result_digest_field'}
            and type(owner['role']) is str and re.fullmatch('[a-z][a-z0-9_-]{0,63}', owner['role'])
            and owner['role'] not in prior['priority'], 'new explicitly named owner required')
    source = path(owner['source']); evidence = path(owner['evidence']); result_path = path(owner['result_path'])
    require(str(evidence) in accounted_roots and evidence in result_path.parents
            and type(owner['result_digest_field']) is str
            and re.fullmatch('[a-z][a-z0-9_]*_sha256', owner['result_digest_field']), 'explicit owned result binding required')
    association = dict(role=owner['role'], source=str(source), evidence=str(evidence),
                       result_digest_field=owner['result_digest_field'], inherited_catalog_sha256=sha(prior))
    def load(name, p):
        row = ordinary(file_record(p), p)
        association[name] = dict(path=str(p), sha256=row['sha256'])
        return read_json(p), row
    receipt, receipt_file = load('receipt', evidence/'receipt.json')
    result, result_file = load('result', result_path)
    audit, _ = load('audit', path(owner['audit']['path']))
    wire, input_file = load('inputs', source/'inputs.json')
    plan, plan_file = load('plan', source/'plan.json')
    snapshot, _ = load('projection', source/'snapshot-plan.json')
    retained, _ = load('retained_projection', evidence/'snapshot-plan.json')
    manifest, _ = load('manifest', evidence/'source-snapshots.json')
    require(same(association['audit'], owner['audit']) and audit['status'] == 'verified'
            and audit['receipt_sha256'] == receipt_file['sha256']
            and audit['result_sha256'] == result_file['sha256']
            and receipt['status'] in ['passed', 'passed-awaiting-independent-audit']
            and receipt[owner['result_digest_field']] == result_file['sha256']
            and receipt['started_at'] <= receipt['admitted_at'] <= receipt['finished_at'], 'closed passed owner/audit/result required')
    require(validate_owner(clone(owner), clone(receipt), clone(result), clone(audit)) is True,
            'owner-specific completed recipe is not qualified')
    require(receipt['inputs_sha256'] == input_file['sha256'] == snapshot['inputs_sha256']
            and wire['plan_sha256'] == plan_file['sha256']
            and association['projection']['sha256'] == association['retained_projection']['sha256']
            == receipt['snapshot_plan_sha256'] and same(snapshot, retained)
            and association['manifest']['sha256'] == receipt['source_snapshots_sha256'], 'actual source/snapshot receipt association differs')
    require(same(plan['snapshot_reuse'], prior), 'owner omitted or relabelled inherited catalog')
    require(set(plan['evidence_roots']) <= set(accounted_roots) and str(evidence) in plan['evidence_roots'],
            'owner evidence accounting changed')
    freeze = expand_inputs(clone(wire), clone(input_file))
    metadata = lambda doc: {k:v for k,v in doc.items() if k not in ['files', 'file_table_base', 'file_table_integrity']}
    require(same(metadata(wire), metadata(freeze)), 'expanded inputs changed non-file metadata')
    if 'file_table_base' in wire:
        require('file_table_integrity' in wire and 'file_table_base' not in freeze
                and 'file_table_integrity' not in freeze, 'incomplete compact input reconstruction')
        base = wire['file_table_base']
        require(type(base) is dict and set(base) == {'path','sha256'} and token(base['sha256']),
                'exact authenticated file-table base reference required')
        bp = path(base['path']); br = ordinary(file_record(bp), bp); base_doc = read_json(bp)
        require(br['size'] <= 64*2**20 and br['sha256'] == base['sha256']
                and 'file_table_base' not in base_doc and 'file_table_integrity' not in base_doc
                and not set(base_doc['files']) & set(wire['files'])
                and same({k:br[k] for k in ['size','sha256','identity']},wire['files'][str(bp)])
                and same(freeze['files'],dict(base_doc['files'],**wire['files'])),
                'compact source base/delta association differs')
        association['file_table_base'] = dict(base)
        integrity = wire['file_table_integrity']
        require(set(integrity) == {'sha256', 'count', 'total_bytes'}
                and same(integrity, dict(sha256=sha(freeze['files']), count=len(freeze['files']),
                    total_bytes=sum(v['size'] for v in freeze['files'].values()))), 'expanded input integrity differs')
    else:
        require('file_table_integrity' not in wire and same(wire, freeze), 'flat input reconstruction changed')
    helper = snapshot['helper']; hp = path(helper['path']); hr = ordinary(file_record(hp), hp)
    require(hr['sha256'] == helper['sha256'] and same({k:hr[k] for k in ['size','sha256','identity']}, freeze['files'][str(hp)]),
            'actual helper not frozen by completed owner')
    association['helper'] = dict(helper)
    projection = snapshot['projection']; blobs = projection['blobs']; storage = projection['storage']
    require(same(snapshot['limits'], limits) and same(projection['limits'], limits)
            and projection['policy'] == manifest['policy'] == SNAPSHOT_POLICY
            and manifest['projection_sha256'] == sha(projection)
            and manifest['full_logical_readback'] is True and manifest['full_gzip_eof'] is True,
            'complete qualified v2 projection/manifest required')
    names = freeze['snapshot_inputs']
    require(type(names) is list and all(type(n) is str for n in names) and len(names) == len(set(names))
            and set(names) <= set(freeze['files']) and str(source/'inputs.json') not in names,
            'complete original logical selection required')
    files = {n:dict(path=n, **freeze['files'][n]) for n in sorted(names)}
    files[str(source/'inputs.json')] = input_file
    wanted = {}
    for n, row in files.items():
        ordinary(row, path(n), single_link=False)
        require(same(ordinary(file_record(path(n)), path(n), single_link=False), row), 'original selected input changed or disappeared')
        require(row['size'] <= limits['maximum_file_bytes'], 'logical file cap exceeded')
        require(row['sha256'] not in wanted or wanted[row['sha256']] == row['size'], 'logical alias conflict')
        wanted[row['sha256']] = row['size']
    logical_accounting = dict(logical_bytes=sum(r['size'] for r in files.values()),
                              unique_logical_bytes=sum(wanted.values()),
                              manifest_reservation_bytes=2*limits['maximum_manifest_bytes'])
    require(same(projection['files'], files) and set(blobs) == set(wanted) == set(storage)
            and same(manifest['blobs'], blobs) and len(files) <= limits['maximum_files']
            and logical_accounting['logical_bytes'] <= limits['maximum_logical_bytes']
            and same({k:projection[k] for k in logical_accounting}, logical_accounting),
            'complete logical catalog/accounting differs')
    selected = select(list(files.values()), prior)
    expected_reuse = {r['blob']['logical_sha256']:r for r in selected['records']}
    require(same(projection['reuse'], expected_reuse) and same(projection['evidence_roots'], selected['evidence_roots'])
            and same(manifest['reuse'], expected_reuse) and same(manifest['evidence_roots'], selected['evidence_roots']),
            'reused bytes lack exact authenticated predecessor ownership')
    root = evidence/'source-snapshots'; association['snapshot_root'] = str(root)
    require(str(root) not in prior['evidence_roots'], 'owner attempts to replace existing snapshot root')
    actual_directory = directory_record(root)
    require(set(actual_directory) == {'identity', 'children'}, 'complete new-owner directory required')
    identity(actual_directory['identity'], stat.S_ISDIR)
    current_records = []; physical = {}; total = new = allocated = new_allocated = 0; stored_names = []
    for key, b in sorted(blobs.items()):
        blob(b, key, wanted[key], limits)
        if key in expected_reuse:
            row = expected_reuse[key]
            require(same(b, row['blob']) and same(storage[key], dict(kind='reused', path=row['path'])), 'reused descriptor/path changed')
            physical[key] = dict(kind='reused', path=row['path'])
        else:
            require(same(storage[key], dict(kind='stored')), 'new blob incorrectly receives reuse credit')
            p = root/b['filename']; actual = ordinary(file_record(p), p)
            require(actual['sha256'] == b['sha256'] and actual['size'] == b['compressed_bytes'], 'new physical blob differs')
            current_records.append(dict(path=str(p), identity=actual['identity'], blob=b, evidence_root=str(root)))
            physical[key] = dict(kind='stored', path=str(p)); stored_names.append(p.name)
            new += b['compressed_bytes']; new_allocated += ((b['compressed_bytes']+4095)//4096)*4096
        total += b['compressed_bytes']; allocated += ((b['compressed_bytes']+4095)//4096)*4096
    mapping = {n:dict(path=physical[r['sha256']]['path'], sha256=r['sha256'], size=r['size'], encoding='gzip') for n,r in files.items()}
    require(same(manifest['storage'], physical) and same(manifest['files'], mapping)
            and actual_directory['children'] == sorted(stored_names), 'complete physical storage/mapping/membership differs')
    accounting = dict(compressed_bytes=total,new_compressed_bytes=new,reused_compressed_bytes=total-new,
                      compressed_allocated_bytes=allocated,new_compressed_allocated_bytes=new_allocated)
    manifest_accounting = {k:accounting[k] for k in ['compressed_bytes','new_compressed_bytes','reused_compressed_bytes']}
    require(total <= limits['maximum_compressed_bytes']
            and same({k:projection[k] for k in accounting}, accounting)
            and same({k:manifest[k] for k in manifest_accounting}, manifest_accounting),
            'stored/reused physical accounting differs')
    require(all(len(encoded(v)) <= limits['maximum_manifest_bytes'] for v in [projection,manifest,snapshot]),
            'completed snapshot manifest bound exceeded')
    roots = dict(prior['evidence_roots']); roots[str(root)] = actual_directory['identity']
    answer = dict(policy=POLICY, priority=prior['priority']+[owner['role']],
                  predecessors=prior['predecessors']+[association], records=prior['records']+current_records,
                  evidence_roots=dict(sorted(roots.items())))
    validate_catalog(answer, accounted_roots, limits, file_record=file_record, directory_record=directory_record)
    return answer


def reservation(projection, maximum_manifest_bytes, remaining_bytes):
    """No old bytes are subtracted from the enclosing aggregate sample."""
    require(type(maximum_manifest_bytes) is int and 0 <= maximum_manifest_bytes <= 4*2**20
            and type(remaining_bytes) is int and 0 <= remaining_bytes <= 32*2**20,
            'bounded nonnegative exact integer reservation parameters required')
    blobs, storage = projection['blobs'], projection['storage']
    require(type(blobs) is dict and type(storage) is dict and 0 < len(blobs) <= 1024
            and set(blobs) == set(storage) and all(token(k) for k in blobs)
            and all(type(v) is dict and v.get('kind') in ['stored','reused'] for v in storage.values()), 'complete bounded storage map required')
    for key,b in blobs.items():
        blob(b,key,b['logical_bytes'],LIMIT_CAPS)
        s=storage[key]
        require(set(s) == ({'kind'} if s['kind'] == 'stored' else {'kind','path'}), 'exact projected storage fields required')
        if s['kind'] == 'reused':path(s['path'])
    keys = [k for k in blobs if storage[k]['kind'] == 'stored']
    allocated = sum(((blobs[k]['compressed_bytes']+4095)//4096)*4096 for k in keys)
    total = sum(b['compressed_bytes'] for b in blobs.values())
    new = sum(blobs[k]['compressed_bytes'] for k in keys)
    expected = dict(new_compressed_allocated_bytes=allocated,compressed_bytes=total,
                    new_compressed_bytes=new,reused_compressed_bytes=total-new,
                    compressed_allocated_bytes=sum(((b['compressed_bytes']+4095)//4096)*4096 for b in blobs.values()))
    require(total <= 128*2**20 and same({k:projection[k] for k in expected},expected),
            'new allocation or compressed accounting differs')
    return allocated+4096*len(keys)+2*maximum_manifest_bytes+remaining_bytes
