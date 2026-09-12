# Token allocation-limit mismatch

The first fre catalog controller omitted the existing reference's explicit
150,000-allocation limit. It used the default 100,000 and trapped in the
exhaustive test's generate() helper. Older/newer exporters and runtimes reproduced
the same failure under that incorrect limit. Those controls did not establish a
lowering defect. The diagnostic stack and original workflow receipt exposed the
configuration mistake. Preserve the failed run and this correction.

Propagate the independently recorded allocation limit to both Cargo-launched and
saved VM commands. Complete the qualification at 150,000 using the exact owned
previous export cache and source state, then ordinary/fresh/prepared comparisons
with controlled entropy. Verify all native assertions and original source
restoration. The earlier source is already strictly checked; reusing its own
nonincremental cache avoids another cold dependency cache. The cache is private
to the terminal failed run and protected by the normal invocation lock. Admit
this correction at the existing 8 GiB child floor; the larger fresh-cache floor
still applies to new cold exports. Preserve prior bytecode before any re-export;
reuse its immutable saved copy if the corrected launch selects identical bytes.
No timing comparison or guest semantic change is involved.
