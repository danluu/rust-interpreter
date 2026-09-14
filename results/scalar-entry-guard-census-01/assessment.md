# Captured pointer ranges have limited present coverage

Seven static controls pass in debug and release, including 512 independently
enumerated diamond paths and both same-PC computation orders. All 245 archived
store-log bodies reconstruct exactly (111/124/10). Three commands take
22.74 seconds; closure verifies 262 input bindings. This observer
emits no executable code and changes no production policy.

The simple rule admits 7/8/1 functions. On successful prototype scalar paths,
those account for 3,372,993 / 6,816 / 1 calls. Block contains 72,635,137 read and
46,178,497 write IR occurrences, largely SipHash c_rounds. These are occurrences,
not instructions or predicted time; failed attempts are excluded.

The separately closed adopted-sample join finds only 11 transition and 32 body
samples out of 1,561 generated block samples. SipHash contributes 31 body and 11
transition samples. Exhaustive has zero transition and one body sample out of
1,231. The whole-body 43/1 counts overstate removable work and omit guard costs.
Defer native wiring of this subset alone. Main retains the adopted backend.

Inspect a broader, bounded entry-value dependency graph before a full execution
model: pure arithmetic and captured loads may form addresses, but a load can be
hoisted only if every potentially earlier external write is proved disjoint from
its checked range. Do not require disjointness from later writes: a value loaded
before an update remains captured afterward. Cross-block order, arbitrary aliases,
128-bit values, fault order, budgets and fresh frames require explicit controls.
This is a new hypothesis, not permission to replay after a committed store.
