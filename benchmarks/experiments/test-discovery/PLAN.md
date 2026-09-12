# Discover tests without a native test executable

The isolated runner currently needs a manually selected list of names. Native
listing adds code generation and linking before the custom engine can run. Add
`--list-tests --test-body` to the Cargo launcher. Obtain built-in libtest names
and attributes from the fully checked rustc context already used by lowering
audits, without generating or executing guest bytecode or a native test binary.
Publish a bounded, versioned JSON listing beside Cargo's exact selected metadata
artifact. Track discovery mode in rustc's dependency inputs, so discovery and
execution selections cannot reuse the wrong output after an edit or mode change.

List ignored and should-panic attributes explicitly, including reasons. Listing
is not test execution and does not add support for panic/unwind/thread semantics.
Reject custom harnesses and unsupported descriptor associations. Preserve Cargo
features, cfg, package and integration-target selection. An empty built-in test
target may list zero tests. Resolve full definition paths before short-name
fallback so a root test is not ambiguous merely because a nested test shares its
leaf name. Keep the existing ordinary/audit routes otherwise unchanged.

Qualify debug/release workspace tests and Python controls. Use a generated Rust
fixture with root/nested duplicate leaf names, Result tests, ignored and
should-panic tests, feature-gated tests and an integration target. Compare names
with native libtest listing; preserve classification independently. An unused
borrow error must fail before publishing a successful listing. Exercise edits,
restoration and transitions between listing and ordinary execution in the same
owned cache. Then list actual pgrust and fre targets with native name controls.
Keep two workers, bounded 45-second global-lock waits and the 8 GiB child floor.
No unchanged-build or performance claim follows from discovery qualification.

After listing is qualified, use the metadata for automatic filtered suites.
That later step must handle single/empty selections, ignored tests, explicit
unsupported semantics and the current 256-entry execution bound deliberately.
