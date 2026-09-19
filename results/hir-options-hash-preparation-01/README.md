# Options-hash compiler preparation

The isolated compiler source and offline providers were acquired successfully at
candidate commit `4de35bdacef0e3cd18a66bc30b5459c19e09b118`, based on
`7efc0d9484da82cd327deb3b48616f8ec81eaf8d`. The candidate changes only the
per-context options-hash cache and its generated HIR source identity.

The acquisition completed all 17 local Git commands and 908 independent provider
copies. Full readback checked all 64,443 original frozen files, the resulting
source/backtrace contents, and every copied provider. Four acquisition controls,
five initial allocation controls, and fifteen successor allocation/monitor/linker
controls passed. The successor monitor continues checking capacity after a
retained bookkeeping failure or a delayed exit following its owned stop request.

No candidate compiler build, native recipe, hash-driver qualification, runtime
installation, application test, or performance comparison has run. Metadata03 is
reviewed but remains unrun behind the unchanged 24 GiB entry requirement. Earlier
metadata and retention proposals remain historical and unrun. The expected
benefit of caching the options hash remains unmeasured.

The archive retains all selected experiment source, complete input catalogs,
actual receipts and raw streams, independent audits, and the reviewed unrun
proposals. It does not duplicate live compiler, SDK, registry, or seed payloads.
The acquisition readback and their content identities remain explicit evidence;
a catalog is not a claim that all external payload bytes are in this archive.
Generated plan/input/launch JSON is retained in the archive at its original
absolute-path-derived member name. Directly tracked Python/Rust/patch files are
provided for review; restoring an original prepared attempt requires its archived
JSON and exact original inputs, rather than relabeling a new machine's files.

Retention03 passed once with a 9 GiB live floor and 128 MiB reservation. All 243
logical members (190 physical payloads), their hashes and backward links, and the
complete gzip EOF/CRC were independently checked. The archive is 39,584,137 bytes,
SHA256 `88420663870dbb118df5a4fbe791a59e9ddc684d789c61260c3638a075822415`.
See `manifest.json`, `archive-execution.json`, and `verification.json` for the
complete scope and actual process associations.
