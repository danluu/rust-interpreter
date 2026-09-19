# Options-hash compiler admission, 2026-09-18

Metadata admission passed through two preserved histories: the original 48
successful probes ended in a strict linker-output parser rejection; a corrected
parser passed nine controls, consumed those exact saved probe outputs, and ran
only the two missing Git postguards. The final metadata result admits the
candidate source and providers. It does not qualify a new compiler binary.

The first compiler build then stopped while building Cargo's bootstrap package:
the generated source tree was discovered inside the interpreter repository's
parent workspace. Two Git guards and the failed bootstrap command are retained;
no compiler stage completed. Six offline metadata controls using the exact
extracted beta Cargo verified that excluding `.work` from the parent workspace
isolates generated projects while retaining ordinary workspace membership and
rejecting an unrelated orphan package. This general parent-manifest fix changes
no compiler or application source. The separately reviewed build02 continuation
reuses the extracted providers and preserves the failed attempt; it was still
unrun when this archive completed.

`evidence.tar.gz` preserves all 60 completed child histories, their raw streams,
source and frozen catalogs, independent audits, the 14-file workspace fixture,
and the original parent-manifest bytes. It excludes live compiler, SDK,
registry, seed and provider payloads, plus mutable build02 evidence. The prior
preparation archive remains a separately hash-bound artifact. A read-only
preparer initially found the prior result unmaterialized in X's sparse checkout;
its failure note is retained, and the final packet references the identical
already-landed archive in the integration checkout.

The evidence-only archive ran once under the canonical lock with a 9 GiB live
floor and 192 MiB reservation. It is 17,936,663 bytes, with 313 logical members
represented by 231 physical payloads. Both the archiver and a separate audit
rehash every member, follow only backward content-deduplication links, read the
full gzip stream through EOF/CRC, and recheck all 312 source/proof inputs.
No compiler, metadata probe or test was rerun during retention.

- Archive SHA256: `f965116855fe2cd33b325f4fd4c924ec0d6c82140e05dd63019a21f50409bd26`
- Manifest SHA256: `653ed8a194f1c6976ef435a89689f88ba8ba27ca80fcb175af60008dd8ce9e1c`
- Verification SHA256: `e2e004457fe178fa574d8ef103f5f6cc2f5233c30a69aa753913a058802cce5d`

`archive-execution.json` associates the exact launch, supervisor and terminal.
`manifest.json` maps every logical member to its bytes and digest;
`verification.json` records the independent complete readback. Exact retention
source snapshots are in `experiments/hir-options-hash/admission-01`.
This packet reports no compiler/application correctness result, performance
improvement, or attainment of the 0.5-second target.
