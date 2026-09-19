# Status

The N overlay01 default-discovery correctness phase passed once: two macro dylib builds and eighteen real caller commands, with all 20 children closed at their expected return codes. All nine stock/candidate caller pairs matched the required stable diagnostics, including success, error, panic, stale-handle and recovery cases.

Actual result SHA: 129e8818d8a2505139a147fb0f3c2d6593a049c0e8c7cfc9989798caf10a3a42. Execution SHA: fb525fb1ee530f706e2eef523c9db351db925e40222fd78cd0431981ec012893. Parent 24718 released its canonical lock at 1789824581.7055528. No retries, explicit signals or observation errors occurred.

Independent saved readback SHA: 433379113642b537b47532a048f889433d3c0309dc4c5062053437783f89800c. It reconstructed all 20 commands and raw diagnostic results, rehashed all 33 frozen input rows and the actual N04 prerequisite, and checked full unchanged N runtime membership and bytes (63 files, two declared links, 564,106,543 logical file bytes). Both overlays retained exactly eight owned files, 104 declared links and fourteen directories in total. The original 94 result files, source tree and complete 34-file WORK tree remained unchanged; all six built artifacts were rehashed.

Each macro build used its matching explicit overlay sysroot while omitting direct proc_macro and literal extern selections and dependency search overrides. Its actual dep-info selected all four matching overlay proc_macro/literal metadata and library files. Opposite-arm and original client/literal artifacts were excluded. Successful callers selected the matching newly built macro dylib. The N compiler server itself remained unchanged.

The prerequisite is the independently verified N04 correctness run: its candidate executed 13 native Arena/Interner tests, while stock had zero tests and only compiler/loader smoke. Overlay01 did not rerun those tests. All binary and source associations remain explicit in prerequisite.json and its before/after observations.

This capsule contains the full source tree, all actual result/raw files, every current source input, prerequisite proof records, successful dep-info, reviews and the independent readback. Large N runtime and WORK binary payloads are recorded by original path, identity and verified SHA-256 in external-artifacts.json. No portable reconstruction of those binaries is claimed. Prior N04 source/proof publication is referenced by its exact manifest SHA. Every copied payload has a fresh independent destination identity, and original files remain untouched.

This qualifies the tested external N clients and finite default-discovery cases. It does not qualify a full compiler distribution, runtime composition, builtin quote optimization, application holdouts or performance. The existing 16/9/8 resource policy was used unchanged; RSS/swap allowance is unmeasured and the aggregate output limit is sampled. The readback and publication ran no compiler or test commands. manifest.json has no self-row.
