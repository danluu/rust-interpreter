"""Read-only cache provenance for one explicitly assessed interrupted corpus.

The original failure and stale running receipts remain unchanged. Only a case
in both its completed ledger and the successful recovery assessment is eligible.
This module never licenses the incomplete case or private project caches.
"""
import json
from pathlib import Path

from verify_repeated_workflow import require

ORIGINAL = 'resumable-bulk-heldout-01'
RECOVERY = 'results/resumable-bulk-heldout-recovery-01/summary.json'
FAILURE = 'results/resumable-bulk-heldout-failure-01/summary.json'
ASSESSOR = 'benchmarks/experiments/resumable-native-calls/assess_heldout_recovery.py'
ASSESSMENT = '.work/experiments/resumable-heldout-recovery-assessment-01'
ASSESSOR_SHA = 'f2f594fd9b8d4994a97e45fefcb6e48376d9ec6f7db913050a8028ea38e1c872'
COMPLETE = {'pgrust', 'nushell', 'rg-aot', 'forward-anchored-tls', 'pgrust-sha1-inline8', 'ruff'}


def validate(bundle, root, run_id):
    recovery, failure, status, plan, assessment, launch = bundle
    require(recovery['status'] == 'seven complete cases verified across two run histories' and
            recovery['original_run_status'] == 'incomplete: ENOSPC; unchanged' and
            recovery['failure_report'] == FAILURE and recovery['assessor_sha256'] == ASSESSOR_SHA and
            recovery['counts'] == dict(primary_commands=441, check_commands=147, edited_pairs=105, artifacts=294),
            'recovery assessment identity or completeness differs')
    require(failure['run_id'] == ORIGINAL and failure['status'] == 'incomplete: ENOSPC' and
            failure['source_restored'] is True and failure['no_matching_processes'] is True and
            failure['stale_original_status_receipts_preserved'] is True and
            failure['incomplete_workflow'] == 'nushell-type-relations' and
            failure['completed_workflows'] == 6, 'failure/restoration evidence differs')
    require(status['cwd'] == str(root) and status['status'] == 'running' and
            len(status['completed']) == 6 and {r['label'] for r in status['completed']} == COMPLETE and
            status['case'] == 'nushell-type-relations', 'original completed-case ledger differs')
    require(assessment['status'] == 'finished' and assessment['returncode'] == 0 and
            assessment['owner'] == assessment['cwd'] == launch['owner'] == str(root) and
            assessment['command'] == launch['command'] == ['python3', ASSESSOR],
            'recovery assessment is not successfully terminal under this owner')
    require(plan['options']['run_id'] == ORIGINAL and
            plan['frozen'] == recovery['archived_harnesses'][ORIGINAL]['inputs'],
            'recovered corpus plan differs')
    for field in ['candidate_tool_key', 'baseline_tool_key']:
        require(plan['options'][field] == recovery[field], 'recovered tools differ')
    selected = [r for r in status['completed'] if run_id == ORIGINAL + '-' + r['label']]
    require(len(selected) == 1 and selected[0]['label'] != 'rg-aot',
            'only an assessed complete public case is eligible')
    row = selected[0]
    require(row['report'] == 'results/' + run_id + '/summary.json', 'recovered report path differs')
    matches = [r for r in recovery['workflows'] if r['workflow'] == row['label']]
    require(len(matches) == 1 and all(matches[0][k] == row[k] for k in ['report', 'report_sha256']),
            'recovery assessment does not bind this completed case')
    return dict(plan=plan, workflows=status['completed'])


def evidence(root, corpus_id, run_id, sha):
    require(corpus_id == ORIGINAL, 'no qualified recovery evidence for this corpus')
    paths = [RECOVERY, FAILURE, '.work/corpus-runs/' + ORIGINAL + '/status.json',
             '.work/corpus-runs/' + ORIGINAL + '/plan.json', ASSESSMENT + '/status.json',
             ASSESSMENT + '/plan.json']
    bundle = [json.loads((root / path).read_text()) for path in paths]
    corpus = validate(bundle, root, run_id)
    recovery, failure, status, _, assessment, _ = bundle
    require(sha(root / FAILURE) == recovery['failure_sha256'] and
            sha(root / ASSESSOR) == ASSESSOR_SHA and
            sha(root / (ASSESSMENT + '/plan.json')) == assessment['plan_sha256'] and
            sha(root / (ASSESSMENT + '/command.log')) == assessment['log_sha256'],
            'recovery evidence hashes differ')
    paths += [ASSESSOR, ASSESSMENT + '/command.log']
    required = {'.work/experiments/' + ORIGINAL + '/status.json',
                '.work/corpus-runs/' + ORIGINAL + '/status.json'}
    require(required <= set(failure['evidence']), 'failure does not preserve both original receipts')
    for source, entry in failure['evidence'].items():
        relative = Path(source)
        snapshot = Path(entry['snapshot'])
        require(not relative.is_absolute() and '..' not in relative.parts and
                relative.parts[0] == '.work' and ORIGINAL in source and
                snapshot.name == str(snapshot) and snapshot.name not in ['', '.', '..'],
                'noncanonical failure evidence path')
        saved = Path(FAILURE).parent / snapshot
        require((root / source).resolve() == root / source and (root / saved).resolve() == root / saved and
                sha(root / source) == sha(root / saved) == entry['sha256'],
                'preserved failed-run evidence changed')
        paths += [source, str(saved)]
    # The ordinary cache verifier additionally rechecks all completed command,
    # artifact and source-restoration evidence. Include the last child in the
    # caller's fresh liveness check, without changing any old process receipt.
    return corpus, [root / p for p in paths], [status['child_pid']]
