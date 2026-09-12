Two custom suite workers reduced the full changed-source token command by
**34.3%** versus the retained one-worker custom runner, with **3.2% more CPU**.
The five paired edits pass the predeclared screen. All40 commands preserve
original assertion outcomes, deliberately wrong-edit rejection, unchanged test
source, identical paired bytecode/catalogs and source restoration.

Median edited commands: candidate5.330s, retained custom8.021s,
two-process native2.422s, serial native3.119s, check0.681s. The median paired
candidate/native ratio is**2.216**: native remains substantially faster.
This is twelve original tests, with two Cargo workers in every mode. Native
tests run in separate processes with one libtest thread each; this is not an
ordinary default-concurrency Cargo/libtest control.

The40 commands include cold original, deliberately wrong, five valid edited,
and restored-original source states across five independent caches. Only valid
edits enter the paired medians. Cold custom candidate11.006s versus retained
15.772s and concurrent native12.835s are separate observations. No unchanged
build timing enters the improvement claim. Normal OS entropy is preserved.

Proceed to the fixed folded/pgrust guards; keep one worker as default for now.
The next adoption comparison will include ordinary Cargo/libtest concurrency
as requested by the updated review. Raw records remain at the path bound in
[the compact result](summary.json); no timing trial is discarded or repeated.
