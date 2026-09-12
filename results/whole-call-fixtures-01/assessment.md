# Strict compiler/native differentials

All 1,050 commands pass. Four fixtures, 32 boundary/random seeds, two MIR settings, two exporters and interpreter/JIT execution yield 1,024 VM executions matching fresh native output. Both uncalled invalid-type and invalid-borrow programs are rejected without publishing bytecode. Original fixtures/assertions and every artifact/log are preserved. This is correctness qualification, not performance evidence.
