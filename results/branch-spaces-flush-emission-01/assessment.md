# Exact emission comparison

Both adopted captures reconstruct byte-for-byte, covering all1101/1305 recorded
functions. Selector-only emission adds60,324/118,396 bytes. The composition then
removes exactly197,384/238,016 bytes belonging to successor-dead register spills,
with identities matched against the prior adopted flush census. All remaining
span lengths and PC ownership match between selector-only and composed emission;
selector changes are confined to memory operations, range guards and transitions.

Composed unprofiled code is10,960,764/13,354,888 bytes, versus11,097,824/13,474,508
adopted. This proves reconstruction and static accounting, not faster execution.
No guest benchmark or executable code publication occurred in this stage.
The first admission timed out without work; the successful outer receipt is
branch-spaces-flush-emission-admission-02. Do not repeat the completed captures.
