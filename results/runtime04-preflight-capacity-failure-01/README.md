# Runtime04 preflight stopped before compiler execution

The launcher passed its original 24 GiB free-space check. After source validation
and canonical-lock admission, the controller observed 23,099,760,640 free bytes
and failed the same check. No compiler child was launched, no source-probe
directory was created, and the receipt records zero children.

The controller and supervisor closed with exit 1. The launcher observed their
terminal state and also exited with failure. This directory preserves all nine
actual files from those three closed namespaces, plus a readback of the matching
PIDs, output hashes and ordering. The exact lock-release timestamp was not recorded
and is not reconstructed. The original namespaces and packet remain unchanged.

The prepared packet is referenced by its seven actual file hashes and is already
retained in the earlier runtime04-preflight-preparation-01 publication. The
success-only saved audit was not invoked. A new attempt needs fresh namespaces;
this failure is not a passed preflight, runtime installation or timing result.
