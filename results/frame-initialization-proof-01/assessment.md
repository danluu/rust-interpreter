# Conservative frame proof: insufficient sampled coverage

The diagnostic passes 22 tests in debug and release, including 12 new proof
tests and an independent path/byte-mask oracle over 29,282 small programs.
It admits 49 of 278 functions and 31 of 416 direct call sites in the unchanged
es8 artifact. No guest execution, bytecode transformation or runtime change was
made. The source and artifact hashes, build settings and four terminal commands
are retained in the linked receipts.

The existing typed arena attribution reconciles all 1,135 clearing samples as
guest-frame memory, with zero register-array clearing samples. Matching exact
sampled PCs to the proof covers only **3 samples**: 0.264% of clearing and
0.039% of all 7,662 thread samples. This already overstates what can be removed
because alignment padding must remain cleared. The runtime elision proposal
does not proceed to a performance screen.

Of the remaining clearing samples, 1,064 encounter an unknown memory effect
before full frame initialization, 63 an unknown-pointer read, four a local
read before a proven write, and one an unproven call argument source. The hot
iterator wrappers call other functions early. Assuming their callees cannot
observe the caller's unwritten bytes would weaken the VM's aliasing semantics.
More analysis is possible, but this result does not justify implementing it now.

The next candidate keeps every byte initialized and specializes the clearing
code itself. Inspecting these typed call layouts finds 1,041 clearing samples
at sites whose caller alignment proves a constant total extent of at most 256
bytes, including padding. This is 13.59% of all samples and is enough opportunity
to test a bounded sequence of stores in place of the loop. It remains a sampled
opportunity, not an expected or measured speedup. A separate source change,
correctness qualification and paired performance screen are required.
