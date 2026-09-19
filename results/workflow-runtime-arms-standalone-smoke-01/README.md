# Standalone runner deployment and help smoke

The four reviewed non-test source files were exclusively created under R/experiments/workflow-runtime-arms-01. The original R/scripts files and all prior proposal/control artifacts remain unchanged. deployment.json records complete source and destination hashes, sizes and identities.

The exact benchmark and saved-verifier help commands ran once each with -E -s -B, from R, and both closed with exit code 0 and empty stderr. The benchmark help lists all four explicit baseline/candidate runtime/std options. Both process records retain command, passed environment, parent/child PIDs, start/spawn/finish times, raw hashes and before/after source identities. No proposed code was edited during deployment.

Only argparse help was executed: no provider lookup, compiler, application, benchmark command or benchmark lock was invoked. API definitions and source-placement metadata were loaded as covered by the prior source inspection. This smoke establishes placement/import/help behavior only, not real provider or workflow qualification.
