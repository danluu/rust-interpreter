# Metadata continuation after the retained linker parser rejection

The original `compiler-metadata-03` attempt executed 48 of its 50 probes and
retained `RuntimeError('unknown linker architecture grammar')`. Its actual
`ld -v` child returned zero. The six version lines include additional ARM
architectures and an `ld-classic` architecture list, and omit the search-path
sections assumed by the original parser. No compiler build ran.

This separate continuation keeps that failed receipt and every original byte
unchanged. A source-bound parser qualifies the saved linker stream with exact
version text and the original strict, lossless DYLD grammar. The controller
reconciles all 48 saved child histories and replays the actual `otool` outputs
through the loader reader without executing any completed probe again.

Only the original final Git HEAD and empty-diff probes execute. The same full
source/provider/SDK identities and byte hashes are checked before and after,
along with exact loader search state. Canonical admission remains 600 seconds
with the unchanged 24 GiB entry, 9 GiB stop and 8 GiB floor. Passing this stage
admits metadata only; compilation and native/B3/driver qualification remain
separate, unrun stages.

The saved-output controls and this two-child continuation each require review
of their exact frozen launch before execution. The original failed receipt is
not changed to passed, and the combined metadata records both histories.
