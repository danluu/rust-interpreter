# Reader audit 03: failed

The Reader03 run passed, but its independent verifier tried to decode a Python source file as JSON. The verifier child exited with status 1 and produced no verification report. This directory preserves its complete source, raw output and process record. No compiler ran and no files were retired.

The correction uses a raw source hash check in a separate auditor04; it does not rerun or rewrite Reader03. This failure is not a performance measurement.
