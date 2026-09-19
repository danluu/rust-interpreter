# Next runtime work

New session/indirect/readonly/spill composition has passed full qualification:
720 Rust tests per profile,446 Python passes/22 skips,52 owned servers/108 clients.
Parser replay passed1824 original invocations and19815 verified template hits;
fre replay passed192 invocations/14548 verified hits; both are closed. Installed
tool3ebea1cd. The fresh40-command fre primary passed and is independently closed:
wall/adopted.9537077504 + A/A.0373937777 = .9911015281; CPU margin.9588016423.
Candidate/native wall1.5416394568. Full176-command fre history also passed and
is closed35515: wall/adopted.9414513615 + A/A.0268743944 = .9683257559;
CPU margin.9629909017, nativewall1.5806520070. Exact closed-primary compiler-cache
retirement is CLOSED60900. Parser14 controls and large/private23 controls are
closed. Full folded history is ACTIVE91338/91341. Finish and independently
close it before admitting pgrust. See STATE.md for paths.

Both parent experiments remain failed; no combined speedup is inferred. The new
cache key binds indirect signature ordinals, and session options are explicitly
transported and verified. Main runtime remains adopted scratch/scalar df4006e0.
No unchanged timing retries or later guards on a failed primary.

No subagents/goal tools; two workers, shared lock, dynamic disk admission. Four
closed old parser caches were safely retired, with all11256 protected hashes
unchanged; never repeat that retirement or clean the shared target/peer caches.
Continue indefinitely and publish qualified evidence regularly.
