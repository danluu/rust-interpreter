# A larger local register pool has little coverage

Two structural controls pass and all 245 saved scalar bodies reconstruct exactly.
No new guest executes or hypothetical larger-pool code is published. Closure
binds 261 inputs and all command logs.

On successful block-test paths, four to eight registers reduce narrow spilled
SSA definitions by 154,304 (31,641,092 to 31,486,788) and IR operand occurrences
by 170,432 (159,652,489 to 159,482,057). Preserving the additional used registers
would add 308,608 save/restore instructions under the stated model. Eleven
registers reduce definitions by 257,936 and operands by 274,064, with 515,872
preservation instructions. These different units are not a performance model.
The exhaustive/folded opportunities are smaller still.

Do not implement a broader caller-preserved register pool on this evidence.
The dominant sparse-set, copy-precondition and vector-extension bodies gain
nothing from additional local registers. Most surviving values cross blocks
or are branch-merge phis. Extend the diagnostic breakdown before choosing
cross-block allocation or coalesced byte phis. Keep all native candidates parked.
