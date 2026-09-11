# Worker helper and serializable argument receipts

Six configurations, 48 rejection checks, sixteen parser rejection cases and
worker-count checks against 756 historical commands pass. A new positive check
serializes the argument namespace exactly as corpus plans do; duplicate detection
now uses a list. The prior helper used a non-JSON set. These historical commands
were inspected, not rerun. Actual harness integration is qualified separately.

[Exact evidence and source hashes](summary.json).
