//! Bounded, opt-in diagnostics. These session IDs are never cache keys.
use serde_json::{Value, json};
use std::io::{self, Write};

pub(crate) const MAX_EVENTS: usize = 1_000_000;
pub(crate) const MAX_BYTES: usize = 64 * 1024 * 1024;
pub(crate) const MAX_ALLOCATION_BYTES: usize = 16 * 1024 * 1024;

pub(crate) struct Trace {
    bytes: Vec<u8>,
    events: usize,
    max_events: usize,
    max_bytes: usize,
    failed: bool,
}

struct LimitedWriter<'a> {
    bytes: &'a mut Vec<u8>,
    limit: usize,
}

impl Write for LimitedWriter<'_> {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        if bytes.len() > self.limit.saturating_sub(self.bytes.len()) {
            return Err(io::Error::other("allocation trace byte limit reached"));
        }
        self.bytes.extend_from_slice(bytes);
        Ok(bytes.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

impl Trace {
    pub(crate) fn new() -> Self {
        Self::with_limits(MAX_EVENTS, MAX_BYTES)
    }

    fn with_limits(max_events: usize, max_bytes: usize) -> Self {
        Self {
            bytes: Vec::new(),
            events: 0,
            max_events,
            max_bytes,
            failed: false,
        }
    }

    /// Roll back a partial record and poison the whole trace on any failure.
    /// The exporter must not publish a truncated diagnostic as complete.
    pub(crate) fn event(&mut self, mut value: Value) -> Result<usize, String> {
        if self.failed {
            return Err("allocation trace already failed".into());
        }
        let before = self.bytes.len();
        let result = (|| {
            if self.events >= self.max_events {
                return Err("allocation trace event limit reached".into());
            }
            let object = value
                .as_object_mut()
                .ok_or("allocation trace event must be an object")?;
            if object.contains_key("event") {
                return Err("allocation trace event ID is reserved".into());
            }
            object.insert("event".into(), json!(self.events));
            let mut writer = LimitedWriter {
                bytes: &mut self.bytes,
                limit: self.max_bytes,
            };
            serde_json::to_writer(&mut writer, &value).map_err(|e| e.to_string())?;
            writer.write_all(b"\n").map_err(|e| e.to_string())?;
            Ok(self.events)
        })();
        match result {
            Ok(id) => {
                self.events += 1;
                Ok(id)
            }
            Err(error) => {
                self.bytes.truncate(before);
                self.failed = true;
                Err(error)
            }
        }
    }

    pub(crate) fn finish(mut self, artifact_sha256: &str) -> Result<Vec<u8>, String> {
        self.event(json!({"kind": "complete", "prior_events": self.events,
                          "artifact_sha256": artifact_sha256}))?;
        Ok(self.bytes)
    }
}

pub(crate) fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut result = String::with_capacity(bytes.len() * 2);
    for &byte in bytes {
        result.push(DIGITS[(byte >> 4) as usize] as char);
        result.push(DIGITS[(byte & 15) as usize] as char);
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn complete_trace_has_ordered_ids_and_artifact_binding() {
        let mut trace = Trace::new();
        assert_eq!(
            trace
                .event(json!({"kind": "header", "text": "λ\nquoted \""}))
                .unwrap(),
            0
        );
        assert_eq!(
            trace
                .event(json!({"kind": "request", "parent": 0}))
                .unwrap(),
            1
        );
        let bytes = trace.finish("artifact-digest").unwrap();
        let records: Vec<Value> = std::str::from_utf8(&bytes)
            .unwrap()
            .lines()
            .map(|line| serde_json::from_str(line).unwrap())
            .collect();
        assert_eq!(records.len(), 3);
        for (id, record) in records.iter().enumerate() {
            assert_eq!(record["event"], id);
        }
        assert_eq!(records[2]["kind"], "complete");
        assert_eq!(records[2]["prior_events"], 2);
        assert_eq!(records[2]["artifact_sha256"], "artifact-digest");
    }

    #[test]
    fn byte_limit_includes_newline_and_failed_record_is_atomic() {
        let value = json!({"kind": "x"});
        let mut measured = Trace::new();
        measured.event(value.clone()).unwrap();
        let size = measured.bytes.len();
        let mut exact = Trace::with_limits(10, size);
        exact.event(value.clone()).unwrap();
        assert_eq!(exact.bytes.len(), size);
        assert!(exact.event(value.clone()).is_err());
        assert_eq!(exact.bytes, measured.bytes);
        assert!(exact.finish("digest").is_err());
        let mut short = Trace::with_limits(10, size - 1);
        assert!(short.event(value).is_err());
        assert!(short.bytes.is_empty());
        assert!(short.failed);
    }

    #[test]
    fn event_limit_also_applies_to_completion() {
        let mut trace = Trace::with_limits(1, 1024);
        trace.event(json!({"kind": "header"})).unwrap();
        assert!(trace.finish("digest").unwrap_err().contains("event limit"));
    }

    #[test]
    fn malformed_or_reserved_event_poisons_trace() {
        for value in [json!(true), json!({"event": 99})] {
            let mut trace = Trace::new();
            assert!(trace.event(value).is_err());
            assert!(trace.event(json!({"kind": "valid"})).is_err());
            assert!(trace.bytes.is_empty());
        }
        assert_eq!(hex(&[0, 1, 15, 16, 127, 128, 255]), "00010f107f80ff");
    }
}
