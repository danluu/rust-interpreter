# Direct native operands: primary rejected

All 154 token commands pass their expected outcomes, including all 12 original
tests, wrong edits and compiled restoration. The primary performance gate
fails: paired wall changes +0.78% and CPU +0.06% versus adopted main, with
4.84% wall and 2.25% CPU A/A envelopes. These small changes establish neither
a useful improvement nor a meaningful regression. The separate short screen's
5.49% wall improvement did not carry into the full history.

Keep the runtime on its experimental branch. Folded, pgrust, private rg-aot
and Nushell were not started, as the frozen primary-first protocol requires.
No case will be repeated to seek acceptance; no screen pairs enter this result.
The fixed-anchor improvement of 17.84% includes already adopted work and
does not rescue the failed incremental gate. Candidate/ordinary native wall
ratio is 1.773; candidate/line-tables native is 2.027.

Median VM execution stages are 3.016 s baseline and 3.032 s candidate. These
separate stage medians do not add up to paired complete-command effects.
The two dominant tests also show little descriptive difference. The smaller
emitted code observed during qualification was not sufficient evidence of an
end-to-end gain.

The controller ended normally after the failed gate. Final verification
rechecks all 101 controller and 1,573 case frozen inputs and the restored fre
working tree. Minimum recorded free space was 24,557,899,776 bytes. The other
cases consumed no new benchmark caches. Original raw records remain local;
the report independently rehashes its inputs and recomputes the frozen gate.

Next: qualify a post-execution operation map for the adopted runtime, then
attribute fresh same-process native samples to bytecode operations and explicit
entry/exit/flush machinery. Preserve an unassigned category and distinguish
sampled time from static code size. The separate bounded reuse-miss observer
remains a planned frontend diagnostic. Do not expand into a memory-model or
allocator rewrite without evidence that its targeted work dominates.

[Token measurements](../direct-operands-edit-token-01/stage-assessment.md),
[frozen protocol](../../benchmarks/experiments/direct-operands/FULL.md),
[final audit](final-audit.json).
