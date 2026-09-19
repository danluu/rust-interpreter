//! Shared argument grammar and checking defaults for native host codegen policies.
//! No dependency-name or application-source classification belongs here.

#[derive(Default)]
struct Invocation<'a> {
    crate_types: Vec<&'a str>,
    emits: Vec<&'a str>,
    inputs: Vec<&'a str>,
    codegen: Vec<&'a str>,
    target: bool,
    probe: bool,
    test: bool,
    unsupported: bool,
}

/// Return extra arguments only for a definite linked host proc-macro unit.
/// Unsupported explicit policies are errors, never silently overridden.
pub fn additions(args: &[String], selected: bool) -> Result<Vec<String>, String> {
    additions_for(args, selected, HostKind::ProcMacro, 1)
}

pub fn library_additions(args: &[String], selected: bool) -> Result<Vec<String>, String> {
    additions_for(args, selected, HostKind::Library, 1)
}

/// Fixed combined O3 policy. Both passes use the same original Cargo argv;
/// their disjoint role predicates prevent duplicate additions. The legacy
/// macro grammar still rejects library-only unstable flags on proc macros.
pub fn combined_additions(args: &[String], selected: bool) -> Result<Vec<String>, String> {
    let macro_args = additions_for(args, selected, HostKind::ProcMacro, 3)?;
    if !macro_args.is_empty() { return Ok(macro_args); }
    additions_for(args, selected, HostKind::Library, 3)
}

#[derive(Clone, Copy)]
enum HostKind { ProcMacro, Library }

impl HostKind {
    fn accepts(self, kind: &str) -> bool {
        match self {
            Self::ProcMacro => kind == "proc-macro",
            Self::Library => matches!(kind, "lib" | "rlib"),
        }
    }

    fn label(self) -> &'static str {
        match self { Self::ProcMacro => "proc-macro", Self::Library => "library" }
    }

    fn preserves_metadata_option(self, option: &str) -> bool {
        // Cargo can emit separate metadata alongside an ordinary native rlib.
        // Keep its exact embedding choice; this does not select optimization
        // or alter checking. The existing proc-macro policy stays unchanged.
        if !matches!(self, Self::Library) { return false; }
        let (name, value) = option.split_once('=').map_or((option, None), |(n, v)| (n, Some(v)));
        name.replace('_', "-") == "embed-metadata" && boolean(value).is_some()
    }
}

