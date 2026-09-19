"""Bind an explicit runtime session to the actual server and selected artifacts."""
import hashlib,json
from pathlib import Path

def validate_selection(args):
    if (args.tool_key is None or args.engine!='jit' or not args.jit_resumable_calls or
            args.isolated_batch!='prepared' or args.suite_workers!=2 or args.jit_shared_templates or
            args.allocation_trace or args.audit_entries is not None or args.list_tests):
        raise ValueError('--jit-template-session requires --tool-key and a prepared two-worker resumable suite without shared templates, tracing or discovery modes')
    ready=args.jit_template_session
    if not ready.is_absolute() or ready.resolve(strict=True)!=ready or not ready.is_file() or ready.stat().st_size>16*1024:
        raise ValueError('--jit-template-session requires a canonical absolute readiness file')
    if args.jit_indirect_calls and json.loads(ready.read_bytes()).get('indirect_calls') is not True:
        raise ValueError('session server does not support indirect calls')
    receipt=Path(str(args.suite_report)+'.session.json')
    if receipt.exists() or receipt.is_symlink():raise ValueError('session receipt already exists')

def read_receipt(ready_path,report_path,artifact_path,catalog_path,returncode,*,expected_artifact_sha256=None,expected_jit_options=None):
    # The server binds its actual input bytes to the catalog and receipt before
    # execution. With stats, also require the launcher's pre-execution digest.
    # Re-reading artifact_path here would describe a later file, not add proof
    # about the bytes that executed. Keep the argument for existing callers.
    def require(condition,message):
        if not condition:raise RuntimeError('session receipt: '+message)
    def bounded(path,limit):
        require(not path.is_symlink() and path.is_file() and 0<path.stat().st_size<=limit,'missing or oversized input')
        data=path.read_bytes();require(len(data)<=limit,'input grew beyond bound');return data
    def digest(data):return hashlib.sha256(data).hexdigest()
    def integer(n):return type(n) is int and n>=0
    def hex_digest(s):return isinstance(s,str) and len(s)==64 and all(c in '0123456789abcdef' for c in s)
    path=Path(str(report_path)+'.session.json')
    if not path.exists() and not path.is_symlink():
        require(returncode!=0,'successful client omitted its receipt');return None
    data=bounded(path,4*1024**2);receipt=json.loads(data);require(isinstance(receipt,dict),'invalid object')
    ready_bytes=bounded(ready_path,16*1024);ready=json.loads(ready_bytes)
    require(isinstance(ready,dict) and receipt.get('schema_version')==1 and receipt.get('transport')=='private-unix-socket','wrong schema/transport')
    require(integer(receipt.get('request_id')) and receipt['request_id']>0 and
        integer(receipt.get('server_pid')) and receipt['server_pid']>0 and receipt['server_pid']==ready.get('pid') and
        hex_digest(receipt.get('server_executable_sha256')) and receipt['server_executable_sha256']==ready.get('executable_sha256') and
        receipt.get('readiness_sha256')==digest(ready_bytes),'server identity differs')
    catalog_bytes=bounded(catalog_path,4*1024**2);catalog=json.loads(catalog_bytes)
    require(isinstance(catalog,dict) and hex_digest(catalog.get('artifact_sha256')),'invalid catalog artifact digest')
    require(receipt.get('report')==str(report_path) and receipt.get('artifact_sha256')==catalog['artifact_sha256'] and
        receipt.get('catalog_sha256')==digest(catalog_bytes),'selected artifact/catalog/report differs')
    if expected_artifact_sha256 is not None:
        require(hex_digest(expected_artifact_sha256) and receipt['artifact_sha256']==expected_artifact_sha256,
            'pre-execution artifact digest differs')
    require(receipt.get('history_bytes_per_worker')==ready.get('history_bytes_per_worker') and
        integer(receipt.get('history_bytes_per_worker')) and receipt['history_bytes_per_worker']<=64*1024**2 and
        type(receipt.get('verify_hits')) is bool and receipt['verify_hits']==ready.get('verify_hits'),'history mode differs')
    require(receipt.get('status') in ['completed','unknown-or-error','sending'],'unknown status')
    if receipt['status']=='completed':
        response=receipt.get('response');require(isinstance(response,dict),'missing response')
        report_bytes=bounded(report_path,4*1024**2);report=json.loads(report_bytes)
        require(isinstance(report,dict) and response.get('kind')=='result' and response.get('poisoned') is False and
            response.get('id')==receipt['request_id'] and response.get('pid')==receipt['server_pid'] and
            response.get('executable_sha256')==receipt['server_executable_sha256'] and
            response.get('report')==str(report_path) and receipt.get('report_sha256')==response.get('report_sha256')==digest(report_bytes),'response/result binding differs')
        require(report.get('request_id')==receipt['request_id'] and report.get('artifact_sha256')==receipt['artifact_sha256'] and
            report.get('catalog_sha256')==receipt['catalog_sha256'] and report.get('mode')=='prepared' and report.get('workers')==2 and
            report.get('poisoned') is False and report.get('status')==response.get('status') and
            report.get('status')==('passed' if returncode==0 else 'failed'),'suite outcome differs')
        if ready.get('indirect_calls') is True:
            options=report.get('jit_options')
            require(isinstance(options,dict) and set(options)=={'persistent_registers','scalar_calls','indirect_calls'} and
                all(type(value) is bool for value in options.values()),'invalid JIT options')
            if expected_jit_options is not None:
                require(options==expected_jit_options,'requested JIT options differ')
        elif expected_jit_options is not None:
            require(expected_jit_options.get('indirect_calls') is False,'server lacks indirect calls')
        from suite_reports import validate_report
        validate_report(report,[entry['name'] for entry in catalog['entries']],'prepared',returncode==0)
        for field in ['user_us','system_us']:
            values=[ready.get('cpu_at_ready',{}).get(field),response.get('cpu_before',{}).get(field),response.get('cpu_after',{}).get(field)]
            require(all(integer(n) for n in values) and values==sorted(values),'invalid process CPU counters')
    else:require(returncode!=0,'successful client has an uncertain outcome')
    # Only the explicit public receipt is retained; never emit ready-file content.
    fields=['schema_version','transport','request_id','server_pid','server_executable_sha256','readiness_sha256',
        'history_bytes_per_worker','verify_hits','cpu_at_ready','artifact_sha256','catalog_sha256','report','status',
        'execution_possible','response','report_sha256','error']
    public={key:receipt[key] for key in fields if key in receipt}
    public.update(receipt_path=str(path),receipt_sha256=digest(data),
        cpu_accounting_scope='server request snapshots; owning benchmark must also charge kernel process totals and startup/teardown')
    return public
