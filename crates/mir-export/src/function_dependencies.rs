//! Observe compiler query dependencies; always recompute and verify the output.
use rustc_middle::mono::MonoItem;
use rustc_middle::ty::{Instance, TyCtxt};
use serde_json::{Value, json};
use std::time::Instant;

pub(crate) fn enabled() -> Result<bool, String> {
    match std::env::var_os("RUST_INTERP_FUNCTION_DEPENDENCIES") {
        None => Ok(false),
        Some(value) if value == "0" => Ok(false),
        Some(value) if value == "1" => Ok(true),
        _ => Err("RUST_INTERP_FUNCTION_DEPENDENCIES must be 0 or 1".into()),
    }
}

pub(crate) fn observe<'tcx, R>(tcx: TyCtxt<'tcx>, instance: Instance<'tcx>,
                              enabled: bool, operation: impl FnOnce() -> R) -> (R, Option<Value>) {
    if !enabled {
        return (operation(), None);
    }
    let node = MonoItem::Fn(instance).codegen_dep_node(tcx);
    let started = Instant::now();
    let previous_green = tcx.dep_graph.try_mark_green(tcx, &node).is_some();
    let green_check_seconds = started.elapsed().as_secs_f64();
    let result = if previous_green {
        // Marking green has already created the current node and retained its
        // edges. Re-execution verifies the output without duplicating the node.
        tcx.dep_graph.with_ignore(operation)
    } else {
        let (result, index) = tcx.dep_graph.with_task(node, tcx, operation, None);
        tcx.dep_graph.read_index(index);
        result
    };
    (result, Some(json!({"node": format!("{}", node.key_fingerprint),
        "kind": format!("{:?}", node.kind), "previous_green": previous_green,
        "green_check_seconds": green_check_seconds, "lowering_executed": true})))
}
