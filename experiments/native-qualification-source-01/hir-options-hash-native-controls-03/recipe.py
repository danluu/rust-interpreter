"""The unchanged native 18-command history, plus two explicit wrong-B3 calls.

Source-only: desired_commands is not a launch plan. Actual compiler, assembly,
provider and loader observations must be supplied by the admitted controller.
No hash-driver process is part of this recipe.
"""
from pathlib import Path

HOST = 'aarch64-apple-darwin'
ORIGINAL = b'fn anchor() -> u32 { 42 }\nfn main() { println!("{}", anchor()); }\n'
ERROR = ORIGINAL + b'fn uncalled() -> u8 { "wrong" }\n'
WRONG = b'fn main() {}\n'


def paths(namespace):
    n = Path(namespace)
    s = n / 'source'
    root = n / 'native-controls-03'
    return dict(source=s, build=s/'build'/HOST/'stage0', runtime=s/'build'/HOST/'stage1',
                beta=n/'beta-sysroot', root=root, stock=root/'smoke-rustc', stock_source=root/'stock-main.rs',
                fixture=root/'fixture/main.rs', program=root/'fixture/program',
                wrong_source=root/'wrong-role/main.rs', wrong_output=root/'wrong-role/program')


def desired_commands(plan):
    p = paths(plan['namespace'])
    env = plan['environment']
    clang = plan['clang']
    rows = []
    def add(argv, *, role='native-history', environment=env, expected=(0,)):
        rows.append(dict(argv=list(map(str, argv)), cwd=str(p['source']), environment=environment,
                         expected=list(expected), role=role))
    for root in [p['build'], p['runtime']]:
        add([root/'bin/rustc', '-vV'])
        add([root/'bin/rustc', '--print', 'sysroot'])
    pair = plan['ordered_driver_destinations']
    assert len(pair) == 2 and pair[0].endswith('.dylib')
    assert pair[1] == str(Path(pair[0]).with_suffix('.rmeta'))
    add([p['build']/'bin/rustc', '--sysroot='+str(p['beta']), '--edition=2024',
         '--crate-name', 'rustc_main', '--print=link-args', p['stock_source'],
         '--extern', 'rustc_driver='+str(p['beta']/pair[0]),
         '--extern', 'rustc_driver='+str(p['beta']/pair[1]),
         '-Lnative='+str(p['runtime']/'lib'), '-Clinker='+clang,
         '-C', 'link-arg=-Wl,-rpath,'+str(p['runtime']/'lib'), '-o', p['stock']],
        environment=env | {'RUSTC_BOOTSTRAP': '1'})
    add([plan['otool'], '-L', p['stock']])
    add([p['stock'], '-vV'], environment=env | {'DYLD_PRINT_LIBRARIES': '1'})
    common = [p['fixture'], '--sysroot='+str(p['runtime']), '--edition=2024',
              '--crate-name', 'embedded_driver_smoke', '-Cmetadata=embedded_driver_smoke',
              '-Cdebuginfo=2', '-Clinker='+clang, '-Zhir-body-cache-capture=false', '-o', p['program']]
    def compile(reuse, info=False, fails=False, raw=False):
        argv = [p['stock'] if reuse else p['runtime']/'bin/rustc', *common,
                '-Cincremental='+str(p['root']/('incremental-reuse' if reuse else 'incremental-ordinary'))]
        if reuse:
            argv += ['-Zhir-body-cache-reuse=true']
        if info:
            argv += ['-Zincremental-info']
        if raw:
            argv += ['--error-format=json']
        add(argv, expected=(1,) if fails else (0,))
    def execute():
        add([p['program']])
    compile(False); execute()
    compile(True, info=True); execute()
    compile(True, info=True); execute()
    compile(False, fails=True, raw=True)
    compile(True, fails=True, raw=True)
    compile(True, info=True, fails=True)
    compile(True, info=True); execute()
    assert len(rows) == 18
    for compiler in [p['runtime']/'bin/rustc', p['stock']]:
        add([compiler, p['wrong_source'], '--sysroot='+str(p['beta']), '--edition=2024',
             '--crate-name', 'wrong_beta_application_role', '--error-format=json', '-o', p['wrong_output']],
            role='wrong-B3-application-role', expected=(1,))
    assert len(rows) == 20
    return rows


def execute(stage):
    """Execute only through the controller's exact allowlist/guarded command API.

    stage keeps the canonical descriptor, validates every prior qualification,
    binds generated executors, snapshots executed programs and restores source.
    All mutations are in the fresh native-controls root, never compiler inputs.
    """
    p = stage.paths
    stage.fresh_root()
    for index, expected in enumerate([stage.plan['build_version'], str(p['build'])+'\n',
                                      stage.plan['runtime_version'], str(p['runtime'])+'\n']):
        out, err, _ = stage.command(index)
        stage.require(not err and out.decode() == expected, 'native compiler identity differs')
    out, err, _ = stage.command(4)
    stage.require(not err, 'stock build emitted diagnostics')
    stage.bind_stock(out)
    out, err, _ = stage.command(5)
    stage.require(not err, 'stock otool diagnostics')
    stage.static_stock(out)
    out, err, child = stage.command(6)
    stage.require(out.decode() == stage.plan['runtime_version'], 'stock compiler is not E2')
    stage.loaded_stock(err, child)
    p['fixture'].parent.mkdir()
    p['wrong_source'].parent.mkdir()
    p['wrong_source'].write_bytes(WRONG)
    try:
        stage.write_fixture(ORIGINAL, 'original')
        stage.compile(7, ORIGINAL); stage.output(8)
        stage.hit(stage.compile(9, ORIGINAL), cold=True); stage.output(10)
        stage.hit(stage.compile(11, ORIGINAL)); stage.output(12)
        stage.write_fixture(ERROR, 'error')
        retained = stage.file(p['program'])
        ordinary = stage.compile(13, ERROR)
        candidate = stage.compile(14, ERROR)
        stage.error_pair(ordinary, candidate, 'E0308')
        stage.hit(stage.compile(15, ERROR))
        stage.require(stage.file(p['program']) == retained, 'failed typecheck changed prior executable')
        stage.write_fixture(ORIGINAL, 'restored')
        stage.hit(stage.compile(16, ORIGINAL)); stage.output(17)
        ordinary = stage.wrong_role(18)
        candidate = stage.wrong_role(19)
        stage.wrong_pair(ordinary, candidate)
    finally:
        stage.write_fixture(ORIGINAL, 'restored')
    stage.require(len(stage.record['commands']) == 20, 'complete native history required')
    stage.finish()
