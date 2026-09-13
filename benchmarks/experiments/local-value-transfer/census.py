"""Reconstruct saved generated code and inspect test-only guarded local facts."""
import collections
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write


def weighted(census, mapping, profile):
    reports = []
    for current, saved in zip(census['functions'], mapping['functions']):
        fid = current['function']; assert fid == saved['function']
        f = profile['functions'][fid]
        assert f['name'] == current['name']
        pcs = {s['pc']: s['region_pc'] for s in saved['spans'] if s['pc'] is not None}
        def hits(pc):
            region = pcs[pc]
            assert region <= pc < f['jit_block_ends'][region]
            return f['jit_blocks'][region]
        baseline = {(pc, op): kind for pc, op, kind in current['baseline_forwarding']}
        assert len(baseline) == len(current['baseline_forwarding'])
        candidate = current['candidate']
        if candidate['status'] != 'emitted':
            reports.append(dict(function=fid, status='declined', baseline_bytes=current['baseline_end']-current['baseline_offset']))
            continue
        alternative = {(pc, op): kind for pc, op, kind in candidate['forwarding']}
        assert len(alternative) == len(candidate['forwarding'])
        extra = sorted(alternative.keys()-baseline.keys()); lost = sorted(baseline.keys()-alternative.keys())
        facts = collections.Counter()
        for (pc, _), kind in baseline.items(): facts[kind] += hits(pc)
        static = []
        for spans in [saved['spans'], candidate['spans']]:
            totals = collections.Counter()
            for span in spans:
                assert span['end'] >= span['offset'] and (span['end']-span['offset']) % 4 == 0
                totals[span['kind']] += ((span['end']-span['offset'])//4) * f['jit_blocks'][span['region_pc']]
            static.append(totals)
        outcomes=collections.Counter(); transferred=0; incompatible=0
        event_pcs=set()
        for event in candidate['transfers']:
            pc=event['pc']; assert pc not in event_pcs; event_pcs.add(pc)
            count=hits(pc)
            outcomes[event['outcome']] += count
            transferred += count*event['transferred']
            incompatible += count*event['too_wide']
        reports.append(dict(function=fid, name=f['name'], status='emitted',
            transfer_outcomes_weighted=dict(outcomes), transferred_references_weighted=transferred,
            incompatible_references_weighted=incompatible,
            baseline_bytes=current['baseline_end']-current['baseline_offset'], candidate_bytes=candidate['bytes'],
            words_equal=candidate['words_equal'],
            additional=[dict(pc=pc, opcode=op, fact=alternative[(pc, op)], region_hits=hits(pc)) for pc, op in extra],
            lost=[dict(pc=pc, opcode=op, fact=baseline[(pc, op)], region_hits=hits(pc)) for pc, op in lost],
            retained_writes=[dict(pc=pc, register=reg, size=size, live_values=count, region_hits=hits(pc))
                             for pc, reg, size, count in candidate['retained_writes']],
            baseline_forwarding_by_fact_weighted=dict(facts),
            weighted_static_word_delta={kind:static[1][kind]-static[0][kind] for kind in sorted(static[0].keys()|static[1].keys())}))
    assert len(reports) == len(census['functions']) == len(mapping['functions'])
    outcomes=collections.Counter()
    word_deltas=collections.Counter()
    for report in reports:
        outcomes.update(report.get('transfer_outcomes_weighted',{}))
        word_deltas.update(report.get('weighted_static_word_delta',{}))
    return dict(functions=reports, transfer_outcomes_weighted=dict(outcomes),
        transferred_references_weighted=sum(f.get('transferred_references_weighted',0) for f in reports),
        incompatible_references_weighted=sum(f.get('incompatible_references_weighted',0) for f in reports),
        weighted_static_word_delta=dict(word_deltas), additional_weighted=sum(s['region_hits'] for f in reports for s in f.get('additional', [])),
        lost_weighted=sum(s['region_hits'] for f in reports for s in f.get('lost', [])),
        changed_functions=sum(f.get('words_equal') is False for f in reports),
        declined_functions=sum(f['status']=='declined' for f in reports),
        note='Frequency-weighted static sites/words; not retired instructions, uniform path execution, or latency')


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45); require_space(ROOT, 12)
        proof_path = ROOT / 'results/guarded-local-facts-profile-01/summary.json'
        proof = json.loads(proof_path.read_text()); prior = ROOT / proof['raw']
        assert proof['status'] == 'passed' and proof['exact_operation_map_reconstruction']
        assert proof['tool_key'] == '317a0bf16da0f15f562ab457408ab321b12f25211f8169ec8bcd8205a3cb7dfb'
        build_path=ROOT/'results/local-value-transfer-build-01/summary.json'
        build=json.loads(build_path.read_text())
        assert build['status']=='passed' and build['tests']=={p:dict(passed=411,ignored=6) for p in ['debug','release']}
        build_plan=ROOT/build['raw']/'plan.json'
        assert sha(build_plan)==build['plan_sha256']
        assert all(sha(ROOT/p)==h for p,h in json.loads(build_plan.read_text())['frozen'].items())
        for name in ['plan', 'records']: assert sha(prior / (name + '.json')) == proof[name + '_sha256']
        references = json.loads((prior / 'records.json').read_text())
        assert len(references) == 3
        paths = [build_path,build_plan,Path(__file__), Path(__file__).with_name('PLAN.md'), proof_path, prior/'plan.json', prior/'records.json',
                 ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'rust-toolchain.toml']
        cases = []
        for index, row in enumerate(references):
            artifact = Path(row['command'][-1]); mapping = prior/f'{index}-code/operations.json'
            code = prior/f'{index}-code/code.bin'; profile = prior/f'{index}-profile.json'
            selection, = [json.loads(line.split(': ',1)[1]) for line in row['stderr'].splitlines()
                          if line.startswith('rust-interp-profile-selection: ')]
            comparison, = [c for c in proof['comparisons'] if c['index']==index]
            assert selection['name']==comparison['name'] and row['returncode']==0
            assert sha(artifact) == selection['artifact_sha256']
            assert sha(profile) == comparison['profile_sha256']
            assert sha(mapping) == comparison['operation_map_sha256']
            assert sha(code) == comparison['code_sha256']
            cases.append(dict(artifact=artifact, mapping=mapping, code=code, profile=profile, selection=selection))
            paths += [artifact, mapping, code, profile]
        paths += [p for p in (ROOT/'crates/bytecode').rglob('*') if p.is_file() and (p.suffix=='.rs' or p.name=='Cargo.toml')]
        frozen = {str(p.relative_to(ROOT)):sha(p) for p in paths}
        work = ROOT/'.work/local-value-transfer-census-01'; work.mkdir(exist_ok=False)
        target = ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        command = ['cargo','+nightly-2026-09-08','test','--release','--locked','--offline','--jobs','2',
                   '--target-dir',str(target),'-p','rust-interp-bytecode','--lib',
                   'jit::code_spans::local_census::observe_saved_local_transfers','--','--ignored','--exact','--nocapture','--test-threads=1']
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,command=command,expected_commands=3,
            guest_commands=0,executable_code_publications=0,static_fact_preservation=True,scalar_copy=True,initial_gib=12,minimum_child_gib=8,
            selections=[c['selection'] for c in cases],performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_'))
             and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0',CARGO_PROFILE_RELEASE_DEBUG='1')
        rows, summaries = [], []
        for index, case in enumerate(cases):
            require_space(ROOT,8)
            output=work/f'{index}-census.json'
            selected=dict(env,LOCAL_CENSUS_ARTIFACT=str(case['artifact']),LOCAL_CENSUS_MAP=str(case['mapping']),
                          LOCAL_CENSUS_CODE=str(case['code']),LOCAL_CENSUS_OUTPUT=str(output),LOCAL_CENSUS_STATIC_FACTS='1',LOCAL_CENSUS_SCALAR_COPY='1')
            child,out,err=capture(command,cwd=ROOT,env=selected,receipt_path=work/'active.json',receipt=dict(index=index))
            (work/f'{index}.stdout').write_text(out);(work/f'{index}.stderr').write_text(err)
            rows.append(dict(index=index,command=command,pid=child.pid,returncode=child.returncode,
                stdout_sha256=sha(work/f'{index}.stdout'),stderr_sha256=sha(work/f'{index}.stderr')))
            write(work/'records.json',rows)
            assert child.returncode==0 and 'test result: ok. 1 passed; 0 failed;' in out,err[-3000:]
            census=json.loads(output.read_text());assert census['exact_baseline_reconstruction'] and census['static_fact_preservation'] and census['scalar_copy'] and census['local_value_transfers']
            assert census['guest_commands']==census['executable_code_publications']==0
            analysis=weighted(census,json.loads(case['mapping'].read_text()),json.loads(case['profile'].read_text()))
            write(work/f'{index}-analysis.json',analysis)
            summaries.append(dict(index=index,name=case['selection']['name'],baseline_bytes=census['baseline_bytes'],
                candidate_bytes=census['candidate_bytes'],**{k:v for k,v in analysis.items() if k!='functions'},
                census_sha256=sha(output),analysis_sha256=sha(work/f'{index}-analysis.json')))
            print(json.dumps(summaries[-1]),flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results/local-value-transfer-census-01';result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=3,guest_commands=0,executable_code_publications=0,
            cases=summaries,raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            frozen_inputs_verified=len(frozen),performance_measurement=False))


if __name__=='__main__':main()
