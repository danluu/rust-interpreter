# Retire completed passing-primary compiler intermediates

The new full110-command guard uses independent cold cache namespaces. Retire only
primary04's five measured and one strict-control compiler caches, after verifying
its closed passing40-command record and two strict rejections. Keep every native
executable, bytecode/catalog snapshot, source, log, proof and frozen input.

Same exact historical launcher derivation/cross-check for the strict namespace,
benchmark/invocation locks, process/open-file checks, regular-file identity checks
and protected-hash verification as the closed primary03 retirement. Only recorded
nonexecutable compiler .o/.rlib/.rmeta/incremental files are eligible. No build target,
installed tool, previous retired namespace, source or peer cache. No signaling or
compiler/guest work.8GiB floor; complete inventory and independent closure required.
A passing result is preserved; cache retirement does not authorize its remeasurement.
