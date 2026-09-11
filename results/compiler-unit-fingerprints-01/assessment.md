# Nu-protocol unit configuration in completed histories

The completed Nushell interface qualification left **three nu-protocol
fingerprints in each history**: native, independent Cargo check, baseline JIT
and candidate JIT. Each has ordinary-library configurations with `os,os_pipe`
and `default,os,os_pipe`, plus the default-feature test target.

Native/check units recorded the repository's `-Ctarget-cpu=apple-m1` flag.
Custom target units recorded the same flag; their host library recorded no
rustflags. Profile hashes and target-context hashes also differ. The hashes are
preserved as opaque evidence, not interpreted as particular optimization levels.

This read-only inventory used twelve files from the completed qualification's
isolated targets. It started no compiler and changed no project source. The
[complete fingerprints, paths and hashes](summary.json) link to the qualified
input report.

These files describe cached configurations across a completed history, not which
units executed on each edit or their time. In conjunction with the older Cargo
profile, they justify inspecting current unit timelines and actual command/profile
settings. They do not justify treating three named units as duplicate work that
only the custom backend created, or assuming that removing `--target` removes it.