fn additions_for(args: &[String], selected: bool, kind: HostKind, opt_level: u8) -> Result<Vec<String>, String> {
    let fail = |reason: &str| format!("host {} optimization: {reason}", kind.label());
    if args.iter().skip(1).any(|arg| arg.starts_with('@')) {
        return Err(fail("response files are unsupported"));
    }
    let mut invocation = Invocation::default();
    let mut index = 1;
    while index < args.len() {
        let arg = args[index].as_str();
        index += 1;
        if arg == "--" {
            // Appending policy flags after an option terminator would turn
            // them into extra source operands instead of compiler options.
            invocation.unsupported = true;
            invocation.inputs.extend(args[index..].iter().map(String::as_str));
            break;
        }
        if matches!(arg, "-vV" | "-V" | "--version" | "-h" | "--help") {
            invocation.probe = true;
            continue;
        }
        if arg == "--test" {
            invocation.test = true;
            continue;
        }
        if matches!(arg, "-g" | "--verbose" | "-v") {
            continue;
        }
        if let Some(long) = arg.strip_prefix("--") {
            let (name, joined) = long.split_once('=').map_or((long, None), |(n, v)| (n, Some(v)));
            if matches!(name, "crate-type" | "emit" | "target" | "print" | "crate-name" |
                "edition" | "cfg" | "check-cfg" | "extern" | "out-dir" | "sysroot" |
                "error-format" | "json" | "color" | "diagnostic-width" | "remap-path-prefix" |
                "remap-path-scope" | "cap-lints" | "allow" | "warn" | "force-warn" |
                "deny" | "forbid" | "codegen" | "explain") {
                let value = if let Some(value) = joined { Some(value) } else {
                    let value = args.get(index).map(String::as_str);
                    index += usize::from(value.is_some());
                    value
                };
                let Some(value) = value else {
                    invocation.unsupported = true;
                    continue;
                };
                if value.is_empty() { invocation.unsupported = true; }
                match name {
                    "crate-type" => invocation.crate_types.push(value),
                    "emit" => invocation.emits.push(value),
                    "target" => invocation.target = true,
                    "print" | "explain" => invocation.probe = true,
                    "codegen" => invocation.codegen.push(value),
                    "sysroot" => invocation.unsupported = true,
                    _ => {}
                }
            } else {
                invocation.unsupported = true;
            }
            continue;
        }
        if arg.starts_with('-') && arg != "-" {
            let mut chars = arg.chars();
            chars.next();
            let option = chars.next().unwrap();
            if matches!(option, 'C' | 'Z' | 'L' | 'l' | 'o' | 'A' | 'W' | 'D' | 'F') {
                let tail = chars.as_str();
                let value = if tail.is_empty() {
                    let value = args.get(index).map(String::as_str);
                    index += usize::from(value.is_some());
                    value
                } else { Some(tail) };
                match (option, value) {
                    ('C', Some(value)) => invocation.codegen.push(value),
                    ('Z', Some(value)) if kind.preserves_metadata_option(value) => {}
                    ('Z', _) | (_, None) => invocation.unsupported = true,
                    _ => {}
                }
            } else {
                // Includes -O and combined short flags: do not hide an override.
                invocation.unsupported = true;
            }
            continue;
        }
        invocation.inputs.push(arg);
    }
    if selected || invocation.target || invocation.probe || invocation.test {
        return Ok(vec![]);
    }
    if !invocation.crate_types.iter().any(|types| types.split(',').any(|value| kind.accepts(value))) {
        return Ok(vec![]);
    }
    if !invocation.emits.iter().any(|emits| emits.split(',').any(|emit| emit.split('=').next() == Some("link"))) {
        return Ok(vec![]);
    }
    if invocation.unsupported || invocation.crate_types.len() != 1 || !kind.accepts(invocation.crate_types[0]) ||
        invocation.emits.len() != 1 || invocation.inputs.len() != 1 || invocation.inputs[0] == "-" {
        return Err(fail(&format!("requires an unambiguous ordinary Cargo host {} invocation", kind.label())));
    }
    if invocation.emits[0].split(',').any(|emit| !matches!(emit.split('=').next(),
        Some("dep-info" | "metadata" | "link"))) {
        return Err(fail("additional compiler output kinds are unsupported"));
    }
    let mut debug_assertions = None;
    let mut overflow_checks = None;
    for value in invocation.codegen {
        let (name, value) = value.split_once('=').map_or((value, None), |(n, v)| (n, Some(v)));
        let name = name.replace('_', "-");
        match name.as_str() {
            "debug-assertions" => debug_assertions = Some(boolean(value).ok_or_else(|| fail("invalid debug-assertions value"))?),
            "overflow-checks" => overflow_checks = Some(boolean(value).ok_or_else(|| fail("invalid overflow-checks value"))?),
            // Preserve these inputs exactly; none changes the codegen policy
            // or the effective debug/overflow defaults derived below.
            "metadata" | "extra-filename" | "incremental" | "debuginfo" |
            "split-debuginfo" | "embed-bitcode" | "prefer-dynamic" | "codegen-units" |
            "panic" | "target-cpu" | "target-feature" | "relocation-model" |
            "code-model" | "force-frame-pointers" | "force-unwind-tables" |
            "linker" | "link-arg" | "link-args" | "rpath" | "strip" |
            "symbol-mangling-version" | "no-redzone" | "link-dead-code" => {}
            _ => return Err(fail(&format!("explicit codegen option {name} is unsupported"))),
        }
    }
    let mut result = vec![format!("-Copt-level={opt_level}"), "-Zmir-opt-level=1".into(), "-Clto=off".into()];
    if debug_assertions.is_none() { result.push("-Cdebug-assertions=yes".into()); }
    if overflow_checks.is_none() {
        result.push(format!("-Coverflow-checks={}", if debug_assertions.unwrap_or(true) { "yes" } else { "no" }));
    }
    Ok(result)
}

fn boolean(value: Option<&str>) -> Option<bool> {
    match value {
        None | Some("y" | "yes" | "on" | "true") => Some(true),
        Some("n" | "no" | "off" | "false") => Some(false),
        _ => None,
    }
}
