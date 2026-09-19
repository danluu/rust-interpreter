"""Full original18 frontend recipe with explicit current provider/work routes."""
from pathlib import Path
from types import SimpleNamespace

ERRORS = [('type', 'E0308', b'\nfn uncalled_type_error() -> u32 { "wrong" }\n'),
    ('borrow', 'E0515', b"\nfn uncalled_borrow_error() -> &'static u32 { let value = 3; &value }\n")]

def context(c, work, environment):
    """Return functions bound to the current immutable source/provider roles."""
    R, B2, D, TARGET = c.RUNTIME, c.B3, c.D2/'bin/rustc', c.TARGET
    WORK, FIXTURE, OUTPUT = work, work/'fixture', work/'outputs'
    require = c.require
    def ordinary_files(root):
        return [Path(root)/name for name in sorted(c.tree(root))]
    m = SimpleNamespace(ordinary_files=ordinary_files, file_record=c.file)
    def app_environment(sdk):
        return environment | {'TMPDIR': str(WORK/'tmp')+'/'}

    def application_environment(row, sdk):
        env = app_environment(sdk)
        env['RUST_INTERP_COMPILER_ARGV_RECORD_DIR'] = str(OUTPUT / (row['name'] + '-argv'))
        artifact = OUTPUT / (row['name'] + ('.json' if row['profile'] == 'list' else '.rbc'))
        if row['profile'] != 'native':
            env.update(RUST_INTERP_EXPORT_CRATE='role_test' if row['profile'] in ('test', 'list') else 'role_basic',
                       RUST_INTERP_OUTPUT=str(artifact))
            if row['profile'] in ('test', 'list'):
                env['RUST_INTERP_EXPORT_TEST'] = '1'
            if row['profile'] == 'list':
                env['RUST_INTERP_LIST_TESTS'] = '1'
            else:
                env['RUST_INTERP_ENTRY'] = 'selected' if row['profile'] == 'test' else 'changing_value'
        return env

    def application_commands(sdk):
        x, w = [str(TARGET/'release'/name) for name in ['rust-interp-mir-export','rust-interp-rustc-wrapper']]
        def args(test=False, sysroot=R):
            result = ['--crate-name', 'role_test' if test else 'role_basic', '--edition=2024',
                '--crate-type', 'lib' if test else 'bin', '-Copt-level=0', '-Cdebuginfo=0',
                '-Clinker='+sdk['clang'], '--error-format=json', '--emit=metadata']
            if test: result += ['--test','-Zalways-encode-mir=yes']
            if sysroot is not None: result += ['--sysroot',str(sysroot)]
            return result + [str(FIXTURE/('test_export.rs' if test else 'basic.rs'))]
        def row(name, executable, *, test=False, sysroot=R, profile='native', state='original', error=None, wrapper=None):
            argv = [executable] + ([str(wrapper)] if wrapper is not None else [])
            return dict(name=name, argv=argv+args(test,sysroot)+['-o',str(OUTPUT/(name+'.rmeta'))],
                profile=profile, state=state, error=error)
        rows = [dict(name='exporter-capabilities',argv=[x,'--rust-interp-capabilities'],profile='native',state='original',error=None),
            dict(name='wrapper-roles',argv=[w,'--rust-interp-compiler-roles'],profile='native',state='original',error=None),
            row('basic-native',str(R/'bin/rustc')), row('basic-export-explicit-R',x,profile='basic'),
            row('basic-export-default-R',x,profile='basic',sysroot=None),
            row('wrapper-export-R',w,profile='basic',wrapper=R/'bin/rustc'),
            row('wrapper-reject-D',w,profile='basic',wrapper=D,error='wrong-role'),
            row('test-native',str(R/'bin/rustc'),test=True),row('test-export',x,test=True,profile='test'),
            row('test-discovery',x,test=True,profile='list')]
        for state,code,_ in ERRORS:
            rows += [row('uncalled-'+state+'-native',str(R/'bin/rustc'),state=state,error=code),
                row('uncalled-'+state+'-export',x,profile='basic',state=state,error=code)]
        rows += [row('restored-native',str(R/'bin/rustc')),row('restored-export',x,profile='basic'),
            row('reject-build-sysroot-native',str(R/'bin/rustc'),sysroot=B2,error='metadata'),
            row('reject-build-sysroot-export',x,sysroot=B2,profile='basic',error='metadata')]
        require(len(rows)==18, 'fixed application command count differs')
        return rows

    def argv_record(row,root):
            paths=m.ordinary_files(root)
            if row['profile']=='native' or row['error']=='wrong-role':
                require(not paths,'unexpected final compiler argv record')
                return None
            require(len(paths)==1 and paths[0].name.startswith('exported-'),'one actual exported compiler argv required')
            data=paths[0].read_bytes();fields=data.split(b'\0')
            require(fields[-1]==b'' and fields[:4]==[b'rust-interp-compiler-argv-v1',b'exported',str(R).encode(),str(FIXTURE).encode()],
                'compiler argv evidence header differs')
            args=[x.decode() for x in fields[4:-1]]
            expected_first=str(R/'bin/rustc') if row['name']=='wrapper-export-R' else str(TARGET/'release/rust-interp-mir-export')
            require(args[0]==expected_first,'actual final compiler route differs')
            roots=[]
            for i,arg in enumerate(args):
                if arg=='--sysroot':require(i+1<len(args),'missing final sysroot');roots.append(args[i+1])
                elif arg.startswith('--sysroot='):roots.append(arg.split('=',1)[1])
            require(roots==[str(B2 if row['error']=='metadata' else R)],'final compiler sysroot differs')
            require(str(FIXTURE/('test_export.rs' if row['name'].startswith('test-') else 'basic.rs')) in args,
                'actual compiler source differs')
            return m.file_record(paths[0])

    return SimpleNamespace(application_environment=application_environment,
        application_commands=application_commands, argv_record=argv_record, errors=ERRORS)
