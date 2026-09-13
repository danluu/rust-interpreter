.text
.globl _boundary_memory_encodings
_boundary_memory_encodings:
    eor v0.16b, v0.16b, v0.16b
    stp q0, q0, [x11]
    stp q0, q0, [x11, #32]
    stp q0, q0, [x11, #224]
    ldp x9, x13, [x11], #16
    stp x9, x13, [x12], #16
    ldp x9, x13, [x11, #-16]!
    stp x9, x13, [x12, #-16]!
