"""Archive saved mono compiler retirement evidence; never inspect/remove compiler files."""
import collections
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tarfile
import time

OWNER = Path(__file__).resolve().parents[1]
PRIMARY = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
BASE = PRIMARY / '.work'
RETIRE = BASE / 'mono-compiler-intermediate-retirement-01'
INSPECT = BASE / 'mono-compiler-intermediate-inventory-02'
FAILED = BASE / 'mono-compiler-intermediate-inventory-01'
PROPOSAL = BASE / 'mono-compiler-intermediate-proposal-01.json'
RETIRE_SHA = '2b1e08ea14a86eb19563c85fca8a479f1daca563ff92f324752ea19e023aac05'
INSPECT_SHA = 'a52e05c65c2d0063d158a7fcb042607a45e925c7dd8c52160f4cf0ab09105002'
FAILED_SHA = '585acfeae96fa4df1e86badd0e4177fce13c2458c6073d748d7e6bea69a87952'
PROPOSAL_SHA = '99c6189c99656c9f97b68d88f07d7ab91886104209ebf454d51649ac89f16be1'
RETIRE_SOURCE_SHA = 'e035d223ce13490087c3368f30452845e5e604ccd0a825cb79324b8c9be24df0'
HELPERS = {
    'experiments/stable-cgu/owned_stage.py': '7021a15d3b806ab908f03276051d9d9ca9c9e208bbf8933a60229c9fb35bb68e',
    'scripts/supervise_experiment.py': '019608c2d37fcecb55ed436fafe3753498bfe11e1a1805a46ae49a59c7d6a1b2',
}
sys.path.insert(0, str(OWNER / 'experiments/stable-cgu'))
from owned_stage import CANONICAL_LOCK, workload_lock, sha, write, require, disk


