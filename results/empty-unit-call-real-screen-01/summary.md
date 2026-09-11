# Empty unit-call removal: crossed bytecode and VM runtime screen

The new bytecode improves the complete eighteen-test folded-trie execution on both VM binaries. Other workflows are mixed. This screen times execution of retained original-test artifacts; it is not edited-command or whole-application qualification.

The compiler removes only proved direct calls to exactly Return/unit-result bodies, after existing opt-in leaf expansion. Argument evaluation and function identities remain. Every function keeps its previous frame size and register count. All 106 bytecode tests pass, including aliases, indirect calls, failure paths, proof resets, branch remapping and exact transformed instruction budgets.

Both VM executables are retained because the compiler-only source edit changed the linked VM binary as well. Both old and new bytecode are executed on both VMs, six times per cell with alternating order. Virtual instruction counts, JIT instruction/entry counts, generated-code size and peak guest memory agree between VMs for each fixed artifact; timings may differ.

| Workflow | Removed executed calls | Bytecode change on baseline VM (ms; wins) | Bytecode change on candidate VM (ms; wins) | Complete-build runtime change (ms; wins) |
|---|---:|---:|---:|---:|
| fre-folded-literal-trie | 1,549,104 | -38.341; 6/6 | -24.270; 5/6 | -51.485; 5/6 |
| fre-word64 | 162,136 | +2.279; 2/6 | +6.924; 3/6 | +25.225; 2/6 |
| fre-word64-inline8 | 162,136 | -2.522; 6/6 | -1.159; 4/6 | -3.743; 5/6 |
| pgrust-sha1-inline8 | 81 | -2.562; 4/6 | +1.451; 1/6 | -5.795; 5/6 |

Negative changes favor the new bytecode/build. “Complete-build runtime” compares the old artifact on the old VM with the new artifact on the new VM; it still excludes compilation and launching through Cargo. Medians of different contrasts do not add. No outliers are removed.

The SHA-1 trace loses only 81 executed calls, so its small timing differences are weak evidence for this pass. Word64 loses 162,136 calls but has mixed bytecode results and a 25 ms complete-build runtime regression. Preserve those results through the complete-command gate rather than treating every runtime win as an optimization gain.

Profiles are separate diagnostic executions, outside the timing samples. All artifacts, pair orders, fixed-VM and fixed-bytecode contrasts, raw command logs and hashes are retained in summary.json and the referenced raw directory.

[Prior identical-tool calibration](../identical-tools-aa-e2e-01/summary.md), [structural call inspection](../call-simplification-inspection-01/summary.md).
