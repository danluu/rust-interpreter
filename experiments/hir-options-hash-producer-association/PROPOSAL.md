# Source-only producer association proposal

The two different native Cargo environments in the retained historical child
are explained by bootstrap's dry self-check followed by its real execution.
The proposed first change is to distinguish those two classes using balanced
step-timing records. It would keep the full printed-command catalog and the
current complete-environment equality rule among **real** same-child contexts.
It would not discard arbitrary environment keys, choose the last convenient
printed command, or rerun a compiler. Frozen B3 successor02 and its 49 passed
pure controls remain unchanged. No successor03 parser or control has run.

The historical observation is not evidence that the new candidate has built.
New build02 output discovery and exact producer coverage remain required.

## Bound source contract

In the exact candidate bootstrap source:

- `core/session.rs` runs `execute_cli()` in a fresh Builder with
  `DryRun::SelfCheck`, then in another fresh Builder with `DryRun::Disabled`.
- `core/build_steps/compile.rs::stream_cargo` prints its verbose `running:`
  command before calling `stream_capture_stdout`. The latter returns `None`
  during dry-run unless the command explicitly opts into dry-run execution.
- `utils/exec.rs` initializes `BootstrapCommand::run_in_dry_run` to false and
  its `ExecutionContext::stream` checks that flag before spawning. The Cargo
  command is private to `builder/cargo.rs`, which does not enable that flag;
  `stream_cargo` also does not enable it. Other initialization commands can
  execute during setup and must not be confused with this specific contract.
- `Builder::ensure` prints matching `[TIMING:start]` and `[TIMING:end]` around
  `Step::run` only when `print_step_timings && !dry_run`. The candidate's bound
  bootstrap configuration has `print-step-timings = true`.
- `stream_cargo` captures stdout, consumes Cargo JSON, and waits for the Cargo
  process before returning. Its stderr is inherited. With the current default
  JSON-output configuration, compiler-artifact JSON is consumed rather than
  forwarded. It is unavailable as an independent association channel.
- `bootstrap.py` first builds bootstrap through a synchronous Cargo process,
  waits for it, and only then runs the bootstrap executable. That initial
  Cargo's `Finished` line is separate from the later Rust bootstrap commands.

Before implementing classification, a successor must bind these complete source
files, command construction/conversion, relevant Cargo-emitting Step paths,
the selected configuration and actual child argv/environment. An unrelated
`running:` line, an opt-in dry-run command, disabled timing, multiline/unparsed
timing event, unknown Cargo execution route or a command outside a proved Step
must remain an admission failure. Step names alone are not an executable hash.

## Observed historical trace

The existing native005 stdout is 73 lines/29,728 bytes and contains zero
compiler-artifact JSON lines. It has 30 matched timing events:

| Stdout line | Printed Cargo target | Open timing stack | Interpretation under bound contract |
| --- | --- | --- | --- |
| 32 | stage1-rustc | empty | self-check print; no native process |
| 33 | stage1-std | empty | self-check print; no std process |
| 57 | stage1-rustc | compile::Assemble → compile::Rustc | real native Cargo context |
| 70 | stage1-std | compile::Std | real std Cargo context |

There is an earlier real `tool::LibcxxVersionTool` timing pair at lines 23–25.
Therefore selecting everything after the first timing event would incorrectly
admit both self-check prints. The complete balanced stack is necessary.

Historical stderr is 1,110 lines/2,476,991 bytes. Its three exact Cargo terminal
lines are bootstrap `dev` at line 67, native `release` at line 983 and std `dist`
at line 1109. The corresponding segments contain 0, 173 and 42 Cargo `Running`
lines. These counts include non-rustc commands and are not a private-artifact
coverage denominator. One trailing non-command line remains after line 1109.
The native and std stderr regions must retain every diagnostic and warning.

The unused self-check native print differs from the real native context in
AR/CC/CXX/RANLIB target settings, target linker and LLVM_LINK_SHARED. None of
these keys should be projected away. The execution distinction explains their
presence; it does not prove arbitrary environment differences harmless.

## Conservative successor and possible later extension

A minimal successor03 could retain all printed Cargo commands with their raw
coordinates and complete environments, parse/validate the entire timing stack,
and separately mark source-proved self-check prints. Actual producer association
would consider every real native-tree context in that child and keep the exact
two-shim/D2 provider checks and complete effective-environment equality. If more
than one real context differs, it would still reject the history. This may be
sufficient for the actual candidate, but only its completed history can answer
that question.

If the actual build has differing real contexts, stderr `Finished` boundaries
are a possible separate extension, not a current proof:

1. Inventory every real Cargo invocation, including the Python bootstrap build,
   stream-captured Cargo and any direct test/tool commands. Prove serialized
   invocation order and synchronous completion from exact source and raw bytes.
2. Require complete, uniquely matching terminal boundaries, expected profiles,
   actual success, and exact command counts. Do not derive a cross-stream wall
   timestamp or silently ignore unknown extra terminal lines.
3. Bind each compiler `Running` line to its containing completed Cargo segment,
   then verify exact output stem/type/target, compiler route and full environment.
4. For a private artifact produced in more than one completed segment, use the
   last completed producing segment in the ordered successful build history.
   Reject duplicate producers within a segment unless their completion/order is
   independently proved; the last `Running` line is not necessarily the last
   finisher when Cargo executes jobs concurrently.
5. Continue proving final ordinary artifact bytes/stamps, complete native stamp
   membership, ordered rustc_main driver pair and all post-build copy/strip
   operations. Cargo `Fresh` lines are not new producers. A missing producer or
   unknown native build-script artifact still requires a separate proof.

This extension still needs a bound Cargo terminal-output contract and complete
actual event coverage for all relevant stages. The historical counts alone do
not establish those obligations. No parser should accept them by analogy.

## Required source cases before any successor qualification

- Retained real historical trace: all 30 timing events balance; printed32/33
  remain in the catalog as self-check; real57/70 retain their full environments.
- Real setup timing before self-check: a closed LibcxxVersionTool step must not
  cause later empty-stack prints to become real.
- Real nested contexts: native Cargo inside Assemble/Rustc is associated with
  the inner step while the outer stack remains intact; sibling std is separate.
- Malformed, missing, out-of-order or mismatched timing ends; a partially parsed
  event; missing timing configuration; unknown emitting path: reject.
- Two real same-child native contexts with different arbitrary environment,
  source identity, LLVM/linker or wrapper values: reject exactly as successor02.
- Self-check and real commands with otherwise identical argv: retain both raw
  records rather than deduplicating away the evidence of two printed contexts.
- Truncated/extra Finished boundaries and multiple same-output producers in one
  concurrent segment: reject any proposed segment extension.

These are planned controls, not claimed executed tests. The retained observation
script only reads existing source/streams and writes its own report; it invokes
no compiler, Cargo, application or process-control command.