def main():
    output = OWNER / 'results/mono-compiler-intermediate-retirement-01'
    receipt_path = OWNER / '.work/mono-compiler-intermediate-archive-01.json'
    require(not output.exists() and not receipt_path.exists(), 'fresh archive destinations required')
    receipt = dict(status='waiting', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(),
        owner=str(OWNER), input_owner=str(PRIMARY), canonical_lock=str(CANONICAL_LOCK), wait_seconds=600,
        runner_sha256=sha(Path(__file__)), builds=0, tests=0, benchmarks=0, deletions=0, process_controls=0,
        live_compiler_or_dependency_inspection=False)
    write(receipt_path, receipt)
    try:
        with workload_lock(CANONICAL_LOCK, 600):
            disk(OWNER)
            receipt.update(status='running', admitted_at=time.time())
            write(receipt_path, receipt)
            files = {}

            def add(path, expected=None, *, original=None):
                path = Path(path)
                require(path.is_file() and not path.is_symlink() and path.resolve(strict=True) == path,
                    'archive input must be an ordinary canonical evidence file')
                require(path.is_relative_to(BASE) or path.is_relative_to(OWNER), 'unexpected evidence owner')
                data = path.read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                require(expected is None or digest == expected, 'historical evidence hash changed: ' + str(path))
                identity = Path(original) if original is not None else path
                require(identity.is_absolute() and '..' not in identity.parts, 'unsafe archive identity')
                name = 'original/' + str(identity).lstrip('/')
                row = dict(source=str(path), original=str(identity), sha256=digest, bytes=len(data))
                if name in files:
                    require(files[name]['sha256'] == digest and files[name]['bytes'] == len(data), 'duplicate identity differs')
                else:
                    files[name] = row
                return data

            def read(path, expected=None):
                return json.loads(add(path, expected))

            def supervisor(runner_name, run_name, stage, expected_code, source_name):
                runner = BASE / runner_name
                folder = runner / '.work/experiments' / run_name
                status = read(folder / 'status.json')
                plan = read(folder / 'plan.json', status['plan_sha256'])
                add(folder / 'command.log', status['log_sha256'])
                add(folder / 'supervisor.log')
                require(status['status'] == 'finished' and status['returncode'] == expected_code
                    and status['child_pid'] == stage['pid'] and status['supervisor_pid'] == stage['parent_pid']
                    and status['owner'] == plan['owner'] == str(runner) and status['cwd'] == str(runner)
                    and status['command'] == plan['command'], 'historical supervisor/child association differs')
                require(plan['supervisor_sha256'] == HELPERS['scripts/supervise_experiment.py'], 'supervisor source differs')
                require(stage['runner'] == str(runner), 'stage runner differs')
                add(runner / 'scripts/supervise_experiment.py', plan['supervisor_sha256'])
                for name in [source_name, 'workflow_io.py']:
                    add(runner / 'scripts' / name)
                return status

            def quiescence(work, stage):
                saved = read(work / 'quiescence.json')
                require(saved == stage['quiescence'] and set(saved) == {'processes', 'handles'}, 'saved quiescence differs')
                for label, value in saved.items():
                    child = read(work / (label + '-process.json'))
                    require(value['returncode'] == child['returncode'] == 0 and child['status'] == 'finished'
                        and child['pid'] == value['pid'] and child['parent_pid'] == stage['pid']
                        and value['matches'] == [] and value['raw_output_retained'] is False
                        and value['stderr_lines'] == 0
                        and value['stderr_sha256'] == hashlib.sha256(b'').hexdigest(), 'saved quiescence incomplete')
                    require('stdout' not in child and 'stderr' not in child, 'unfiltered host output cannot be published')

            retired = read(RETIRE / 'summary.json', RETIRE_SHA)
            inspected = read(INSPECT / 'summary.json', INSPECT_SHA)
            failed = read(FAILED / 'summary.json', FAILED_SHA)
            proposal = read(PROPOSAL, PROPOSAL_SHA)
            require(retired['status'] == inspected['status'] == 'passed'
                and retired['owner'] == inspected['owner'] == str(PRIMARY)
                and retired['inspection_sha256'] == INSPECT_SHA
                and retired['proposal_sha256'] == inspected['proposal_sha256'] == PROPOSAL_SHA,
                'frozen successful retirement/inventory identity differs')
            require(inspected['deleted'] == [] and inspected['retirement_authorized'] is False
                and inspected['all_candidate_and_preserved_identities_unchanged'] is True,
                'inventory must remain an inspection, not a retirement claim')
            for name, digest in inspected['proof_files'].items():
                require(Path(name).name == name, 'unexpected inventory metadata path')
                add(INSPECT / name, digest)
            inventory = json.loads(gzip.decompress(add(INSPECT / 'inventory.json.gz', retired['inventory_sha256'])))
            selected = read(RETIRE / 'selected-files.json', retired['selected_sha256'])
            eligible = [r for r in inventory if r['status'] == 'eligible']
            excluded = [r for r in inventory if r['status'] == 'excluded']
            require(len(inventory) == len({r['path'] for r in inventory}) == inspected['proposed_files'] == 404
                and len(eligible) == inspected['eligible_files'] == retired['selected_count'] == 258
                and len(excluded) == inspected['excluded_files'] == retired['excluded_count'] == 146
                and selected == eligible, 'selected/excluded inventory binding differs')
            require({r['path'] for r in inventory} == {p for c in proposal['candidates'] for p in c['proposed_files']},
                'proposal and actual inventory differ')
            require(dict(collections.Counter(r['reason'] for r in excluded)) == inspected['exclusions'] == {
                'hardlink count exceeds proposed names': 73, 'preserved dependency inode': 73}, 'exclusion reasons differ')
            require([{k: r[k] for k in ['path', 'sha256', 'state']} for r in retired['deleted']]
                == [{k: r[k] for k in ['path', 'sha256', 'state']} for r in selected], 'deleted file receipts differ')
            require(all(retired['admitted_at'] <= r['finished_at'] <= retired['finished_at'] for r in retired['deleted']),
                'deletion timestamps outside recorded retirement')
            require(retired['excluded_files_unchanged'] is True
                and retired['all_preserved_dependencies_and_proofs_unchanged'] is True
                and retired['only_selected_ordinary_files_removed'] is True and retired['directories_removed'] == 0
                and retired['builds'] == retired['benchmarks'] == retired['process_controls'] == 0,
                'historical retention/scope checks did not pass')
            protected = read(INSPECT / 'preserved-dependencies.json', inspected['proof_files']['preserved-dependencies.json'])
            require(len(protected) == inspected['preserved_dependencies'] == retired['preserved_dependency_count'] == 63448,
                'protected metadata count differs')
            inodes = {(r['state']['device'], r['state']['inode']) for r in selected}
            require(len(inodes) == 258 and all(r['state']['nlink'] == 1 for r in selected), 'selected unique inode contract differs')
            require(not {r['path'] for r in selected}.intersection(protected)
                and not inodes.intersection((s['device'], s['inode']) for s in protected.values() if s),
                'saved protected path/inode overlap')
            require(sum(r['state']['blocks'] * 512 for r in selected)
                == inspected['eligible_allocated_bytes'] == retired['eligible_allocated_bytes'] == 3484483584,
                'recorded allocation estimate differs')

            proofs = read(INSPECT / 'proof-manifest.json', inspected['proof_files']['proof-manifest.json'])
            require(len(proofs) == inspected['retained_proofs'] == retired['retained_proof_count'] == 85
                and sum(p['bytes'] for p in proofs.values()) == 37896662, 'proof payload set differs')
            for original, value in proofs.items():
                digest = value['sha256']
                require(re.fullmatch('[0-9a-f]{64}', digest), 'invalid proof digest')
                data = add(INSPECT / 'proof-bytes' / digest, digest, original=original)
                require(len(data) == value['bytes'] == value['state']['bytes'], 'proof payload size differs')
                data.decode('utf-8')  # These85 retained payloads are text metadata/logs, never dependency binaries.
            referenced = [proposal['completed'], *proposal['receipts'].values()]
            for command in proposal['actual_commands']:
                referenced.extend([dict(path=command['receipt'], sha256=command['sha256']),
                    dict(path=command['stderr'], sha256=command['stderr_sha256'])])
            require(all(proofs.get(ref['path'], {}).get('sha256') == ref['sha256'] for ref in referenced),
                'proposal producer receipt/log is absent from actual archived proof payloads')
            source_inputs = read(RETIRE / 'source-inputs.json', 'fcd758ce74d2e5ae60f335e5cb3451dedf18fc5ca15e8fe72fadddce868229fb')
            require(len(source_inputs) == 3, 'retirement source inventory differs')
            for original, digest in source_inputs.items():
                path = Path(original)
                require(path.parent == BASE / 'mono-compiler-intermediate-retirement-runner-01/scripts', 'unexpected retirement source')
                add(RETIRE / 'sources' / path.name, digest)
                add(path, digest)
            require(source_inputs[str(BASE / 'mono-compiler-intermediate-retirement-runner-01/scripts/retire.py')]
                == RETIRE_SOURCE_SHA, 'frozen retirement implementation differs')
            supervisor('mono-compiler-intermediate-retirement-runner-01', 'retirement-supervisor-01', retired, 0, 'retire.py')
            supervisor('mono-compiler-intermediate-inventory-runner-02', 'inventory-supervisor-02', inspected, 0, 'inventory.py')
            quiescence(RETIRE, retired)
            quiescence(INSPECT, inspected)

            require(failed['status'] == 'failed' and failed['deleted'] == [] and failed['error'] == 'AssertionError()',
                'historical failed inventory relabeled')
            supervisor('mono-compiler-intermediate-inventory-runner-01', 'inventory-supervisor-01', failed, 1, 'inventory.py')
            for name in ['source-head.json', 'source-head-process.json']:
                add(FAILED / name)
            partial = sorted((FAILED / 'proof-bytes').iterdir())
            require(len(partial) == 25, 'partial failed proof payload count differs')
            for path in partial:
                require(re.fullmatch('[0-9a-f]{64}', path.name), 'unexpected partial proof name')
                add(path, path.name).decode('utf-8')
            for name in ['inventory.py', 'workflow_io.py', 'supervise_experiment.py']:
                path = BASE / 'mono-compiler-intermediate-inventory-runner-01/scripts' / name
                require(sha(path) in {p.name for p in partial}, 'failed runner source was not retained')
            for relative, digest in HELPERS.items():
                add(OWNER / relative, digest)
            add(Path(__file__), receipt['runner_sha256'])

            output.mkdir(parents=True, exist_ok=False)
            archive = output / 'evidence.tar.gz'
            with tarfile.open(archive, 'w:gz', compresslevel=6) as tar:
                for name, row in sorted(files.items()):
                    disk(OWNER)
                    data = Path(row['source']).read_bytes()
                    require(hashlib.sha256(data).hexdigest() == row['sha256'], 'evidence changed while archiving')
                    entry = tarfile.TarInfo(name)
                    entry.size = len(data)
                    entry.mode = 0o644
                    entry.mtime = 0
                    tar.addfile(entry, io.BytesIO(data))
            with tarfile.open(archive, 'r:gz') as tar:
                members = tar.getmembers()
                require(len(members) == len(files) and len({m.name for m in members}) == len(files), 'archive members differ')
                for member in members:
                    require(member.isfile() and member.name in files
                        and hashlib.sha256(tar.extractfile(member).read()).hexdigest() == files[member.name]['sha256'],
                        'archive readback hash differs')
            for row in files.values():
                require(sha(row['source']) == row['sha256'], 'retained input changed during collection')
            write(output / 'manifest.json', files)
            result = dict(status='passed', input_retirement_sha256=RETIRE_SHA, inspected_sha256=INSPECT_SHA,
                selected=258, excluded=146, exclusion_reasons=inspected['exclusions'], protected_metadata_entries=63448,
                retained_proof_records=85, retained_proof_payload_bytes=37896662,
                failed_inventory=dict(status='failed', helper=failed['pid'], supervisor=failed['parent_pid'], partial_payloads=25),
                retirement=dict(helper=retired['pid'], supervisor=retired['parent_pid'], admitted_at=retired['admitted_at'],
                    finished_at=retired['finished_at'], free_bytes_before=retired['free_bytes_before'],
                    free_bytes_after=retired['free_bytes_after'], observed_free_space_increase=retired['free_bytes_after']-retired['free_bytes_before'],
                    selected_allocated_bytes=retired['eligible_allocated_bytes'], directories_removed=0),
                verification_scope='Saved cleanup receipts and metadata; no current compiler/dependency inspection or new deletion.',
                quiescence_scope='Only saved empty matching subsets, command receipts and raw hashes/counts; full host process/handle tables were not retained.',
                protected_binary_payloads_archived=0, archive=dict(path='evidence.tar.gz', members=len(files),
                    bytes=archive.stat().st_size, sha256=sha(archive), all_member_hashes_verified=True))
            write(output / 'summary.json', result)
            receipt.update(status='passed', finished_at=time.time(), archive=result['archive'])
            write(receipt_path, receipt)
            write(output / 'archive-receipt.json', receipt)
            print(json.dumps(result, indent=2))
    except BaseException as error:
        receipt.update(status='failed', error=repr(error), finished_at=time.time())
        write(receipt_path, receipt)
        raise


if __name__ == '__main__':
    main()
