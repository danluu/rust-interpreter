# Completed-directory audit attempt

The nine focused directory-access regressions passed. Manifest preparation
completed with 243 retained source/evidence rows (2,936,721 bytes).

The saved preflight audit exited with code 1. Its completed-directory checks
passed, and it reached the later supervisor output-membership check. That check
expected `plan.json`, `status.json`, and `command.log`, but the original
supervisor also retained `supervisor.log`. The failure and all executed sources
are preserved here; no source or compiler invocation was repeated.

Audit parent 84369 observed child 85095 close. The execution record hash is
`23786949ac2f542f28aefc95f1a8d03a0ba680322cbf8dd765530c8f57ee1b42`;
stderr is `cd68e179e6c54b37d36a42ecb816693437226930112128800415d958a6a16078`.
There were no observation errors, compiler calls, provider probes, or signals.

No final independent preflight report was published. Runtime installation and
performance qualification remain pending. This audit attempt is not a build
benchmark.
