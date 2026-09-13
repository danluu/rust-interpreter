# Merged compiler-role defaults and getcwd qualification

The merged source `56e9aea9ec157c716f8cc4ab3e3f4e1c6068b532` passed the release
workspace and native getcwd controls with compiler-role separation disabled.
The workspace reported 548 passed, 10 ignored, zero failed, zero filtered, and
50 test suites. Every one of the eight compiler-role controls and four getcwd
controls passed once. The ten existing ignored tests require separately owned
external artifacts; none of the twelve required controls was ignored.

The metadata stage retained 212 complete source snapshots and 30 resolved
package inventories in 34 actual commands. The run retained 17 outer commands:
release workspace tests, standalone release build of exporter/wrapper/VM,
twelve loader inspections, exporter capability and wrapper-role probes, and
the native Python suite. The exporter capability contained no `compiler_roles`
field, and the wrapper probe returned exactly `null` followed by a newline.

Both native Python tests passed with all 33 recorded children. They preserve
the same getcwd fixture and checks used in the earlier independent qualification:
exact path bytes, errno and pointer/sentinel results, all supported NULL size
forms, interpreter/JIT agreement, default-disabled execution, wrong-path negative
controls, invalid guest buffers and invalid exporter ABI rejection. Native source,
fixture binary, bytecode, metadata, all raw outputs and child receipts are retained.

The actual public compiler is commit
`cea272fa356e94bd2ee2cadf376630aa0683867a`. Native linking uses its full sysroot;
export uses the separately qualified metadata sysroot
`bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef`.
The same exact source, registry checksum/source, compiler, prepared std, selected
SDK and loader guards surround this completed sequence and its archival pass.
SDK selection and the platform dyld-cache assumption are retained; the SDK is
not claimed to be a separately hashed hermetic distribution.

This archive includes both supervisors, all metadata and run receipts, raw
stdout/stderr, complete source snapshots and registry package source/archive
bytes. Compiler, standard-library and produced exporter/wrapper/VM binaries are
represented by exact inventories instead of copied binary payloads. Every tar
member is read back against its manifest. The earlier independent role-default
and getcwd archives are bound by their unchanged SHA-256 references and retained
summaries/manifests, without nested tar duplication. The original unexecuted
role draft remains preserved in its independent default archive.

This qualifies merged default behavior and getcwd correctness. It supplies no
split-role ABI qualification, tool publication, build-script completion, or
performance result.

Exact terminal bindings:

- Plan: `8dc9fbdffda06f3f6dc461b945f6f1673f32ae8500c6d0cd321bcfcf29d6e357`.
- Metadata receipt: `735e3115d76314948ffb5888c6416ea3c869615d409eb1a2564cf5f15288a8e7`.
- Run receipt: `a25b4c5ff26c02f382ac605d23da361d4d2a013dda57487316203c7a7e62b4d5`.
- Actual tool inventory: `67cd85e1ba9ac69ee92b675fd62bd2fa2d15cea7e0abb4cc530e519191c77a90`.
- Native results: `c8227ba3c6b688520a5b5c2719ab0ec6cdc83dfc8282f2e5dcad171d36c2e890`.
