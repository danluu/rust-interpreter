# Selective repair prototype qualification

The closed census admits a distinct variant of parked tool3e53b127. Move its
exact role classifier into production `register_widths::visit_full_reads` and
use that visitor for interpreter normalization. Native emission, proof/storage
admission and every initialization rule remain unchanged. The diagnostic now
calls the same production visitor; it cannot silently diverge.

Keep all checked or unreviewed u128 consumers conservative. The existing indirect
repair control now expects only the handle to be normalized; its argument and
destination addresses explicitly truncate. Add direct physical-storage checks
and full native/VM heap fallback histories that preserve dirty upper words until
a later full-width read, including invalid alignments and every budget prefix.

Run11 native/VM controls and4 role controls per profile. Then require634workspace
tests/profile with16ignored observers, the full Python suite,121strict/cache
commands and3original profiles. The latter must reconstruct code and preserve
original logical counts, and compare native bytes with the retained conservative
prototype. Only the interpreter's normalization work should change.

Any new primary still compares to adopted df4006e0, with ordinary entropy and
the same wall/CPU/A/A gate. No result from the parked primary is discarded or
used as a passing prerequisite. Full five-project and both parser histories
remain necessary for adoption after a passing primary. Main is unchanged.
