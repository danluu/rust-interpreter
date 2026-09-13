.text
.p2align 2
_counter_control:
    ldr q29, [x19, #48]
    mov x9, #1
    fmov d30, x9
    movi v31.2d, #0
    ins v31.d[1], x9
    add v29.2d, v29.2d, v30.2d
    add v29.2d, v29.2d, v31.2d
    str q29, [x19, #48]
    ret
