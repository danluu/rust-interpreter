# Explicit frozen link reader (unrun)

This separate helper addresses saved audit06's link-metadata failure. The
immutable actual53 `audit_io.Access` deliberately rejects symlink ancestors for
ordinary physical reads. Audit06 also used that API for a frozen symlink beneath
the Homebrew `opt` directory alias, which cannot pass that ordinary route rule.
The completed preflight05 and failed audit06 records remain unchanged.

`FrozenLinks` accepts only the authenticated frozen `links` dictionary. Its
`verify(name)` resolves one declared link using held directory descriptors and
bounded explicit expansion. It checks the exact original leaf's seven-field
stamp, link text and resolved route. It records every current ancestor link's
identity/text and every directory's inode/type/mode, then rechecks all held routes
after the resolved target check. These ancestor observations are current audit
evidence; they do not assert that ancestors were present in the original freeze.

The first complete observation is retained independently for every declared
name. Later `verify()` or `recheck()` calls must reproduce it. A failed later
check cannot replace that baseline. The caller must keep one helper instance
for the entire audit and recheck it at the final current-input guard. No generic
filesystem alias or virtual file API is introduced.

For a regular-file endpoint, the callback receives the exact canonical resolved
path, never the alias. It must perform the existing strict frozen-file read and
return `{identity, size, sha256}`. With the unchanged qualified Access API:

```python
def strict_target_file(name):
    io.file(name)  # unchanged ordinary route, current frozen identity, full SHA/EOF
    return copy.deepcopy(io.files[name])

links = FrozenLinks(prepared['links'], read_file=strict_target_file, guard=guard)
# At both current_guard calls, replace only the former frozen-link loop:
for name in prepared['links']:
    links.verify(name)
```

Resolved directories receive metadata-only route checks, matching the old
frozen-link contract. No missing historical directory identity is invented.
Ordinary file reads, historical-copy exclusions, executor-route equations and
all other audit predicates stay with their existing strict implementations.
One final `links.recheck()` may substitute for the second complete link loop;
do not reconstruct a fresh helper instance at the final guard.

There are 24 source-only fixtures using owned temporary directories and real
symlinks. They cover relative/absolute/nested parent aliases, file and directory
targets, typed rows, frozen identity/text/resolution mismatches, dangling/cyclic
links, strict payload readback, callback-time leaf/ancestor/directory changes,
and first-observation preservation across calls. They read no provider path and
perform no process launches. They have not been imported or executed.

After review, the proposed ordinary development command is:

```
cd /Users/danluu/dev/rust-interp-semantic-reuse-20260913/experiments/runtime-frozen-link-reader-01
/opt/homebrew/bin/python3 -B -m unittest -v test_links
```

No integration source was edited. A fresh saved-audit successor must authenticate
and qualify this helper before import, preserve the failed06 attempt, and use a
fresh execution namespace. This draft authorizes no audit retry or workload.
