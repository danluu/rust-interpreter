# Staged production compiler driver

This implements the reviewed `MONO-PRODUCTION-ADMISSION.md` setup/build plan.
It is source-only until an exact generated plan is reviewed and admitted. The
fresh compiler destination remains `/Users/danluu/dev/rustc-stable-mono-production-20260913`.
The driver owner is the interpreter worktree containing `production-driver.py`;
it writes only that owner's run directory and the explicitly fresh compiler
source. The old source, stage sysroots, packages, installations and archives
are read-only inputs. No cache retirement is performed.

Generate the plan after the source/harness checkpoint is committed:

```sh
python3 experiments/stable-cgu/production-driver.py plan \
  --run-id mono-production-build-01 \
  --output "$PWD/experiments/stable-cgu/planned-mono-production-build-01.json"
```

Planning hashes the source/harness inputs and full public rust-src inventory
under the canonical lock, with its own bounded admission/process receipt. It
does not copy sources/archives, probe compilers, download, build or test.
Archive hashes come from the reviewed stage0 manifest
and retained CI proof. Their actual large files are rehashed at admitted setup.

After review, admit exactly one stage at a time:

```sh
python3 experiments/stable-cgu/production-driver.py run \
  --plan "$PWD/experiments/stable-cgu/planned-mono-production-build-01.json" \
  --stage prepare --attempt prepare-01
```

Every invocation records its supervisor PID, parent, plan hash, canonical lock,
admission, child identities, exact commands, environment, separate stdout and
stderr, disk observations, exit status and receipts. Use the existing external
owned supervisor to start this command and retain its process identity. The
driver itself bounds lock acquisition at 600 seconds and prints progress every
30 seconds while a child runs. Package/control helpers inherit the held
canonical lock descriptor; a different open description cannot bypass it.

Stages run in the following order. Substitute each stage name into the same
command, with a fresh explicit attempt name. Successful predecessors are
hash-checked; a failed or omitted predecessor cannot be skipped.

1. `prepare`: require 36 GiB free; verify all five stage0/formatter archives and
   CI LLVM; clone independent Git objects with no hardlinks or alternates;
   check out exact73a, materialize pinned backtrace, apply and verify the exact
   six-file per-item patch, copy the exact production TOML and seed only new
   bootstrap archive caches. Record OS, SDK, clang and linker metadata.
2. `freeze-source`: run the focused format check. If that check fails, preserve
   it, format only the reviewed six files, then require a new successful check.
   Commit the real result as C_mono, retain the formatted mono delta and complete
   upstream-to-C_mono patch, and freeze complete tracked and backtrace inventories.
3. `stage1`: build compiler and native standard library with two jobs.
4. `stage1-controls`: all partitioning codegen tests and the new full mono
   run-make history.
5. `stage2`: build compiler and native standard library with two jobs.
6. `option-hash`: existing compiler-interface unstable-option tracking test.
7. `stage2-controls`: all partitioning tests and both complete module/mono
   run-make histories, retaining post-test stage2 runtime inventory.
8. `dist`: build rustc-dev and rust-std components and retain exact image hashes.
9. `package`: compose a fresh complete prefix. Preserve stage2/std/dev bytes,
   runtime additions and LLVM aliases; materialize the exact public distributed
   library source tree after comparing tracked/backtrace files against C_mono;
   include the CI archive's verified rust-objcopy. Require truthful version and
   both options, full reviewed production TOML, and a raw unmapped E0080 core/std
   snippet probe through the existing std-source validator. Keep loader output.
10. `native-controls`: retain all15 compile/execute states with module off and
    mono policy selected, including real binary activation and edit/restoration.
11. `strip-controls`: retain all six native binary/proc-macro strip states and
    actual stripped-macro loading/execution, with module off and mono selected.
12. `complete`: rehash the composed package after all controls and record its
    handoff paths. This does not claim installation or strict interpreter36
qualification; those and the matched27 screen remain separate gates.

The public rust-src component and installer metadata are pinned in the plan.
Package construction rechecks its complete inventory, all tracked library and
backtrace bytes against the new compiler, and exactly the previously documented
distribution omissions. Distribution-only `vendor/` files are checked against
their Cargo checksums and the library lockfile; the distributed `.cargo` config
is retained separately. These extras are not claimed to be rustc Git source or
verified `.crate` archives. The resulting installed library tree remains exactly
equal to the public tree required by strict native/prepared diagnostic checks.

All bootstrap build/test/dist commands retain `-vv` output so actual compiler
environment/flags are reviewable. The environment whitelist prevents unrelated
credentials appearing in verbose build logs. Cargo is offline; normal bootstrap
must find the exact verified cached archives. An unexpected bootstrap download
request is a setup assumption failure, never permission to change pins or build
LLVM locally. No native stage1/stage2 artifacts are reused from the older
assertions-enabled package. Both partitioning defaults remain off while building
the new compiler/native std. The profile/source-path change is recorded and is
not a partitioning performance claim.

Later stage admission adds its recorded allocation allowance to the8GiB floor;
packaging also checks actual remaining component sizes. During a running child,
the supervisor samples capacity every5 seconds and requests SIGINT below9GiB
only after revalidating its exact created process session and descendant group.
It always waits for that child, including a receipt-write failure. It never
signals a process by name or controls a peer. Other sessions can still consume
space; a shared-host observation cannot guarantee a physically reserved floor.

Failures and partial outputs stay at their original paths. A failed command can
use a new explicit attempt only if its unchanged preconditions still hold. A
partially created source, committed source or first-package directory is never
overwritten automatically; recovery requires a separately reviewed continuation
or new plan. No test or workload is run by the source-only preparation step.
