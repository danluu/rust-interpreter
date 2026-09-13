Park local-value transfer without a timing screen. All three adopted generated
code maps reconstruct byte-for-byte with transfer disabled. Enabling the
observer changes only std::fmt::write in the two token selections, saving eight
static bytes each; folded code is unchanged. The additional frequency-weighted
forwarding counts are1,792 /8 /0, with zero lost sites, zero declines and no
weighted flush/transition changes. This is too little useful coverage to justify
a complete-command experiment.

The large transferred-reference totals (324.6M /129.5M /48.0M, weighted by saved
region hits) are not avoided loads. They include the just-loaded range that the
existing emitter already remembers against the destination. Even additional
aliases rarely survive to a useful later read. The actual emitted-code and new-
forwarding comparison prevents treating those bookkeeping totals as a speedup.
Only static code/weighted-site facts are measured; none are retired-instruction
counts or latency measurements.

Both profiles pass408 bytecode-package tests, including eight new boundaries;
the initially miscounted debug result is retained and only release was resumed.
The census makes three offline emissions and zero guest executions or executable
publications. Production transfer stays disabled. Implementation and test-only
observer remain on experiment/local-value-transfer-20260913; the adopted main
runtime stays unchanged. Source at the completed census: `80252c41bc5647f507335ba328b4abc78c6c8775`.

Next refresh same-process native-PC attribution for the adopted VM's block and
exhaustive tests, using original selected artifacts and the verified owned-VM
sampler. Preserve strict process ownership, source/byte identity, explicit
unassigned samples and the separation between diagnostic samples and timings.
Choose the next guest mechanism from the new cost distribution.
