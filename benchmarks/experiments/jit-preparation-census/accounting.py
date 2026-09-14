"""Accounting of existing intervals, with no inferred critical-path savings."""
import math


def analyze(suite, command_seconds, execution_seconds):
    assert suite['status']=='passed' and suite['mode']=='prepared'
    assert suite['failed']==0 and suite['passed']==len(suite['tests'])
    workers=suite['workers'];assert type(workers) is int and 1<=workers<=2
    duration=suite['seconds_before_report_write']
    assert all(math.isfinite(x) and x>0 for x in [duration,command_seconds,execution_seconds])
    preparation=suite['preparation_ns'];assert type(preparation) is int and preparation>=0
    assert preparation/1e9<=workers*duration
    per_worker=[dict(tests=0,compile_ns=0,test_seconds=0.0,code_bytes=0,compiled_functions=0) for _ in range(workers)]
    for test in suite['tests']:
        assert test['status']=='passed'
        worker=test['worker'];assert type(worker) is int and 0<=worker<workers
        seconds=test['seconds'];assert math.isfinite(seconds) and seconds>=0
        for field in ['jit_compile_ns','jit_bytes','jit_compiled_functions']:
            assert type(test[field]) is int and test[field]>=0
        assert test['jit_compile_ns']/1e9<=seconds+1e-6
        row=per_worker[worker]
        # Reports preserve source selection order, which also preserves each
        # worker's execution order despite dynamic distribution between workers.
        assert test['jit_bytes']>=row['code_bytes'] and test['jit_compiled_functions']>=row['compiled_functions']
        row['tests']+=1;row['compile_ns']+=test['jit_compile_ns'];row['test_seconds']+=seconds
        row['code_bytes']=test['jit_bytes'];row['compiled_functions']=test['jit_compiled_functions']
    total=sum(r['compile_ns'] for r in per_worker)/1e9
    largest=max(r['compile_ns'] for r in per_worker)/1e9
    return dict(workers=workers,tests=len(suite['tests']),per_worker=per_worker,
        command_seconds=command_seconds,execution_seconds=execution_seconds,suite_seconds=duration,
        constructor_sum_seconds=preparation/1e9,compile_sum_seconds=total,largest_worker_compile_seconds=largest,
        compile_sum_to_command=total/command_seconds,largest_worker_compile_to_command=largest/command_seconds,
        constructor_sum_to_command=preparation/1e9/command_seconds,
        constructor_plus_compile_interval_sum_to_command=(preparation/1e9+total)/command_seconds)
