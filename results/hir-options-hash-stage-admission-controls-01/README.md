# Hash-stage admission controls

All nine in-memory admission/environment/import controls passed once under the
bounded canonical runner. Independent actual receipt/raw/source verification
passed. No compiler, provider, concrete hash preparation or driver ran.

The source snapshots retain the exact stage/preparer/test bytes exercised by
these controls. This covers the audit gate, environment selection and alias
restoration only; later run-make result bindings and the complete hash stage
still require concrete prerequisite readback and independent qualification.
