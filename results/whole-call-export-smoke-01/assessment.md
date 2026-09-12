# Preserved capability admission failure

The launcher rejected inline-leaves before Cargo/export/guest execution. The isolated builder copied the old compiler capability metadata, including its exporter hash, although it correctly rebuilt and hashed the new exporter. Preserve that receipt and regenerate capabilities by probing the exact installed new exporter, with binary/manifests unchanged. All 300 debug/release tests and original-artifact runtime results remain valid; they do not depend on this launcher capability sidecar.
