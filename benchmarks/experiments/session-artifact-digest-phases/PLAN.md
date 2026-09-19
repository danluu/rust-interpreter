# Artifact digest phase attribution

After closed workspace qualification and verified actual parser replay, use the
separately retained diagnostic binaries from session-artifact-digest-qualification-01.
Run16saved actual suites/1,824invocations, with history off/on and hit verification
off for elapsed phase attribution. Validate outcomes/failure text and phase sums,
actual file sizes, limits, private workers, bounded cache and full kernel CPU.
Dedicated owned endpoints digest-input-phases-01-{fresh,cached}; owner EOF/reap.
No compiler/source changes, new benchmark workload, speedup or acceptance claim.

Question: does catalog validation avoid the previous second hash while actual
input hashing, decode and full Program validation remain? Compare observed phase
magnitudes descriptively; these separated diagnostic runs do not isolate a causal
wall-speedup. Do not sum overlapping worker intervals or call them CPU. Main is
unchanged. Serialize benchmark.lock,12GiB admission/8GiB child floor,2workers.
