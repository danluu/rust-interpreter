# Reuse one file stat during saved standard-library metadata validation

`std_mir_readmission.validate` previously queried each artifact twice: once to check that it was a regular file and again to obtain its saved stamp. On CPython 3.14 POSIX, it now uses the same stat result for both checks. Other runtimes retain the original implementation. Content verification and readmission receipt validation are unchanged.

The fixed comparison exercised the actual public validator on two immutable synthetic trees with the retained 26-artifact filename layout. Each case used 20 balanced baseline/candidate pairs. All 16 preset performance and process-resource checks passed.

| Validation route | Component CPU ratio | Median paired CPU change | Faster pairs |
| --- | ---: | ---: | ---: |
| Matching saved stamps | 0.767485 | -32.5 microseconds | 20/20 |
| Reuse an existing device readmission receipt | 0.860640 | -32.0 microseconds | 20/20 |

These are component measurements on small synthetic files. They do not establish a whole-build, full-export, cold-filesystem, or unknown-holdout speedup.

Correctness passed 48 test executions: the same twelve semantic tests on both source versions under actual CPython 3.14 and 3.9.6. Coverage includes native stat errors, transient failures, symlinks, nonregular files, error precedence, complete content verification, and receipt reuse. Fixture preparation called the original validator three times. All 184 timing children settled, and source, fixtures, loaded dependencies, and warmed bytecode remained unchanged. Independent review verified the raw results.

[Evidence and reproduction protocol](evidence/README.md) retain the frozen decision, exact code and input bindings, complete raw stage records, and independent audits. [Integration verification](integration-01.json) confirms that all 189 measured candidate Python sources were byte-identical when applied to the publication base; intervening upstream commits changed none of those sources.
