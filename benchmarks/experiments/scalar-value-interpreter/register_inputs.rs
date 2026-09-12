// A supplied argument and the explicitly initialized result register are valid
// on entry and every continuation. Retain the existing proof for other locals.
pub(crate) fn needs_initial_zeroes_with_inputs(function: &Function, inputs: &[crate::Reg]) -> bool {
    let mut entry = vec![false; function.registers];
    for &reg in inputs { entry[reg as usize] = true; }
    if !block_needs_initial_zeroes(function, &entry) { return false; }
    for op in &function.code {
        let mut needed = false;
        let mut written = [0; 2]; let mut len = 0;
        visit_registers(op, |r| needed |= !entry[r as usize], |r| {
            written[len] = r; len += 1;
        });
        if needed { return true; }
        for &r in &written[..len] { entry[r as usize] = true; }
        if matches!(op, Op::Jump {..} | Op::Switch {..} | Op::Return | Op::Trap {..}) { break; }
    }
    block_needs_initial_zeroes(function, &entry)
}
