# Directory-mode fixture controls (source-only)

This successor adapts the actual passed twelve-control cache-remover harness and the actual passed runtime-adapter source-read binding. It loads only ROOT/experiments/old-compiler-directory-modes-01/{directory_modes.py,test_directory_modes.py} and the byte-identical qualified ROOT/experiments/old-compiler-partial-retirement-01/fd_remove.py.

The preparer uses AST inspection, freezes the exact test names and local import bytes, and publishes no workload. The controller runs exactly one Python child with canonical admission (600 seconds), 16 GiB entry, 9 GiB stop, and 8 GiB floor. The child has a 120-second alarm, 60-second CPU limit, 256 KiB per-file limit, at most 256 cumulative writable file names and 2,048 directory names beneath its fresh temporary directory, and a 2 MiB retained-stage limit. Local Python bytecode is refused so the admitted source is read. Nested processes, sockets, and signals are refused.

This is a resource guard for the exact reviewed fixture source, not a general security sandbox. Directory chmod and fd-relative removal are exercised only by the admitted tiny fixtures; there is no production-prefix path or cleanup authority. Temporary fixtures must be completely removed before success. Exactly ten controls are derived from the bound test source and verified in discovery, unittest enumeration, raw output and result.

The preparer only creates exact input and launch records. No control, provider probe, compiler, or real retirement is launched by preparation. The actual control launch requires separate review.
