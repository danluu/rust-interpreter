# Name preflight rejects before any benchmark starts

The inherited controller accepted an optional continuation suffix, then rejected
any run name containing the substring `-continuation-`. The new experiment's
name itself contains that substring. It fails before lock/admission, source
editing, work-directory creation or any benchmark command. The raw work
directory is absent; the terminal, log, supervisor plan and qualified controller
source are bound in the summary and closure.

Replace both checks with an exact fresh-run syntax and add a regression control
covering this name and rejected resume/path suffixes. Requalify the protocol and
use fresh screen-token-02. Runtime/tool bytes, workload, schedule and gates stay
fixed. There is no performance observation to repeat or discard from this run.
