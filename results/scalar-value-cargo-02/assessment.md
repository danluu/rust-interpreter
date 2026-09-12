All nineteen Cargo checks pass again with the exact production wrapper paired
with the qualified scalar VM/exporter. This removes a rebuild of unchanged
wrapper source from the performance comparison. The VM and exporter hashes
remain dd9c6b33 and f4051969; the wrapper is the production ba366dd3 binary.

Explicit component key:
ba4ad407e70d887c7872dd85efaaff05fe3efb8e01808767f649ba135803f5c7.
It is SHA256 of the recorded canonical composition JSON, not a legacy source
key. The compiler/runtime source key remains aa56492e. Neither installed build
was overwritten. Normal source selection still uses the production compiler.

The same version toggles, wrong cached header, strict uncalled errors, original
native/custom assertions, trace bindings, audit execution and two audit-version
rejections pass. The source and deliberately damaged sidecar are restored.
Already-qualified real guest artifacts need no rerun: their executing VM and
exporting compiler are unchanged; this qualification exercises the composed
Cargo route. No new performance measurement is claimed.
