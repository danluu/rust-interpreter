.text
.p2align 2
_pair_controls:
    ldr x9, [x11]
    ldr x10, [x11, #8]
    ldp x9, x10, [x11]
    str x9, [x12]
    str x10, [x12, #8]
    stp x9, x10, [x12]
    ldr x0, [x2, #504]
    ldr x1, [x2, #512]
    ldp x0, x1, [x2, #504]
    str xzr, [x3, #504]
    str xzr, [x3, #512]
    stp xzr, xzr, [x3, #504]
