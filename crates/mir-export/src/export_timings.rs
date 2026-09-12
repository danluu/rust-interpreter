//! Optional, non-overlapping wall-time scopes within one exporter phase.
//! These diagnostics do not change the artifact or rustc's checking policy.
use std::time::Instant;

pub(crate) struct Timings {
    scope: &'static str,
    clock: Option<(Instant, Instant)>,
    stages: Vec<(&'static str, f64)>,
}

impl Timings {
    pub fn new(scope: &'static str) -> Self {
        let clock = (std::env::var("RUST_INTERP_EXPORT_TIMINGS").as_deref() == Ok("1"))
            .then(|| { let now = Instant::now(); (now, now) });
        Self { scope, clock, stages: Vec::new() }
    }

    pub fn checkpoint(&mut self, name: &'static str) {
        if let Some((_, previous)) = &mut self.clock {
            let now = Instant::now();
            self.stages.push((name, now.duration_since(*previous).as_secs_f64()));
            *previous = now;
        }
    }

    pub fn finish(mut self) {
        self.checkpoint("remaining");
        if let Some((started, finished)) = self.clock {
            eprintln!("rust-interp-export-timings: {}", serde_json::json!({
                "schema_version": 1,
                "scope": self.scope,
                "stages": self.stages.iter().map(|(name, seconds)|
                    serde_json::json!({"name": name, "seconds": seconds})).collect::<Vec<_>>(),
                "total_seconds": finished.duration_since(started).as_secs_f64(),
                "interpretation": "exclusive within this scope; lower scope is nested in emit.lower_graph"
            }));
        }
    }
}
