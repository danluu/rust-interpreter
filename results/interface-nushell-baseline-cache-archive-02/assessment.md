# First completed custom Cargo-cache archive

The baseline cache of `interface-nushell-repeated-01` is archived after
independently reconstructing its tool key and run namespace and checking every
executed artifact against its preserved snapshot. All 8,523 unique payloads
were decoded and hashed before retiring 23,639 original paths. The invocation
lock was held through revalidation and retirement. All 90 external snapshots
and 99 bound evidence files remain unchanged.

Unique original contents total 2,896,989,978 bytes; the archive
contains 968,365,535 bytes (0.90 GiB). Observed
free space rose from 20,956,872,704 to 22,819,225,600 bytes.
The root and `aarch64-apple-darwin` Cargo attributes are retained in the manifest.
The earlier unsupported-nested-attribute preparation is preserved separately.

A real `nu-protocol` fingerprint was read through the bounded archive inspector
after retirement and matched its original hash; [the receipt](inspection.json)
records the exact member and command. This confirms metadata remains accessible
without restoring the complete cache. The [summary](summary.json) records archive
SHA-256 `1af023aef5d67af0d5392e67a1e87f96399b16c5990cb03c554df6d6968c1fcc` and all original proof/source hashes.
Supervisor 15532 and worker 15536 completed with status 0. Storage work occurred
outside benchmark timers. No tool or benchmark input changed.
