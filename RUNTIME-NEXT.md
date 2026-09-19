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
closed. Folded176-command regression guard passed and CLOSED95676 (wall change
within A/A). Full-token cache retirement CLOSED33463 preserves3759hashes.
Pgrust01 failed before timings: its borrow fixture used std in a no_std crate.
Two compiler errors,zero server requests; source restored and failure CLOSED97727.
Dedicated pgrust02 uses core and fresh namespaces. Its26-control protocol passed
and CLOSED40059, including four real std/no_std compiler probes. Pgrust02 is
complete53869/53872 with176 commands+2strict, independently CLOSED4260. Initial
audit90875 failed only on tuple-vs-JSON-list metadata; preserved without rerunning
any timing. Regression margins wall1.0152011429/CPU1.0136701561 pass; four tests.
Parser protocol02 passed14 controls and CLOSED23181; large protocol02 passed23
and CLOSED43657. First rg admission and first large audit timed out on the shared
lock before work; both preserved. Actual rg-aot176 commands+2strict passed and
CLOSED94315 under outer suffix-admitted-02. Wall margin1.0308613865 and CPU
margin1.0375064256 pass; nativewall.5910980861. No clear gain versus adopted.

Next: parser incremental, parser repository defaults, Nushell last. Transparent
compression of373 closed public bytecode copies is independently CLOSED52338,
saving7.31GiB allocated blocks while preserving every original plaintext hash
and required metadata. Partial conversion and both disposable metadata probes
are retained; continuation02 finished only241 uncompleted entries. Never rerun
these mutations or old stat inventories. Free24.7GiB now meets parser24GiB;
recheck at admission. Nushell66.54872655GiB remains unmet. Saved-history cost
analysis is independently CLOSED70818; no new timings. Main proof publicationc08fb7ce.

Both parents failed. Main runtime stays scratch/scalar df4006e0 until every guard
and current-main integration passes. No unchanged timing retries. No subagents
or goal tools; two workers, shared lock, dynamic admission. Primary/token and old
parser/Nushell retirements are complete and MUST NOT repeat. See STATE.md.
Continue indefinitely and publish qualified evidence regularly.
