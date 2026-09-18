Four exact adopted profiles identify the parser's reduce_cold as the only
directly called function above the current 65,536-register proof bound:
102,786 registers, 140,615 operations, 9,022 saved direct calls and no scalar
returns. Its nominal register-storage weight is 14,837,364,672 bytes and its
nominal frame-storage weight is 3,360,667,934 bytes.

These are dimensions multiplied by calls, not measured clearing traffic. Fast
initialization proofs may already avoid the register clearing. Inspect the
current decision on typed validated functions before implementing any change.
Frame initialization is a separate obligation. Indirect calls and callbacks
are not attributed; scalar returns are conservatively subtracted.

All 13 inputs, four call tables and terminal evidence are closed. No new guest
execution or performance claim.
