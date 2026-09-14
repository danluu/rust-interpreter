# Compiler policy revalidation controls

All 45 focused synthetic controls passed: 13 custom-compiler, 14 runtime-compiler and 18 source-path preparation tests. The source patch is based on `0e57b2b5`; its exact bytes and five changed files are retained with the source manifest. The final preparation check now dispatches through the compiler's `revalidate` method. The legacy and runtime loaders retain their existing policy and equality checks.

The controls exercise both dispatch paths, rejection of changed selected identities and actual synthetic installed-file mutations, failure before readiness when final revalidation changes, and rejection before child operations when the runtime lacks the exact E-specific source capability. Existing source-path, loader, immutable installation and legacy tests also passed. Synthetic capture/probe functions replace compiler, Cargo and loader execution; this is not an actual runtime installation or standard-library qualification.

The archive retains the 29 source/proof inputs, their frozen copies, all 61 retained input paths and corresponding test-time snapshots, raw output and 45 exact passing test IDs, and the child command/environment/cwd/PIDs/times. The saved control launch, admission, helper and completed outer supervisor are bound. Every tar member is read back and verified.

Completed archive execution is retained beside the immutable tar using `archive-execution.json` and eight exact launch/helper/outer records. Those terminal records do not regenerate the tar. No B2 metadata, real compiler input inspection, compiler build, benchmark, CLI change, policy change or capability inference is included.
