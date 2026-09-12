"""Install typed scalar promotion and versioned publication in qualified source."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
def replace(s,old,new):
    if s.count(old)!=1:raise RuntimeError('compiler injection anchor differs: '+old[:100])
    return s.replace(old,new)
def inject(source):
    root=source/'crates/mir-export/src';lower=root/'lower'
    p=root.parent/'Cargo.toml';s=p.read_text()
    s=replace(s,'serde_json = "1"','serde_json = "1"\nserde = { version = "1", features = ["derive"] }');p.write_text(s)
    p=source/'Cargo.lock';s=p.read_text()
    s=replace(s,' "rust-interp-bytecode",\n "serde_json",',' "rust-interp-bytecode",\n "serde",\n "serde_json",');p.write_text(s)
    for local,name in [('capture.rs','scalar_values.rs'),('transform.rs','scalar_value_transform.rs'),('tests.rs','scalar_value_transform_tests.rs')]:
        (lower/name).write_text((HERE/local).read_text())
    p=root/'lower.rs';s=p.read_text()
    s=replace(s,'mod scalar_promote;','mod scalar_promote;\npub(crate) mod scalar_values;')
    s=replace(s,'    pub program: Program,','    pub artifact: rust_interp_bytecode::scalar_abi::Artifact,')
    s=replace(s,'    if allocation_trace && demand {', '''    let scalar_values_enabled=scalar_values::enabled();
    if scalar_values_enabled && demand {return Err("scalar values require strict frontend checking".into());}
    if allocation_trace && demand {''')
    s=replace(s,'        byte_writes: vec![],','        byte_writes: vec![],\n        scalar_values: scalar_values::Collector::new(scalar_values_enabled),')
    s=replace(s,'    byte_writes: Vec<scalar_frame::byte_writes::Observation>,',
        '    byte_writes: Vec<scalar_frame::byte_writes::Observation>,\n    scalar_values: scalar_values::Collector,')
    s=replace(s,'        let observed = scalar_frame::byte_writes::capture(&mut self);', '''        if self.exporter.scalar_values.enabled {
            let binding=scalar_values::capture(&self,&arguments,self.exporter.scalar_values.remaining())?;
            self.exporter.scalar_values.push(binding)?;
        }
        let observed = scalar_frame::byte_writes::capture(&mut self);''')
    s=replace(s,'    scalar_frame::byte_writes::report(exporter.byte_writes, &mut program);',
        '    scalar_frame::byte_writes::report(exporter.byte_writes, &mut program, &mut exporter.scalar_values)?;')
    s=replace(s,'    Ok(Exported { program, unavailable_calls: exporter.unavailable_calls,',
        '    let artifact=exporter.scalar_values.finish(program)?;\n    Ok(Exported { artifact, unavailable_calls: exporter.unavailable_calls,');p.write_text(s)
    p=lower/'byte_writes.rs';s=p.read_text()
    s=replace(s,'''pub(crate) fn report(observations: Vec<Observation>, program: &mut Program) {
    relocation::transform(observations,program);''', '''pub(crate) fn report(observations: Vec<Observation>, program: &mut Program,
    values:&mut crate::lower::scalar_values::Collector)->Result<()> {
    relocation::transform(observations,program,values)''');p.write_text(s)
    p=lower/'aggregate_relocation.rs';s=p.read_text()
    s=replace(s,'pub(super) fn transform(observations: Vec<Observation>, program: &mut Program) {', '''pub(super) fn transform(observations: Vec<Observation>, program: &mut Program,
    values:&mut crate::lower::scalar_values::Collector)->Result<()> {''')
    s=replace(s,'        apply(&mut program.functions[o.id],r);','        values.relocate(o.id,&o.slots,&slots)?;\n        apply(&mut program.functions[o.id],r);')
    s=replace(s,'        "initialization_unchanged":true}));','        "initialization_unchanged":true}));\n    Ok(())');p.write_text(s)
    p=root/'main.rs';s=p.read_text()
    s=replace(s,'''            let program = &exported.program;
            rust_interp_bytecode::validate(&program)?;
            let bytes = bincode::serialize(&program).map_err(|e| e.to_string())?;''', '''            let program = &exported.artifact.program;
            let bytes = exported.artifact.encode()?;''')
    s=replace(s,'"RUST_INTERP_ALLOCATION_TRACE"] {','"RUST_INTERP_ALLOCATION_TRACE", "RUST_INTERP_SCALAR_VALUES"] {')
    s=replace(s,'"export_options":["inline-leaves","trap-unsupported-calls","run-try-callbacks","allocation-trace"]',
        '"artifact_versions":[5,6],"export_options":["inline-leaves","trap-unsupported-calls","run-try-callbacks","allocation-trace","scalar-values"]');p.write_text(s)
    p=root/'audit.rs';s=p.read_text()
    s=replace(s,'                rust_interp_bytecode::validate(&exported.program)?;','                exported.artifact.validate()?;')
    s=replace(s,'                let program = &exported.program;','                let program = &exported.artifact.program;')
    s=replace(s,'record["artifact"] = pack.store(index, &program)?;','record["artifact"] = pack.store(index, &exported.artifact)?;')
    s=replace(s,'        "bytecode_version":rust_interp_bytecode::VERSION,',
        '        "bytecode_version":if super::lower::scalar_values::enabled(){6}else{5},\n        "scalar_values":super::lower::scalar_values::enabled(),');p.write_text(s)
    p=root/'audit/pack.rs';s=p.read_text().replace('use rust_interp_bytecode::Program;','use rust_interp_bytecode::scalar_abi::Artifact;')
    s=replace(s,'pub fn store(&mut self, index: usize, program: &Program)', 'pub fn store(&mut self, index: usize, artifact: &Artifact)')
    s=replace(s,'        let expected = bincode::serialized_size(program).map_err(|e| e.to_string())?;', '''        let expected = if artifact.program.version==6 {bincode::serialized_size(artifact)}
            else {bincode::serialized_size(&artifact.program)}.map_err(|e|e.to_string())?;''')
    s=replace(s,'        let bytes = bincode::serialize(program).map_err(|e| e.to_string())?;', '        let bytes = artifact.encode()?;');p.write_text(s)
    # The experiment launcher lives outside the frozen root launcher. Its
    # isolated source copy uses the usual source-root discovery rule.
    s=(HERE/'launcher.py').read_text()
    s=replace(s,'ROOT=Path(__file__).resolve().parents[3]','ROOT=Path(__file__).resolve().parents[1]')
    (source/'scripts/interpreter.py').write_text(s)
