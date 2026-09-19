"""Source-derived unchanged recipe order, with complete verbose stream slices.

This is qualification accounting, never a substitute implementation of rmake.
The real unchanged recipe must itself return success and enforce its assertions.
"""
import hashlib
import json


def expected_calls():
    rows=[]
    def compiler(capture=False,reuse=False,info=False,fail=False,flags=(),incremental=None,version=None):
        rows.append(dict(kind='compiler',capture=capture,reuse=reuse,info=info,fail=fail,flags=list(flags),
                         incremental=incremental or ('cache-reuse' if reuse else 'cache-on' if capture else 'cache-off'),version=version))
    def run():rows.append(dict(kind='native',fail=False))
    def success(reuse=False):
        compiler();run();compiler(capture=not reuse,reuse=reuse,info=True);run()
    def raw(reuse=False,fail=False,flags=()):
        compiler(fail=fail,flags=['--error-format=json',*flags])
        if not reuse and not fail:run()
        compiler(capture=not reuse,reuse=reuse,fail=fail,flags=['--error-format=json',*flags])
        if not fail:run()
    # main: six ordinary source states, four cfg errors/restorations, corruption.
    for _ in range(6):success()
    for cfg in ['type_error','borrow_error','const_error','panic_error']:
        for capture in [False,True]:compiler(capture=capture,fail=True,flags=['--cfg',cfg,'--error-format=json'])
        success()
    success();success()
    # entry_context_controls: source features and crate/command lint contexts.
    raw()
    for _ in ['async_fn_track_caller','iter_next_chunk']:
        compiler(capture=True,info=True);run();raw();raw()
    for fail,flags in [(False,[]),(True,[]),(False,[]),(False,['-A','unused_variables']),
                       (True,['-D','unused_variables']),(False,['-A','unused_variables'])]:raw(fail=fail,flags=flags)
    # reuse_controls: six source states, uncalled errors and source restoration.
    for _ in range(6):success(True)
    for _ in ['type_error','borrow_error','const_error','panic_error']:
        raw(True,True);compiler(reuse=True,info=True,fail=True);success(True)
    success(True);success(True);raw(True)
    for _ in ['async_fn_track_caller','iter_next_chunk']:
        compiler(reuse=True,info=True);raw(True);raw(True)
    for _ in ['crate','module']:
        for index,fail in enumerate([False,True,False]):
            raw(True,fail)
            if index:compiler(reuse=True,info=True,fail=fail)
    for flag,fail in [('-A',False),('-D',True)]:
        compiler(reuse=True,info=True,fail=fail,flags=[flag,'unused_variables']);raw(True,fail,[flag,'unused_variables'])
    raw(True,False,['-A','unused_variables']);raw(True)
    # Both explicit version values must remain distinct from env_remove.
    for label,version in [('empty',''),('nonempty','fixture-version-override')]:
        for mode,capture,reuse in [('ordinary',False,False),('capture',True,False),('reuse',False,True)]:
            compiler(capture,reuse,True,incremental=f'override-{label}-{mode}-positive',version=version);run()
            compiler(capture,reuse,False,True,['--error-format=json'],f'override-{label}-{mode}-negative',version)
    compiler();compiler(capture=True)
    assert len(rows)==230 and sum(row['kind']=='compiler' for row in rows)==144
    assert sum(row['fail'] for row in rows)==39
    return rows


def command_text(row,*,out,rustc,target,recipe_dyld,e2):
    # Values are all admitted ASCII paths/tokens; JSON and Rust Debug escaping
    # coincide for this bounded grammar. Reject rather than guess a new form.
    quote=lambda value:json.dumps(str(value),ensure_ascii=True)
    if row['kind']=='native':
        env={'DYLD_LIBRARY_PATH':f'{out}:{e2}/lib/rustlib/{target}/lib:{recipe_dyld}','LC_ALL':'C'}
        args=[f'{out}/body_journal_test'];prefix=''
    else:
        env={'DYLD_LIBRARY_PATH':f'{out}:{e2}/lib:{recipe_dyld}'}
        if row['version'] is None:prefix='env -u RUSTC_FORCE_RUSTC_VERSION '
        else:prefix='';env['RUSTC_FORCE_RUSTC_VERSION']=row['version']
        args=[rustc,'-L',out,'input.rs','--crate-name','body_journal_test','-o','body_journal_test',
              '-Cmetadata=body_journal_test','-Cincremental='+row['incremental'],
              '-Zhir-body-cache-capture='+str(row['capture']).lower(),'-Cdebuginfo=2','--edition=2024']
        if row['reuse']:args.append('-Zhir-body-cache-reuse=true')
        if row['info']:args.append('-Zincremental-info')
        args.extend(row['flags']);args.append('--target='+target)
    values=[*map(str,args),*env.keys(),*env.values()]
    assert all(value.isascii() and not any(ord(c)<32 for c in value) for value in values)
    return prefix+''.join(key+'='+quote(value)+' ' for key,value in sorted(env.items()))+' '.join(map(quote,args))


def audit(raw,**context):
    expected=expected_calls();headers=[]
    for row in expected:
        command=command_text(row,**context)
        prefix=('running: '+command+'\n' if row['kind']=='native' else '')+command+'\n'
        headers.append(prefix.encode()+b'output status: `exit status: '+(b'1' if row['fail'] else b'0')+b'`\n=== STDOUT ===\n')
    position=0;records=[]
    for index,(row,header) in enumerate(zip(expected,headers,strict=True)):
        start=position;assert raw.startswith(header,position),('nested command/header differs',index,position)
        body_start=position+len(header)
        if index+1<len(headers):
            stop=raw.find(headers[index+1],body_start);assert stop>=0,('missing next command',index)
        else:stop=len(raw)
        body=raw[body_start:stop];assert body.endswith(b'\n\n\n'),('truncated verbose block',index)
        stdout,stderr=body[:-3].split(b'\n\n\n=== STDERR ===\n',1)
        records.append(dict(index=index,expected=row,start=start,end=stop,
                            raw_sha256=hashlib.sha256(raw[start:stop]).hexdigest(),
                            stdout_bytes=len(stdout),stdout_sha256=hashlib.sha256(stdout).hexdigest(),
                            stderr_bytes=len(stderr),stderr_sha256=hashlib.sha256(stderr).hexdigest()))
        position=stop
    assert position==len(raw)
    return dict(status='passed',nested_commands=230,compiler_commands=144,native_runs=86,
                expected_compiler_failures=39,raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),records=records,
                limitation='Raw command/status/order audit and unchanged recipe assertions; nested PID/start times are not supplied by run-make-support and are not claimed.')
