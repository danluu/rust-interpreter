# Census explicit known reads from immutable program data

Current ordinary emitter facts can identify a Load/Copy source as an immediate
address, but the emitter still loads it at runtime. Observe existing facts only:
size1..16, nonzero full-width address exactly convertible to usize, complete range
inside immutable Program.data. Exclude heap/statics, dynamic/local addresses,
null, truncating high bits, overflow, large copies and all writes. Record exact
bytes without changing facts or code. This does not infer pointer provenance
from arbitrary literals; the selected value is the explicit read operand.

Two Rust controls/profile verify boundaries, full-width values, source selection
and disabled/error cleanup; two Python controls verify sample ownership. Rebuild
all three closed adopted captures (block/exhaustive/parser), preserving every
word, entry, resume, assertion and operation count. Then join the observed reads
to their exact native spans and existing normal-entropy sample captures. Seven
commands; zero guest execution or native publication. Samples are partial and
perturbed; counts cannot establish removable latency. No propagated new facts
are modeled. Only sufficient measured scope warrants an actual runtime candidate.

Shared lock; existing ROOT target; two Cargo/test workers; max(14 GiB,8 GiB plus
twice allocated target) build admission and8 GiB child floor. Retain failures and
complete evidence. No changes to compiler/exporter ownership or paused goal.
