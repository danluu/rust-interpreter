//! Explicit isolated selected-entry execution, not a replacement for libtest.
use rust_interp_bytecode::{EntryCatalog, Limits, Op, PreparedJit, Program, PARTIAL_VALIDATION};
use serde_json::{Value, json};
use std::{collections::HashSet, io::Write, time::Instant, sync::atomic::{AtomicUsize, Ordering}};

#[derive(Clone, Copy)]
pub enum Mode { Fresh, Prepared }

fn selected_entries(program: &Program) -> Result<Vec<(&str, usize)>, String> {
    if program.version & PARTIAL_VALIDATION != 0 {
        return Err("isolated test batches require fully checked bytecode".into());
    }
    let root = program.functions.get(program.entry).ok_or("missing selected batch root")?;
    let names = root.name.strip_prefix("selected test batch: ").ok_or("expected an exporter-selected test batch")?;
    let names: Vec<_> = names.split(", ").collect();
    if names.len() < 2 || names.len() > 10_000 || names.iter().any(|n| n.is_empty())
        || root.frame_size != 0 || root.registers != 1 || !root.args.is_empty() || root.result.size != 0
        || root.code.len() != 2 * names.len() + 2
        || !matches!(root.code.first(), Some(Op::Local { dst: 0, offset: 0 }))
        || !matches!(root.code.last(), Some(Op::Return))
    {
        return Err("selected batch descriptor differs from exporter format".into());
    }
    let mut entries = vec![];
    let mut seen_ids = HashSet::new();
    let mut seen_names = HashSet::new();
    for (name, pair) in names.into_iter().zip(root.code[1..root.code.len() - 1].chunks_exact(2)) {
        let [Op::ResetThreadLocals, Op::Call { function, args, destination: 0 }] = pair else {
            return Err("selected batch contains operations outside its test list".into());
        };
        let entry = program.functions.get(*function).ok_or("invalid selected test entry")?;
        if !args.is_empty() || !entry.args.is_empty() || entry.result.size != 0 || *function == program.entry
            || !seen_ids.insert(*function) || !seen_names.insert(name)
        {
            return Err("selected batch requires distinct zero-argument/unit-result entries".into());
        }
        entries.push((name, *function));
    }
    Ok(entries)
}

fn worker(program: &Program, mode: Mode, limits: &Limits, entries: &[(&str, usize)],
          next: &AtomicUsize, worker: usize) -> Result<(u128, Vec<(usize, Value)>), String> {
    // The JIT is born, used and dropped on this worker. Only immutable Program
    // data and completed JSON outcomes cross thread boundaries.
    let mut shared = match mode { Mode::Fresh => None, Mode::Prepared => Some(PreparedJit::new(program, limits)?) };
    let mut preparation_nanos = shared.as_ref().map_or(0, PreparedJit::preparation_nanos);
    let mut tests = vec![];
    loop {
        let index = next.fetch_add(1, Ordering::Relaxed);
        let Some(&(name, entry)) = entries.get(index) else { break; };
        let test_started = Instant::now();
        let result = if let Some(jit) = &mut shared {
            jit.execute_entry(entry, &[], limits.clone())
        } else {
            let mut jit = PreparedJit::new(program, limits)?;
            preparation_nanos += jit.preparation_nanos();
            jit.execute_entry(entry, &[], limits.clone())
        };
        let seconds = test_started.elapsed().as_secs_f64();
        let mut outcome = match result {
            Ok(run) => json!({"name":name,"function":entry,"status":"passed","seconds":seconds,
                "instructions":run.instructions,"peak_guest_memory":run.peak_memory,
                "jit_compile_ns":run.jit_compile_nanos,"jit_bytes":run.jit_bytes,
                "jit_compiled_functions":run.jit_compiled_functions,"jit_declined_functions":run.jit_declined_functions,
                "jit_instructions":run.jit_instructions,"jit_entries":run.jit_entries}),
            Err(error) => {
                json!({"name":name,"function":entry,"status":"failed","seconds":seconds,"error":error})
            }
        };
        outcome["worker"] = json!(worker);
        tests.push((index, outcome));
    }
    Ok((preparation_nanos, tests))
}

pub fn run(program: &Program, mode: Mode, limits: &Limits, path: &str,
           catalog: Option<&EntryCatalog>, bytes: &[u8], requested_workers: usize) -> Result<(), Box<dyn std::error::Error>> {
    let started = Instant::now();
    if !(1..=64).contains(&requested_workers) { return Err("suite workers must be in 1..64".into()); }
    let entries = match catalog {
        Some(catalog) => catalog.validated_entries(program, bytes)?,
        None => selected_entries(program)?,
    };
    if entries.is_empty() { return Err("isolated batch has no entries".into()); }
    // Reserve the report before any guest code runs. Never replace a previous
    // result merely because the same command was invoked a second time.
    let file = std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    let workers = requested_workers.min(entries.len());
    let next = AtomicUsize::new(0);
    let results = if workers == 1 {
        vec![worker(program, mode, limits, &entries, &next, 0)?]
    } else {
        std::thread::scope(|scope| -> Result<_, String> {
            let mut handles = vec![];
            for id in 0..workers {
                let entries = &entries;
                let next = &next;
                handles.push(std::thread::Builder::new().name(format!("rust-interp-suite-{id}"))
                    .spawn_scoped(scope, move || worker(program, mode, limits, entries, next, id))
                    .map_err(|error| format!("cannot start suite worker: {error}"))?);
            }
            // Scope completion also joins all remaining workers if a startup
            // or worker failure returns early. No guest or JIT outlives run.
            handles.into_iter().map(|handle| handle.join()
                .map_err(|_| "suite worker panicked".to_owned())?).collect()
        })?
    };
    let mut preparation_nanos = 0;
    let mut ordered = vec![];
    for (preparation, tests) in results { preparation_nanos += preparation; ordered.extend(tests); }
    ordered.sort_unstable_by_key(|(index, _)| *index);
    let tests: Vec<Value> = ordered.into_iter().map(|(_, outcome)| outcome).collect();
    let failures = tests.iter().filter(|test| test["status"] == "failed").count();
    let report = json!({"schema_version":1,"status":if failures == 0 {"passed"} else {"failed"},
        "mode":match mode {Mode::Fresh=>"fresh",Mode::Prepared=>"prepared"},
        "requested_workers":requested_workers,"workers":workers,
        "entry_source":if catalog.is_some() {"artifact-bound catalog"} else {"legacy batch descriptor"},
        "isolation":"new guest memory, statics, registers, frames, heap and TLS for each entry",
        "scope":"explicit selected unit-result entries; no libtest ignore, should-panic, unwind or thread semantics",
        "runtime_limits":{"instructions":limits.instructions,"allocations":limits.allocations,
            "memory_bytes":limits.memory,"frames":limits.frames},
        "jit_code_limit_bytes":limits.jit_code_bytes,
        "limit_scope":"runtime limits apply to each isolated test; the code limit applies to each JIT owner, with one owner per prepared worker",
        "seconds_before_report_write":started.elapsed().as_secs_f64(),
        "preparation_ns":preparation_nanos,"preparation_scope":"sum of constructor durations, which can overlap across workers; included in per-test seconds for fresh mode; each prepared worker constructs before its tests",
        "passed":tests.len()-failures,"failed":failures,"tests":tests});
    let mut output = std::io::BufWriter::new(file);
    serde_json::to_writer_pretty(&mut output, &report)?;
    output.write_all(b"\n")?;
    output.flush()?;
    if failures != 0 { return Err(format!("{failures} isolated tests failed; see suite report").into()); }
    Ok(())
}
