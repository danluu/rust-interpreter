# Publication scope

Publish the qualified environment/capacity implementation and its retained
successes and failures. Source qualification integrates main through ca7318da;
the immutable complete-tool result is b08f39e2. Keep later main changes intact
when merging, identify any additional compiler routing separately, and check
the resulting exporter/wrapper tests. The parser lowering and VM changes have
their complete original-output and strict-error proofs; no additional timing
claim follows from merging independent compiler options.

The repository also retains the separately qualified, explicitly ignored
offline emission observer, so its saved diagnosis is reproducible. This updates
the initial plan's proposed exclusion of that test helper: it changes no normal
runtime code or default test execution. Its one selected diagnostic test passed
four offline emissions with no executable publication or guest execution.

Do not publish the prospective32 MiB implementation as part of this change.
The current default and supported JIT arena remain16 MiB. Environment mutation,
enumeration and external execution backends remain unsupported.
