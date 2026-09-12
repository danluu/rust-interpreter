//! Rust caller locations travel through the ordinary guest call ABI.
use super::*;

enum Source {
    Inherited(Slot),
    Constant(rustc_span::Span),
}

impl<'a, 'tcx> Lower<'a, 'tcx> {
    pub(super) fn caller_argument(&mut self, source_info: mir::SourceInfo) -> Result<Reg> {
        // This compiler helper also handles MIR-inlined source scopes: an
        // untracked inlined function ends propagation just like a real frame.
        let source = self.body.caller_location_span(
            source_info, self.caller_location.map(Source::Inherited), self.tcx(), Source::Constant,
        );
        match source {
            Source::Inherited(slot) => Ok(self.local(slot.offset)),
            Source::Constant(span) => {
                let value = self.tcx().span_as_caller_location(span);
                let ConstValue::Scalar(Scalar::Ptr(pointer, _)) = value else {
                    return Err("caller location is not a constant pointer".into());
                };
                let origin = self.exporter.trace_event(|tcx| serde_json::json!({"kind": "caller-location-origin",
                    "source": tcx.sess.source_map().span_to_diagnostic_string(span)}))?;
                let allocation = pointer.provenance.alloc_id();
                let addend = pointer.prov_and_relative_offset().1.bytes();
                let base = self.exporter.with_trace_parent(origin, |e| e.alloc(allocation))?;
                let pointer = (base as u64).checked_add(addend)
                    .ok_or("caller-location address overflow")?;
                let address = self.temporary(8);
                let value = self.imm_pointer(pointer as u128, addend, PointerKind::CallerLocation,
                    || format!("allocation:{}", allocation.0.get()))?;
                self.store(address, value, 8)?;
                Ok(address)
            }
        }
    }
}
