"""Inject a read-only observer into an exact archived integrated exporter."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def replace(path, old, new):
    content = path.read_text()
    if content.count(old) != 1:
        raise RuntimeError('injection anchor differs: ' + old[:100])
    path.write_text(content.replace(old, new))


def inject(source):
    directory = source / 'crates/mir-export/src/lower'
    with (directory / 'scalar_promote.rs').open('a') as output:
        output.write('\n#[path="scalar_boundary_observe.rs"]\npub(super) mod boundary;\n')
    shutil.copy2(HERE / 'observe.rs', directory / 'scalar_boundary_observe.rs')
    shutil.copy2(HERE / 'tests.rs', directory / 'scalar_boundary_tests.rs')
    lower = source / 'crates/mir-export/src/lower.rs'
    replace(lower, '    trace_function: Option<usize>,',
        '    trace_function: Option<usize>,\n    scalar_boundaries: scalar_promote::boundary::Collector,')
    replace(lower, '        trace_function: None,',
        '        trace_function: None,\n        scalar_boundaries: Default::default(),')
    replace(lower, '        scalar_promote::apply(&mut self)?;',
        '''        let boundary = scalar_promote::boundary::capture(
            &self, &arguments, self.exporter.scalar_boundaries.remaining())?;
        self.exporter.scalar_boundaries.push(boundary)?;
        scalar_promote::apply(&mut self)?;''')
    replace(lower, '    Ok(Exported { program, unavailable_calls: exporter.unavailable_calls,',
        '''    scalar_promote::boundary::report(exporter.scalar_boundaries, &program)?;
    Ok(Exported { program, unavailable_calls: exporter.unavailable_calls,''')
    replace(lower, '    scalar_frame::byte_writes::report(exporter.byte_writes, &mut program);',
        '''    scalar_frame::byte_writes::report(exporter.byte_writes, &mut program);
    scalar_promote::boundary::after_relocation(&mut exporter.scalar_boundaries, &program)?;''')
