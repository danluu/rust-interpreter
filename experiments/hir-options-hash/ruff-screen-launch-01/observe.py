#!/usr/bin/env python3
"""Observe one ordinary fixed Ruff history, then its saved verifier. No cleanup."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--inputs-sha256', required=True)
    parser.add_argument('--sources-sha256', required=True)
    parser.add_argument('--history', choices=['ab', 'aa'], required=True)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--previous-sha256')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    # Authenticate the adjacent helper before importing it, then its full closure.
    manifest = here/'sources.json'
    payload = manifest.read_bytes()
    if hashlib.sha256(payload).hexdigest() != args.sources_sha256:
        raise RuntimeError('source manifest changed')
    sources = json.loads(payload)
    source = here/'prepare.py'
    if hashlib.sha256(source.read_bytes()).hexdigest() != sources['files'][str(source)]:
        raise RuntimeError('preparation helper changed')
    spec = importlib.util.spec_from_file_location('_ruff_screen_prepare', source)
    p = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(p)
    checked = {}
    p.authenticate(dict(path=str(manifest), sha256=args.sources_sha256), checked)
    plan_ref = dict(path=str(p.PACKET/'plan.json'), sha256=args.plan_sha256)
    plan = p.pinned(plan_ref, checked)
    frozen = p.pinned(dict(path=str(p.PACKET/'inputs.json'), sha256=args.inputs_sha256))
    p.require(plan['policy'] == 'ruff-fixed-screen-plan-v1' and plan['order'] == ['ab', 'aa']
              and plan['sources'] == dict(path=str(manifest), sha256=args.sources_sha256)
              and Path.cwd() == p.R and sys.dont_write_bytecode and not sys.flags.optimize,
              'packet, source, cwd or Python invocation differs')
    h = plan['histories'][args.history]
    p.require(dict(os.environ) == h['environment'], 'exact reviewed workload environment required')
    owned = p.load(p.OWNED, '_ruff_screen_owned')
    work = Path(h['observer'])
    p.absent(work)
    work.mkdir()
    (work/'tmp').mkdir()
    result_path = work/'result.json'
    record_path = work/'receipt.json'
    record = dict(policy='ruff-fixed-screen-observation-v1', status='starting', history=args.history,
        pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time(), cwd=str(p.R),
        environment=dict(os.environ), plan=plan_ref, histories_order=['ab', 'aa'],
        child_receipts=[], performance_qualified=False, observer_os_closure_observed=False)

    def save():
        owned.write(record_path, record)

    def guard():
        for name, row in frozen['files'].items():
            p.require(p.sha(name) == row['sha256'] and p.stamp(name) == row['stamp'], 'prepared input changed: '+name)
        p.require(p.sha(p.PACKET/'plan.json') == args.plan_sha256
                  and p.sha(p.PACKET/'inputs.json') == args.inputs_sha256, 'packet changed')

    def footprint():
        # Only task-owned generated roots. No provider, holdout or peer tree scan.
        roots = [Path(h[k]) for k in ['work', 'results', 'observer', 'outer']]
        roots += [p.R/'.work'/(h['run_id']+'-execution')]
        roots += list(map(Path, h['custom_caches'].values()))
        seen = set()
        allocated = logical = count = evidence = 0
        caches = list(map(Path, [h['native_cache'], *h['custom_caches'].values()]))
        for root in roots:
            if not root.exists():
                continue
            p.require(not root.is_symlink(), 'owned root replaced by symlink')
            for directory, dirs, files in os.walk(root, followlinks=False):
                for name in [*dirs, *files]:
                    s = (Path(directory)/name).lstat()
                    p.require(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode), 'unexpected owned output kind')
                    count += 1
                    p.require(count <= 100000, 'owned output entry bound exceeded')
                    logical += s.st_size if stat.S_ISREG(s.st_mode) else 0
                    inode = (s.st_dev, s.st_ino)
                    if inode not in seen:
                        seen.add(inode)
                        allocated += s.st_blocks*512
                        path = Path(directory)/name
                        if not any(path.is_relative_to(cache) for cache in caches):
                            evidence += s.st_blocks*512
        p.require(allocated <= 8*p.GIB, 'owned history allocation exceeded8GiB')
        p.require(evidence <= 512*p.MIB, 'retained history evidence exceeded512MiB')
        return dict(allocated_bytes=allocated, logical_file_bytes=logical, entries=count,
                    retained_evidence_allocated_bytes=evidence,
                    free_bytes=owned.disk(p.R, 8), measured_at=time.time())

    save()
    try:
        prior = None
        if args.history == 'aa':
            p.require(args.previous is not None and args.previous_sha256 is not None, 'AA requires closed AB/retirement binding')
            prior = p.pinned(dict(path=str(args.previous), sha256=args.previous_sha256))
            p.require(set(prior) == {'ab_result', 'ab_receipt', 'ab_outer', 'retirement_review'}, 'previous binding fields differ')
            ab = plan['histories']['ab']
            p.require(prior['ab_result']['path'] == ab['observer']+'/result.json'
                      and prior['ab_receipt']['path'] == ab['observer']+'/receipt.json'
                      and prior['ab_outer']['path'] == ab['outer']+'/status.json', 'AB owner paths differ')
            outcome = p.pinned(prior['ab_result'])
            controller = p.pinned(prior['ab_receipt'])
            p.require(outcome['status'] == controller['status'] == 'passed'
                      and outcome['history'] == 'ab' and outcome['plan'] == plan_ref
                      and controller['result'] == prior['ab_result'], 'AB did not pass this packet')
            p.closed_outer(prior['ab_outer'], controller, None)
            # This small externally reviewed declaration binds the existing retirement
            # workflow's actual proof(s); it is not itself a remover or a new audit.
            review = p.pinned(prior['retirement_review'])
            expected = sorted([ab['native_cache'], *ab['custom_caches'].values()])
            p.require(review['status'] == 'verified' and review['selected_roots'] == expected
                      and review['ab_result'] == prior['ab_result']
                      and review['ab_outer'] == prior['ab_outer']
                      and review['preserved_evidence'] == [outcome[k] for k in ['summary', 'records', 'verification']]
                      and review['finished_at'] >= controller['finished_at']
                      and review['retirement_proofs'], 'exact closed AB cache retirement readback required')
            for reference in review['retirement_proofs']:
                p.pinned(reference)
            for key in ['summary', 'records', 'verification']:
                p.pinned(outcome[key])
            for cache in expected:
                p.absent(cache)
        else:
            p.require(args.previous is None and args.previous_sha256 is None, 'AB has no predecessor screen')
        # Release this short admission before starting a runner which acquires the
        # canonical lock itself. The exclusive task names bridge the handoff; no
        # claim of an atomic cache-absence check across those two acquisitions.
        with owned.workload_lock(p.LOCK, 600):
            guard()
            p.prerequisites(p.pinned(plan['binding']), {})
            for cache in [h['work'], h['results'], *h['custom_caches'].values()]:
                p.absent(cache)
            # Completed strict caches must also have been separately retired.
            p.absent(p.STRICT_WORK/'cache')
            record.update(status='admitted', admitted_at=time.time(), entry_free_bytes=owned.disk(p.R, 24),
                          before=footprint(), previous=prior)
            save()
        record['admission_released_at'] = time.time()
        save()
        try:
            owned.run(h['command'], cwd=p.R, env=h['environment'], out=work/'runner', capacity_root=p.R)
        finally:
            if (work/'runner/receipt.json').exists():
                record['child_receipts'].append(p.ref(work/'runner/receipt.json'))
                save()
        runner = p.pinned(p.ref(work/'runner/receipt.json'))
        p.require(runner['status'] == 'finished' and runner['returncode'] == 0, 'runner did not close successfully')
        local_lock = p.R/'.work/benchmark.lock'
        p.require(local_lock.is_file() and local_lock.resolve(strict=True) != p.LOCK
                  and (local_lock.stat().st_dev, local_lock.stat().st_ino)
                      != (p.LOCK.stat().st_dev, p.LOCK.stat().st_ino),
                  'saved verifier local lock must be distinct from outer canonical lock')
        # Canonical ownership is separate from the runner, and the original verifier
        # retains its additional R-local lock. No runner/outer-lock deadlock.
        with owned.workload_lock(p.LOCK, 600):
            admitted = time.time()
            guard()
            record['after_history'] = footprint()
            try:
                owned.run(h['verifier'], cwd=p.R, env=h['environment'], out=work/'verifier', capacity_root=p.R)
            finally:
                if (work/'verifier/receipt.json').exists():
                    record['child_receipts'].append(p.ref(work/'verifier/receipt.json'))
                    save()
            guard()
            record['after_verification'] = footprint()
        released = time.time()
        verification = p.pinned(p.ref(h['verification']))
        summary = p.pinned(p.ref(h['summary']))
        records = p.pinned(p.ref(h['records']))
        for row in records:
            if row['mode'] != 'native' and row['state'] != -1:
                for call in row['calls']:
                    p.require(call['launch']['function_cache'] == call['launch']['borrowck_cache'] == 'off',
                              'ordinary disabled function/borrow-check caches required')
        p.require(verification['measurement_controls_verified'] is True and verification['commands'] == 24
                  and verification['edited_pairs'] == 5 and verification['paired_bytecode_identical'] is True
                  and verification['restored_original_build_and_execution_verified'] is True
                  and len(records) == len(summary['samples']) == 24
                  and summary['cache_workspaces'] == h['custom_caches'], 'complete history/cache verification differs')
        result = dict(status='passed', history=args.history, plan=plan_ref,
            runner=p.ref(work/'runner/receipt.json'), verifier=p.ref(work/'verifier/receipt.json'),
            summary=p.ref(h['summary']), records=p.ref(h['records']), verification=p.ref(h['verification']),
            canonical_verification=dict(admitted_at=admitted, released_at=released),
            generated_cache_roots=sorted([h['native_cache'], *h['custom_caches'].values()]),
            before=record['before'], after=record['after_verification'], previous=prior,
            performance_qualified=False, observer_os_closure_observed=False)
        p.write(result_path, result)
        record.update(status='passed', finished_at=time.time(), result=p.ref(result_path))
        save()
        print(json.dumps(record['result']))
    except BaseException as error:
        record.update(status='failed', error=repr(error), finished_at=time.time())
        save()
        raise


if __name__ == '__main__':
    main()
