The exact-native-copy model passes10 controls and independently closes47849,
with55 verified bindings and both derivations recomputed. The original01 attempt
is retained as a shared-lock admission failure with no controls or analysis run.

The two captures contain9951/12006 exact three-word local eight-byte copies.
Modeled source-cache hits number382/454 static sites, covering3/3 whole-copy
samples but only2/2 actual payload-load samples (0.10%/0.14% of1933/1429).
No sample is ambiguous. Logical hits6,994,223/17,225,168 are separate whole-test
fixed-entropy observations. No guest, compiler or executable code is generated.

Park this specific narrow payload-cache design. Conservative barriers mean this
is not an upper bound for all possible memory caches, but the measured design
does not justify a runtime implementation or another end-to-end timing screen.
The larger virtual-register cache, scratch-width extension and local-copy equality
results remain separately retained; do not repeat any of them unchanged.

Source review instead identifies a possible earlier lowering opportunity:
private numeric MIR locals are already promoted to bytecode registers, whereas
references/raw-pointer locals are excluded by type and ordinary projection-use
rules. Investigate a bounded typed eligibility proof for non-address-exposed,
eight-byte pointer temporaries, preserving argument/result/call ABI exclusions,
existing numeric packing, strict Rust checking and all escaped slots. This is
not an implemented optimization; typed scope/correctness comes before timing.
