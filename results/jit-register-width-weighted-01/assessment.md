# Reject persistent-register width packing before code generation

The bounded proof and offline census pass 337 Rust tests in each of debug and
release (one ignored). Every potential register definition participates;
unrecognized definitions and analysis limits decline conservatively. The
diagnostic validates typed bytecode and exact profile names, operations, shapes,
intervals and counter totals. No guest instruction runs during the census.

The current restored pgrust/folded/token programs admit 90/1,048/5,457 functions,
with zero/zero/eleven declines. Packing narrow values into the existing six-register
bank adds assignments in zero/eight/27 functions. Static read coverage rises by
zero/100/366 operands. These are the current four/eighteen/twelve-test artifacts.

The separately preserved historical token/folded profiles show why that static
increase is unpromising. Against their **own exact artifacts**, the current
ranking would cover only 7,628 additional native read operands out of
10,452,870,848 (0.0000730%), and 900 out of 3,438,538,854 (0.0000262%). Native
instruction totals exactly match the original producer statistics. Seven/five
executed functions gain assignments; most additional assignments are cold.
These profiles predate the expanded token suite and current runtime changes.

Stop this candidate here. No packing emitter or performance screen is justified.
The diagnostic is retained; generated register assignments remain unchanged.
Operand counts are not machine-load counts: the existing two-register local cache
already handles some reads. Block-entry liveness also includes internal native
edges, so it is not a count of actual spills or a speedup estimate.

The next experiment will make otherwise idle persistent-bank registers available
to the existing local cache in resumable regions. It targets short-lived values
excluded by the global ranking, rather than widening that ranking's capacity.
Keep that runtime change separate and screen it before expensive real-edit
qualification. [Plan](../../benchmarks/experiments/jit-region-cache/PLAN.md).

Evidence: [static census](../jit-register-width-census-01/summary.json),
[weighted census](summary.json), [build](../jit-register-width-build-02/summary.json).
Exact raw profiles, programs, tested diagnostic binaries and receipts remain local
and are bound by the committed summaries' hashes.
