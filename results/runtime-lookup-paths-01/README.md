# Faster runtime manifest validation

The runtime loader checks for file/directory collisions by walking the ancestors
of every installed path. Those paths have already passed canonical relative
POSIX-path validation. Using string ancestors avoids constructing a `Path`
object for every segment while preserving every collision check, installation
identity, directory traversal, file stamp and loader-policy check.

All 22 runtime installation controls passed, including new cases for distant
ancestors, component ordering, destination-prefix collisions, Unicode names,
similar sibling prefixes and malformed paths. Every actual measured lookup
returned the same runtime key, standard-library key and physical sysroots.

Twelve alternating pairs of fresh Python processes looked up the same installed
compiler and prepared standard library. Each arm had one separate warmup; all
observations are retained in `summary.json`.

| Lookup component | Baseline median | Candidate median |
| --- | ---: | ---: |
| Runtime compiler | 76.550 ms | 50.622 ms |
| Prepared standard library | 68.254 ms | 68.257 ms |
| Combined lookup | 144.822 ms | 118.937 ms |
| Combined lookup CPU | 144.710 ms | 118.850 ms |

All twelve pairs improved in lookup wall time and CPU. Wall-time savings ranged
from 24.696 to 29.983 ms. This is a component result on the actual installed
runtime, **not an application build-time result or a sub-0.5-second claim**.
The timer surrounds normal runtime/std loading after Python imports; process
and command times are retained separately. The baseline worker additionally
imports its preserved module, so complete worker times do not estimate the
ordinary launcher's improvement. No compiler, Cargo build or VM ran here.

The initial diagnosis is also retained: three lookups took 197.621, 138.086 and
139.502 ms; a separate cProfile lookup identified path-object construction as
the largest runtime identity-validation cost. Instrumented time is not used in
the paired comparison. All test and measurement commands used the canonical
workload lock, 600-second admission and a 16 GiB entry reserve.

The archive contains both diagnoses, frozen producer inputs, all 27 comparison
child receipts and raw streams, supervisor records and the full runtime test
output. All 347 logical members (195 physical members) were hashed on readback,
including gzip EOF/CRC verification. The archive is 1,481,830 bytes.

- Archive SHA-256: `676cac224089728cd8758c77b9b95007e9c378a9afb42694bc52c48ddc38d26a`.
- Manifest SHA-256: `249ca515a2de8b20cefc9c4dbf5837b11ac7cac2166a44a0b2b10ec92141328d`.
- Comparison receipt SHA-256: `5242635565ef88834a0fae079d5fe05472ff3f2078850d21dee913e45f6f235c`.
