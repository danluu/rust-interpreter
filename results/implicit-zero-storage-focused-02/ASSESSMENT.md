# Focused representation controls

All9 controls pass in debug/release. Physical poisoned-register probes verify
omitted stores, reconstructed high reads, actual persistent reloads and complete
host ABI preservation. Additional controls cover read aliases, unusual read
roles, code/metadata admission, reconstruction after metadata exhaustion,
wide/narrow function reuse, initial-zero reads, all budget prefixes, faults,
TLS callbacks, indirect handles and12,160 arithmetic input combinations.

Review identified a stronger end-to-end poison fixture: a native-only wide
Store might never spill its persistent value to backing. Focused03 will add an
actual interpreted128-bit read before the frame is reused. This does not undo
the physically poisoned isolated controls here. No timing or adoption follows.
