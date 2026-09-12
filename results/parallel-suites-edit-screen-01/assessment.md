The fixed changed-source screen passes all three cases and all120 commands.
Each case has five valid production edits, with cold, deliberately wrong and
restored-original states outside the medians. Original test sources and paired
bytecode/catalogs match; every mode restores source and agrees on assertions.

| Selection | Tests | Custom wall change | Custom CPU change | Candidate/native latency |
| --- | ---: | ---: | ---: | ---: |
| token | 12 | −34.3% | +3.2% | 2.216× |
| folded | 18 | −2.1% | +0.5% | 1.002× |
| pgrust | 4 | +3.2% | +4.3% | 0.771× |

Ratios are medians of paired edited commands. Both custom routes use prepared
execution; the candidate runs two isolated test workers, the retained tool one.
Every Cargo build uses two workers. The primary native control in this screen
uses two isolated test processes; a separate serial native control is retained.
This does not establish fastest native execution. Future adoption measurements
will add ordinary Cargo/libtest with default test concurrency.

Keep concurrency available explicitly and one worker as default while that
control is qualified. The next optimization is a prospective composition under
[the revised review](../../docs/SUGGESTIONS-REVIEW-20260912.md). Do not rerun these
screens for a different result or claim they cover an entire project.
