The repository-default full-parser guard passes all 88 commands and all 114 original tests. Three cycles contain the original state, an intentional wrong edit, five cumulative valid production edits, and a final restoration. Native, baseline, duplicate baseline and candidate assertion outcomes agree. Within each source state the three custom artifacts and entry catalogs agree; source restores cleanly.

Candidate/baseline paired median wall ratio is 1.003183686 and child CPU ratio is 1.006435018. A/A envelopes are 2.003% wall and 2.149% CPU; the corresponding margins 1.023210340 and 1.027926756 pass the unchanged 1.05 regression limits. These small differences establish no parser speedup. Candidate/native wall ratio is 1.140227137 and CPU ratio 1.076445828.

This is the repository profile, with Cargo incremental settings left to the original project. The independent matched-incremental guard also passed. Both use two Cargo workers, two prepared custom workers, native default test threads, full strict checking, normal OS entropy and the 16 MiB JIT arena. Only the candidate enables scalar calls. These are complete changed-source command measurements.

The closure binds 6,721 frozen inputs and 263 evidence files to source b6346003. Nushell remains unstarted pending its original disk admission; no runtime adoption follows from this guard alone.
