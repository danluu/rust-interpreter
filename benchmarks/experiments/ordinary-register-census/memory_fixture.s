.text
.p2align 2
.globl _ordinary_memory_fixture
_ordinary_memory_fixture:
    strb w9, [x11, #1]
    ldrb w9, [x11, #1]
    strh w10, [x12, #2]
    ldrh w10, [x12, #2]
    str w9, [x11, #4]
    ldr w9, [x11, #4]
    str x9, [x11, #8]
    ldr x9, [x11, #8]
    stp x9, x10, [x11, #16]
    ldp x9, x10, [x11, #16]
    stp x9, x10, [sp, #-16]!
    ldp x9, x10, [sp, #16]!
    stp x9, x10, [sp], #16
    ldp x9, x10, [sp], #16
