.text
// Encoding control only. This object never supplies guest executable code.
lsr x13, x11, #62
cbz x13, linear_read
movz x14, #0x4000, lsl #48
sub x11, x11, x14
mov x17, x7
mov x15, x8
b ready_read
linear_read:
mov x17, x2
mov x15, x3
ready_read:
lsr x13, x11, #62
cbz x13, linear_write
movz x14, #0x4000, lsl #48
sub x11, x11, x14
mov x17, x7
mov x15, x8
mov x14, xzr
b ready_write
linear_write:
mov x17, x2
mov x15, x3
mov x14, x4
ready_write:
ret
