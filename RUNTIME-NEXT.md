# Next runtime work

Current branch experiment/parameterized-literals-20260919. Explicit selected large
literals are opaque to folding/range/call-slot analyses; checked native relocation
sites and a separate emission manifest carry their current values. Preserve small
constant folding, fused fills, instruction width, all other inputs and callee proofs.
Focused05 c24e1eba passed34controls/profile+24featureoff, closed69859 after14584/14687.
Includes live arithmetic/overflow, addresses/faults, memory forwarding and budgets.

Full qualification01 (72986/72989) was NOT ADMITTED: peer held benchmark.lock;
45s timeout before any build/test/raw directory. Preserved results/parameterized-
literals-qualification-01. Next qualification02 prepared:673Rust/profile+17ignored,
33diagnostic,10ordinarysession,24ordinarymodel/defaultVM; reuse442Python+22skip
only through unchanged source/log bindings. Wait for lock before launch.
Then prepared parser-client01:1824actual saved invocations, fresh verification of
every hit. Then literal-phases-parser01 evaluates key/miss/restore costs separately.
Install controller prepared but do not launch until diagnostics support mechanism.
Primary05 prerequisite bindings still point at old digest candidate: update only
after qualified installation. Current runtime remains experimental, no adoption.

Motivation: closed actual miss trace/join shows3462changed-key misses/214.939ms;
2563bodies differ only in immediate values/152.106ms. Eviction only22/1.421ms.
Narrow relocation census matches154/5.166ms:parked. Buffered keys:parked; phase
key10.539ms vs earlier8.883ms, no affirmative improvement (not causal comparison).
See docs/TEMPLATE-MISS-HISTORY-20260919.md and RELOCATABLE-IMMEDIATES-20260919.md.

Previous digest NOT adopted: primary04 narrowpass, full110-command guard
UNMEASURABLE wall.9437843138+A/A.1156560910=1.0594404049. CPU.9129773888+
.0722446023=.9852219911. All110+2strictcorrect. No unchanged retry/laterguards.
Adoptedtool df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62,
proof results/scratch-scalar-main-qualification-01/summary.json. StrictRustchecking.

Saved goal PAUSED; no goaltools/subagents/peercontrol. Only root and
.work/publication-main worktrees ours. Two Cargo/testworkers. Serialize substantial
work via benchmark.lock45s. Buildtarget .work/fixed-frame-clear-combined-build-01/target
neverclean; buildfloor max(14GiB,8GiB+2*allocated target). Replay/analysis12GiB,
child/closure8GiB,parser24GiB+16GiBcacheallowance,Nushell47GiB. Read-only cleaner
/usr/bin/python3 /Users/danluu/dev/disk-cleanup-monitor-20260912.py status.
Free~25GiB variable. SuggestionsSHA4d74b3dc... unchanged/re-read September19.

Do notrepeat completedcache retirement: primary01/02,03+strict01/02/03,
primary04+strict, recenttoken02, frecustom01. Preserve all proofs/binaries/sources
and sharedbuildtarget. Closed fullparser01 caches may be audited if needed.
Main8509b167 pushed narrow census evidence, preserving peer0dda92e2.
