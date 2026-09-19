"""Pure association and selection of audited, already-accounted proof blobs.

The caller supplies the two fixed predecessor roles and verified file/directory
readers. No filesystem discovery, imports, provider calls or writes occur here.
The complete original catalogs remain in the plan; selection only decides where
each still-present logical input gets its separately verified compressed bytes.
"""
import hashlib
import json
from pathlib import Path
import re
import stat

POLICY = 'hash-proof-reference-selection-v1'
PRIORITY = ['beta', 'native']
FIELDS = {'dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns', 'nlink'}
BLOB_FIELDS = {'filename', 'logical_sha256', 'logical_bytes', 'sha256', 'compressed_bytes'}
NATIVE_FAILURE = "ValueError('wrong-B3 failure is not compiler metadata incompatibility')"


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode()


def hash_token(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def ordinary_file(row, path):
    require(set(row) == {'path', 'identity', 'sha256', 'size'} and row['path'] == str(path)
            and hash_token(row['sha256']) and set(row['identity']) == FIELDS
            and all(type(v) is int for v in row['identity'].values())
            and stat.S_ISREG(row['identity']['mode']) and row['identity']['nlink'] == 1
            and type(row['size']) is int and row['size'] == row['identity']['size'],
            'ordinary single-link frozen proof file required')
    return row


def reconciliation(qualifier, predecessor, terminal, association, original_inputs, accounted_roots, *, read_json, file_record):
    """A new zero-child qualifier may validate an honestly failed snapshot owner."""
    require(set(qualifier) == {'source', 'evidence', 'audit'}, 'exact reconciliation routes required')
    source = Path(qualifier['source']); evidence = Path(qualifier['evidence'])
    require(source.is_absolute() and evidence.is_absolute() and '..' not in source.parts and '..' not in evidence.parts
            and source != Path(predecessor['source']) and evidence != Path(predecessor['evidence']),
            'separate reconciliation source and owner required')
    result = dict(source=str(source), evidence=str(evidence))
    def load(name, path):
        row = ordinary_file(file_record(path), path)
        if name is not None:result[name] = dict(path=str(path), sha256=row['sha256'])
        return read_json(path), row
    receipt, receipt_file = load('receipt', evidence/'receipt.json')
    qualified, qualified_file = load('result', evidence/'native-controls.json')
    audit, _ = load('audit', Path(qualifier['audit']['path']))
    freeze, frozen_file = load(None, source/'inputs.json')
    plan, plan_file = load(None, source/'plan.json')
    old_plan_path = Path(predecessor['source'])/'plan.json'
    old_plan, old_plan_file = load(None, old_plan_path)
    require(result['audit'] == qualifier['audit'] and audit['status'] == 'verified'
            and audit['receipt_sha256'] == receipt_file['sha256']
            and audit['result_sha256'] == qualified_file['sha256']
            and receipt['status'] == 'passed' and receipt['read_only_reconciliation'] is True
            and receipt['commands'] == [] and receipt['actual_workload_children'] == 0
            and receipt['saved_actual_children'] == 20 and receipt['historical_failed_children'] == 11
            and receipt['native_roles_and_behavior_qualified'] is True
            and terminal['finished_at'] <= receipt['started_at'] <= receipt['admitted_at'] <= receipt['finished_at'],
            'actual zero-child reconciliation qualification required')
    require(receipt['inputs_sha256'] == frozen_file['sha256']
            and receipt['plan_sha256'] == freeze['plan_sha256'] == plan_file['sha256']
            and receipt['result_sha256'] == qualified_file['sha256']
            and original_inputs['plan_sha256'] == old_plan_file['sha256'],
            'reconciliation source/result or original plan hash differs')
    base = dict(path=str(Path(predecessor['source'])/'inputs.json'), sha256=association['inputs']['sha256'])
    additions = {'read_only_reconciliation', 'actual_workload_children', 'base_inputs', 'command_evidence',
                 'reconciliation', 'wrong_beta_providers', 'wrong_beta_lib', 'reconciliation_evidence_roots'}
    require(freeze['base_inputs'] == plan['base_inputs'] == base
            and str(Path(predecessor['evidence'])/'native-controls.json') in freeze['absent_paths']
            and set(plan) == set(old_plan)|additions and not set(old_plan)&additions
            and encoded({key:plan[key] for key in old_plan}) == encoded(old_plan)
            and plan['read_only_reconciliation'] is True and plan['actual_workload_children'] == 0,
            'reconciliation must preserve every original command plan value')
    require(plan['reconciliation_evidence_roots'] == sorted(set(old_plan['evidence_roots'])|{str(evidence)})
            and set(plan['reconciliation_evidence_roots']) <= set(accounted_roots),
            'reconciliation cannot omit or move existing physical accounting')
    commands = dict(source=predecessor['source'], evidence=predecessor['evidence'],
        receipt_sha256=association['receipt']['sha256'], inputs_sha256=association['inputs']['sha256'],
        plan_sha256=old_plan_file['sha256'], snapshot_plan_sha256=terminal['snapshot_plan_sha256'],
        status='failed', error=NATIVE_FAILURE, commands=terminal['commands'], failure_audit=association['audit'])
    require(len(terminal['commands']) == 20
            and plan['command_evidence'] == receipt['command_evidence'] == qualified['command_evidence'] == commands
            and plan['reconciliation'] == receipt['reconciliation'] == qualified['reconciliation']
            and plan['reconciliation']['source'] == str(source)
            and plan['reconciliation']['base_inputs'] == base
            and plan['reconciliation']['failure_audit'] == association['audit'],
            'reconciliation does not own the exact failed original history')
    require(qualified['status'] == 'native-roles-and-behavior-qualified'
            and qualified['candidate_revision'] == terminal['candidate_revision'] == old_plan['candidate_revision']
            and qualified['qualified_native_children'] == 20 and qualified['total_actual_native_children'] == 31
            and qualified['history'] == terminal['commands'][:18] and qualified['wrong_B3_commands'] == terminal['commands'][18:],
            'reconciled qualification/history count differs')
    return result


def catalog(predecessors, accounted_roots, limits, *, read_json, file_record, directory_record):
    """Bind every old v1 blob to the exact audited B3/native source and WORK.

    file_record/directory_record must reject symlinks in the entire route, return
    current complete identities, and verify file hashes against the enclosing
    freeze (or add those full hashes during read-only preparation).
    """
    require(type(predecessors) is list and [p['role'] for p in predecessors] == PRIORITY,
            'exact beta then native predecessor roles required')
    require(type(accounted_roots) is list and accounted_roots == sorted(set(accounted_roots)),
            'exact accounted evidence roots required')
    records = []; proofs = []; roots = {}; paths = set()
    for predecessor in predecessors:
        expected_fields = {'role', 'source', 'evidence', 'audit'}
        if predecessor['role'] == 'native':expected_fields.add('qualification')
        require(set(predecessor) == expected_fields, 'exact predecessor routes required')
        role = predecessor['role']; source = Path(predecessor['source']); evidence = Path(predecessor['evidence'])
        require(source.is_absolute() and evidence.is_absolute() and '..' not in source.parts
                and '..' not in evidence.parts and str(evidence) in accounted_roots,
                'predecessor evidence is not already counted')
        snapshot_root = evidence/'source-snapshots'
        require(not any(snapshot_root == Path(root) or snapshot_root in Path(root).parents
                        or Path(root) in snapshot_root.parents for root in roots), 'overlapping predecessor proof roots')
        association = dict(role=role, source=str(source), evidence=str(evidence), snapshot_root=str(snapshot_root))
        def load(name, path):
            row = ordinary_file(file_record(path), path)
            association[name] = dict(path=str(path), sha256=row['sha256'])
            return read_json(path), row
        terminal, terminal_file = load('receipt', evidence/'receipt.json')
        audit_ref = predecessor['audit']
        require(set(audit_ref) == {'path', 'sha256'} and hash_token(audit_ref['sha256']), 'exact predecessor audit reference')
        audit, _ = load('audit', Path(audit_ref['path']))
        require(association['audit'] == audit_ref and audit['receipt_sha256'] == terminal_file['sha256']
                and terminal['started_at'] <= terminal['admitted_at'] <= terminal['finished_at'],
                'closed actual predecessor/audit association required')
        if role == 'beta':
            require(terminal['status'] == 'passed' and audit['status'] == 'verified', 'closed actual beta qualification required')
        else:
            require(terminal['status'] == 'failed' and terminal['error'] == NATIVE_FAILURE
                    and terminal['source_restored'] is True and audit['status'] == 'verified-retained-failure'
                    and audit['children'] == 20 and audit['historical_failed_children'] == 11
                    and audit['total_actual_native_children'] == 31 and audit['qualified_native_children'] == 0
                    and audit['source_restored'] is True and audit['native_roles_and_behavior_qualified'] is False,
                    'original native snapshot owner must remain failed')
        freeze, input_file = load('inputs', source/'inputs.json')
        snapshot, _ = load('projection', source/'snapshot-plan.json')
        retained, _ = load('retained_projection', evidence/'snapshot-plan.json')
        manifest, _ = load('manifest', evidence/'source-snapshots.json')
        require(association['projection']['sha256'] == association['retained_projection']['sha256']
                == terminal['snapshot_plan_sha256'] and retained == snapshot
                and input_file['sha256'] == terminal['inputs_sha256'] == snapshot['inputs_sha256']
                and association['manifest']['sha256'] == terminal['source_snapshots_sha256'],
                'original source/work snapshot receipt hashes differ')
        if role == 'native':
            require(predecessor['qualification']['evidence'] in accounted_roots,
                    'reconciliation evidence is not already counted')
            association['qualification'] = reconciliation(predecessor['qualification'], predecessor, terminal,
                association, freeze, accounted_roots, read_json=read_json, file_record=file_record)
        helper = snapshot['helper']; helper_file = ordinary_file(file_record(Path(helper['path'])), Path(helper['path']))
        require(helper_file['sha256'] == helper['sha256'] == freeze['files'][helper['path']]['sha256'],
                'original snapshot helper is not bound to original freeze')
        projection = snapshot['projection']
        require(snapshot['limits'] == projection['limits'] == limits
                and projection['policy'] == manifest['policy'] == 'bounded-gzip-proof-snapshots-v1'
                and manifest['projection_sha256'] == hashlib.sha256(encoded(projection)).hexdigest()
                and manifest['full_logical_readback'] is True and manifest['full_gzip_eof'] is True,
                'completed original v1 snapshot projection/manifest required')
        names = freeze['snapshot_inputs']
        require(type(names) is list and names == sorted(set(names)) and set(names) <= set(freeze['files'])
                and str(source/'inputs.json') not in names, 'complete original logical selection required')
        original_files = {name:dict(path=name, **freeze['files'][name]) for name in names}
        original_files[str(source/'inputs.json')] = input_file
        require(projection['files'] == dict(sorted(original_files.items())), 'original logical input set was changed')
        blobs = projection['blobs']; wanted = {}
        for row in original_files.values():
            require(row['sha256'] not in wanted or wanted[row['sha256']] == row['size'], 'equal logical hashes have different sizes')
            wanted[row['sha256']] = row['size']
        require(type(blobs) is dict and set(blobs) == set(wanted) and manifest['blobs'] == blobs,
                'complete original compressed catalog required')
        require(len(original_files) <= limits['maximum_files']
                and projection['logical_bytes'] == sum(row['size'] for row in original_files.values()) <= limits['maximum_logical_bytes']
                and projection['unique_logical_bytes'] == sum(wanted.values())
                and projection['manifest_reservation_bytes'] == 2*limits['maximum_manifest_bytes'],
                'original logical accounting differs')
        expected_mapping = {name:dict(path=str(snapshot_root/(row['sha256']+'.gz')), sha256=row['sha256'],
                                     size=row['size'], encoding='gzip') for name, row in original_files.items()}
        require(manifest['files'] == expected_mapping, 'original manifest path/hash mapping differs')
        directory = directory_record(snapshot_root)
        require(set(directory) == {'identity', 'children'} and set(directory['identity']) == FIELDS
                and all(type(v) is int for v in directory['identity'].values())
                and stat.S_ISDIR(directory['identity']['mode'])
                and directory['children'] == sorted(key+'.gz' for key in blobs),
                'complete ordinary predecessor snapshot directory required')
        roots[str(snapshot_root)] = directory['identity']
        total = 0; allocated = 0
        for key, blob in sorted(blobs.items()):
            require(hash_token(key) and set(blob) == BLOB_FIELDS and blob['logical_sha256'] == key
                    and blob['logical_bytes'] == wanted[key] and blob['filename'] == key+'.gz'
                    and hash_token(blob['sha256']) and type(blob['compressed_bytes']) is int
                    and 0 < blob['compressed_bytes'] <= limits['maximum_compressed_bytes'],
                    'original blob descriptor differs')
            path = snapshot_root/blob['filename']; row = ordinary_file(file_record(path), path)
            require(row['sha256'] == blob['sha256'] and row['size'] == blob['compressed_bytes']
                    and str(path) not in paths, 'original compressed file differs or catalog path duplicated')
            records.append(dict(path=str(path), identity=row['identity'], blob=blob, evidence_root=str(snapshot_root)))
            paths.add(str(path)); total += blob['compressed_bytes']; allocated += ((blob['compressed_bytes']+4095)//4096)*4096
        require(total == projection['compressed_bytes'] == manifest['compressed_bytes'] <= limits['maximum_compressed_bytes']
                and allocated == projection['compressed_allocated_bytes'], 'original compressed accounting differs')
        proofs.append(association)
    return dict(policy=POLICY, priority=list(PRIORITY), predecessors=proofs,
                records=records, evidence_roots=dict(sorted(roots.items())))


def select(records, bindings):
    """Keep all logical records; choose at most one retained blob per digest."""
    require(bindings['policy'] == POLICY and bindings['priority'] == PRIORITY
            and [row['role'] for row in bindings['predecessors']] == PRIORITY,
            'unreviewed predecessor selection policy')
    wanted = {}; sources = set()
    for row in records:
        require(set(row) == {'path', 'sha256', 'size', 'identity'} and hash_token(row['sha256'])
                and row['path'] not in sources and type(row['size']) is int and row['size'] >= 0,
                'complete unique logical source records required')
        require(row['sha256'] not in wanted or wanted[row['sha256']] == row['size'], 'logical alias size mismatch')
        wanted[row['sha256']] = row['size']; sources.add(row['path'])
    require(sources, 'empty logical selection')
    selected = {}; inodes = set(); paths = set(); used = set()
    for row in bindings['records']:
        key = row['blob']['logical_sha256']
        if key not in wanted or key in selected:
            continue
        require(row['blob']['logical_bytes'] == wanted[key], 'candidate differs from selected logical bytes')
        inode = (row['identity']['dev'], row['identity']['ino'])
        require(row['identity']['nlink'] == 1 and inode not in inodes and row['path'] not in paths
                and row['evidence_root'] in bindings['evidence_roots'], 'duplicate physical reference credit')
        selected[key] = row; inodes.add(inode); paths.add(row['path']); used.add(row['evidence_root'])
    return dict(records=[selected[key] for key in sorted(selected)],
                evidence_roots={name:bindings['evidence_roots'][name] for name in sorted(used)})


def reservation(projection, maximum_manifest_bytes, remaining_bytes):
    """Reserve only new physical blobs; old roots stay in the monitor's total."""
    blobs = projection['blobs']; storage = projection['storage']
    require(set(storage) == set(blobs), 'complete physical storage selection required')
    keys = [key for key in blobs if storage[key]['kind'] == 'stored']
    require(all(row['kind'] in ['stored', 'reused'] for row in storage.values()), 'unknown physical storage role')
    allocated = sum(((blobs[key]['compressed_bytes']+4095)//4096)*4096 for key in keys)
    require(allocated == projection['new_compressed_allocated_bytes'], 'new physical allocation projection differs')
    return allocated+4096*len(keys)+2*maximum_manifest_bytes+remaining_bytes
