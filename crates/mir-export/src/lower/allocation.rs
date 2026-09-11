//! Observe the existing allocation traversal without changing its ordering.
use super::*;
use serde_json::{Value, json};

impl<'tcx> Exporter<'tcx> {
    pub(super) fn trace_event(
        &mut self,
        details: impl FnOnce(TyCtxt<'tcx>) -> Value,
    ) -> Result<Option<usize>> {
        if self.trace.is_none() {
            return Ok(None);
        }
        let mut value = details(self.tcx);
        let fields = value
            .as_object_mut()
            .ok_or("invalid allocation trace event")?;
        fields
            .entry("parent")
            .or_insert_with(|| json!(self.trace_parent));
        fields
            .entry("function_index")
            .or_insert_with(|| json!(self.trace_function));
        self.trace.as_mut().unwrap().event(value).map(Some)
    }

    pub(super) fn with_trace_parent<T>(
        &mut self,
        parent: Option<usize>,
        operation: impl FnOnce(&mut Self) -> Result<T>,
    ) -> Result<T> {
        let previous = self.trace_parent;
        self.trace_parent = parent.or(previous);
        let result = operation(self);
        self.trace_parent = previous;
        result
    }

    pub(super) fn trace_materialization(
        &mut self,
        allocation: ConstAllocation<'tcx>,
        id: Option<AllocId>,
        tls: Option<rustc_hir::def_id::DefId>,
        pointer: usize,
        reserved_alignment: usize,
    ) -> Result<Option<usize>> {
        if self.trace.is_none() {
            return Ok(None);
        }
        let allocation = allocation.inner();
        if allocation.len() > crate::allocation_trace::MAX_ALLOCATION_BYTES {
            return Err("allocation trace individual allocation limit reached".into());
        }
        let bytes = allocation.inspect_with_uninit_and_ptr_outside_interpreter(0..allocation.len());
        let mut initialized = vec![0u8; allocation.len().div_ceil(8)];
        for offset in 0..allocation.len() {
            if allocation
                .init_mask()
                .get(rustc_abi::Size::from_bytes(offset))
            {
                initialized[offset / 8] |= 1 << (offset % 8);
            }
        }
        // Relocations are emitted individually by materialize, before each
        // recursive request. No unbounded relocation array is constructed.
        self.trace_event(|tcx| {
            json!({"kind": "materialization",
            "allocation_id": id.map(|id| id.0.get().to_string()),
            "tls_definition": tls.map(|def| tcx.def_path_str(def)),
            "size": allocation.len(), "alignment": allocation.align.bytes(),
            "reserved_alignment": reserved_alignment, "mutable": allocation.mutability.is_mut(),
            "pointer": pointer, "bytes_hex": crate::allocation_trace::hex(bytes),
            "initialized_bits_hex": crate::allocation_trace::hex(&initialized),
            "initialized_bit_order": "least significant bit first within each byte",
            "relocation_count": allocation.provenance().ptrs().iter().count()})
        })
    }
}
