"""Separate elapsed JIT preparation intervals from complete edited commands.

Compilation intervals overlap across workers; they are neither CPU time nor
measured recoverable command wall time. Published code counters are cumulative
per worker, whereas jit_compile_ns is an invocation delta (prepared.rs).
"""
import math

BASELINE='df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'


def integer(value):
    assert type(value) is int and 0 <= value < 2**128
    return value


def seconds(value):
    assert type(value) in (float,int) and math.isfinite(value) and value >= 0
    return value


def measure(row,suite):
    assert row['mode']=='baseline' and integer(row['state']) in range(1,6)
    assert row['returncode']==0 and row['source_sha256']!=row['previous_source_sha256']
    integer(row['cycle'])
    launch=row['launch']
    assert launch['tool_key']==BASELINE and launch['isolated_batch']=='prepared'
    for key in ['jit_scalar_calls','jit_resumable_calls','jit_persistent_registers']:assert launch[key] is True
    for key in ['jit_indirect_calls','jit_native_calls','jit_native_call_stubs']:assert launch[key] is False
    assert suite['schema_version']==1 and suite['status']=='passed' and suite['mode']=='prepared'
    tests=suite['tests'];assert tests and suite['passed']==len(tests) and suite['failed']==0
    assert len({t['name'] for t in tests})==len(tests)
    assert sorted(row['outcomes'])==sorted([[t['name'],'passed'] for t in tests])
    workers=integer(suite['workers']);assert 1<=workers<=2 and launch['suite_workers']==workers
    assert suite['requested_workers']==2 and workers==min(2,len(tests))
    wall=seconds(row['wall_seconds'] if 'wall_seconds' in row else row['seconds'])
    execution=seconds(launch['execution_seconds']);suite_time=seconds(suite['seconds_before_report_write'])
    assert 0<suite_time<=execution+1e-6 and execution<=wall+1e-6
    by_worker=[dict(tests=0,test_seconds=0.,compile_seconds=0.,code_bytes=0,functions=0,declines=0) for _ in range(workers)]
    for test in tests:
        assert test['status']=='passed'
        worker=integer(test['worker']);assert worker<workers
        item=by_worker[worker];duration=seconds(test['seconds'])
        compile_seconds=integer(test['jit_compile_ns'])/1e9
        assert compile_seconds<=duration+1e-6
        item['tests']+=1;item['test_seconds']+=duration;item['compile_seconds']+=compile_seconds
        for source,dest in [('jit_bytes','code_bytes'),('jit_compiled_functions','functions'),('jit_declined_functions','declines')]:
            count=integer(test[source]);assert count>=item[dest],'cumulative owner counter decreased'
            item[dest]=count
        assert item['code_bytes']<=integer(suite['jit_code_limit_bytes'])
    assert all(w['test_seconds']<=suite_time+1e-6 for w in by_worker)
    compile_sum=sum(w['compile_seconds'] for w in by_worker)
    return dict(cycle=row['cycle'],state=row['state'],command_seconds=wall,
        execution_seconds=execution,suite_seconds=suite_time,workers=by_worker,
        compile_interval_sum_seconds=compile_sum,
        largest_worker_compile_seconds=max(w['compile_seconds'] for w in by_worker),
        compile_interval_sum_over_command=compile_sum/wall,
        compile_interval_sum_over_execution=compile_sum/execution,
        constructor_interval_sum_seconds=integer(suite['preparation_ns'])/1e9,
        retained_code_bytes=sum(w['code_bytes'] for w in by_worker),
        retained_function_owners=sum(w['functions'] for w in by_worker),
        declined_function_owners=sum(w['declines'] for w in by_worker),
        tests=len(tests))
