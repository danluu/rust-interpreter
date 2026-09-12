Commands after prerequisite control qualification and storage admission:

    python3 scripts/supervise_experiment.py --run-id scalar-aa-01-folded-literal-trie -- python3 benchmarks/experiments/scalar-value-workflow/workflows.py --phase aa --case folded-literal-trie
    python3 scripts/supervise_experiment.py --run-id scalar-aa-01-token-phrase -- python3 benchmarks/experiments/scalar-value-workflow/workflows.py --phase aa --case token-phrase
    python3 scripts/supervise_experiment.py --run-id scalar-e2e-01-folded-literal-trie -- python3 benchmarks/experiments/scalar-value-workflow/workflows.py --phase e2e --case folded-literal-trie
    python3 scripts/supervise_experiment.py --run-id scalar-e2e-01-token-phrase -- python3 benchmarks/experiments/scalar-value-workflow/workflows.py --phase e2e --case token-phrase

Run each only after its predecessor and supervisor are terminal and verified.
Do not queue a lock waiter during storage work. Each assessment recomputes all
paired wall/CPU ratios and artifact/control checks. Gate failure is an outcome,
not permission to discard/reorder observations or change thresholds.
