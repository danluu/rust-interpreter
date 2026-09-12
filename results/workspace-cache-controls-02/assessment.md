# Explicit workspace cache placement

The launcher now accepts an existing cache parent, creates an ownership-marked
namespace for this checkout, and retains tool/selection separation and invocation
locking. Default cache paths stay unchanged. Tools and std MIR metadata stay local.
Unknown directories, altered markers and replacement symlinks are refused.

All 15 targeted Python tests pass. Routing tests use controlled Cargo/VM responses
and exercise actual file locks, including holding the lock through VM execution.
The test exposed an existing unclosed lock descriptor; ExitStack now closes it
on every return and exception. The final run emits no ResourceWarning.

These checks qualify the launcher control path. They do not claim a real build
or a speed improvement on another filesystem. The constant-folding screen can
place all four fresh mode caches on a supplied existing directory while keeping
raw evidence in this repository. The compiler prototype remains off main.
