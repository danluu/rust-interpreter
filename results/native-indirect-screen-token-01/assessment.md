# Native indirect-call screen: wall gate not met

All40 commands preserve original, deliberately wrong, valid-edit and restored
outcomes. Candidate and control bytecode/catalogs agree; source and original
tests are restored. Five paired valid edits give:

| Measure | Candidate / adopted | A/A envelope |
| --- | ---: | ---: |
| Wall | 0.9593646002 (4.06% lower) | 4.5568% |
| CPU | 0.9882043890 (1.18% lower) | 2.4166% |

The required wall margin is1.0049329818, so the predeclared gate fails. The
CPU margin1.0123699797 passes its bound. The short-screen ordinary-native ratio
is1.6066828180; this is not an adopted or general project speedup. No full
comparison, held-out project history or parser controls have started. Do not
retime this unchanged candidate or treat the failed gate as proof of zero gain.

The mechanism works: the two exact original token profiles move1,025,927 and
843,753 calls into native code, eliminating exactly that many JIT reentries.
All logical per-PC counts, entropy, memory and outcomes agree; no new function
declines occur. Native bytes grow29,216/27,000, and the folded control moves30
calls with4,412 extra bytes.541 workspace checks/profile,119 strict/cache
commands,13 screen controls and384 launcher tests (16 skipped) pass.

Retain the opt-in source and immutable tool on its experiment branch. Main's
adopted runtime remains unchanged. Next assess a composition with successor-only
register flushing, using its existing correctness evidence and fresh combined
qualification. The two mechanisms may overlap; their standalone point estimates
are not additive, and a new composition still needs every applicable gate.
