The bounded typed census passes all four current retained profiles. At least one
1/2/4/8-byte argument is constant on 12.44% of executed direct calls in token
block, 18.87% in token exhaustive, 23.96% in folded and 14.28% in pgrust. No
function or observed direct call declined the bounds. Both bytecode and profile
inputs remain unchanged; 357 Rust tests pass in each build profile.

Token exhaustive executes 11,912,384 calls to the copy precondition helper with
constant arguments, including element size/alignment and sometimes count. Token
block has 4,699,754 constant-argument calls to the slice precondition helper and
4,301,250 to the copy precondition helper. Other hot cases include checked adds,
allocation layout checks and scan flags. Pgrust has 100,000 iterator-step calls
with a constant increment. The diagnostic uses no project or function-name rules.

These are argument-byte facts and logical call counts, not time saved, dynamic
pointee facts or proof that a callee may be replaced. Some constants are caller
location pointers and may have little optimization value. Full per-callee native
operation counts include all calls and cannot be attributed to a single argument
pattern. The compiler must derive specialization choices without profile input.

Next prototype bounded constant propagation and direct-call specialization off
main. Keep the original callee, argument/result layouts and runtime ABI; reject
unknown aliasing or exceeded bounds. A prototype needs independent differential
execution and native Rust fixture qualification before the fixed actual-source
edit screen. Retain the 10% complete token wall improvement/no CPU regression
gate. Lifetime allocation and other failed candidates remain parked.
