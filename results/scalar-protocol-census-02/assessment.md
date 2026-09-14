Both three-test protocol suites passed. The first saved capture matched its
complete ordinary/scalar function bytes, then failed the isolated transition
comparison: scalar successor branches are relocated only during whole-function
assembly. The failure is retained and the second capture stayed unstarted.
No guest execution or executable publication occurred.

The diagnostic fix reuses reconstructed internal-entry/fallback decisions to
relocate only recorded branch placeholders before byte comparison. A new
focused control covers compiled and interpreted successors. Saved branch bytes
are not copied into reconstructed output. All original guards remain required.
