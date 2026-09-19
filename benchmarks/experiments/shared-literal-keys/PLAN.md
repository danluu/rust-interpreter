# Share immutable normalized function hashing across current-request workers

The literal primary05 fails its unchanged wall gate (ratio0.969685 plus
A/A0.032002). Preserve it; do not retry. Actual phase evidence assigns10.278ms
per-worker median to keys versus7.103ms to misses. Cache only normalized Function
hashes and logical serialized lengths in the private immutable ValidatedProgram.
OnceLock cells compute a demanded body once across two workers. All current
callee/scalar/context inputs remain outside this cache. Each new Program owns a
fresh cache; trusted history/native/guest ownership stays thread-local.

Bound vector storage to4MiB and65536functions; failed allocation/oversize cache
uses uncached hashing. Memoize failed body-size admission too. New v2 key domain
separates the digest composition; charge full normalized preimage plus current
outer inputs against4MiB, including framing/domain overhead. This is conservative
relative to the old inline preimage, never an expanded admission. Cache data cannot
be externally supplied or paired with a different validated owner. No native or
guest pointer lives in the cache. Normal defaults and strict Rust checking remain.

Five new controls cover two concurrent readers/one computation, cached/uncached
identity, exact logical admission boundary, mismatched owner rejection, current
callee/options changes and oversized storage/body failure. Then existing36template
and3literal-policy controls/profile,31parameterization-only controls; fullworkspace
qualification, verified actual1824parserinvocations, phase attribution and only
then a materially changed end-to-end primary. No adoption from phase savings.
Sharedlock45s,two workers,samebuildtarget neverclean. Admissionmax(14GiB,
8GiB+2*allocated target),8GiB perchild. No subagents/goals/peerprocess actions.
