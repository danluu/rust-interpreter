# Four bounded stock-source derivation controls

Source-only harness copied from the passed five platform controls, selecting only native02 stock_source.py, test_stock_source.py and the exact immutable compiler main.rs. Positive control compares all retained original bytes after removing exactly line4; negatives reject missing/duplicated expectation and changed main body. No compiler/provider call, fixture creation outside the owned temporary directory, process spawning or signaling is permitted.

One pure unittest child, canonical600, 16/9/8 admission, 120-second alarm/60-second CPU, 256KiB per file, cumulative writable-name limits and 2MiB retained output. No test or preparer has run yet.
