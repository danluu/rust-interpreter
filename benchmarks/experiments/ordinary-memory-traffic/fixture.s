.text
.p2align 2
.globl _ordinary_traffic_fixture
_ordinary_traffic_fixture:
    ldr x9, [x0]
    str xzr, [x0, #8]
    ldr x28, [x0, #32760]
    movz x16, #32768
    add x16, x0, x16
    ldr x9, [x16]
    movz x16, #8
    movk x16, #1, lsl #16
    add x16, x0, x16
    str xzr, [x16]
    ldr w9, [x0]
    ldr q9, [x0]
    ldr x9, [x16, #8]
    ldur x9, [x0, #8]
