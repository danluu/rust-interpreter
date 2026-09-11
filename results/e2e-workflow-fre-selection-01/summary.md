# Production edits and three existing fre codec tests

Five cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production encoding. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Selection follows the edit: unsigned encoding, signed decoding, both roundtrips, resource/error cases, then all three tests. Each mode runs the same selection at each state.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.308 | 6.618 |
| interpreter | 4.192 | 4.282 |
| jit | 4.239 | 4.184 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
