//! Allocate only narrow values whose complete live range stays in one block.
//! Phis retain stack slots. Incoming phi uses occur at predecessor exits; a
//! value used from any other block retains its original stack storage.
use super::*;

// x3's entry budget is dead after the admission check. The body never calls
// another function. x15-x17 are otherwise unused by scalar emission. x18 is
// reserved by the platform; caller state in x4-x8 and x19-x29 stays untouched.
const REGISTERS: [u32; 4] = [3, 15, 16, 17];

pub(super) fn allocate(plan: &Plan) -> Result<Vec<Option<u32>>, &'static str> {
    allocate_pool(plan, REGISTERS)
}

fn allocate_pool<const N: usize>(plan: &Plan, registers: [u32; N]) -> Result<Vec<Option<u32>>, &'static str> {
    let mut definitions = vec![None; plan.nodes.len()];
    let mut effect_positions = vec![0; plan.effects.len()];
    let mut exits = vec![0; plan.blocks.len()];
    let mut ordered = vec![Vec::new(); plan.blocks.len()];
    for (block, b) in plan.blocks.iter().enumerate() {
        if !plan.reachable[block] { continue; }
        let mut position = 0;
        for (pc, effect_position) in effect_positions.iter_mut().enumerate().take(b.end).skip(b.start) {
            for &id in &plan.computations[pc] {
                if !plan.live[id] { continue; }
                // Inputs are read at position, output written at position+1.
                // This permits reuse after the last input read, including two
                // separate computations belonging to one original bytecode PC.
                definitions[id] = Some((block, position + 1));
                ordered[block].push(id);
                position += 2;
            }
            *effect_position = position;
        }
        exits[block] = position;
    }
    let mut ends = vec![0; plan.nodes.len()];
    let mut cross_block = vec![false; plan.nodes.len()];
    let mut uses = 0usize;
    let mut use_at = |id: Id, block: usize, position: usize| -> Result<(), &'static str> {
        uses += 1;
        if uses > 250_000 { return Err("native_register_work_limit"); }
        if let Some((defined_in, definition)) = definitions[id] {
            if defined_in != block || position < definition {
                cross_block[id] = true;
            } else {
                ends[id] = ends[id].max(position);
            }
        }
        Ok(())
    };
    for (id, node) in plan.nodes.iter().enumerate() {
        if !plan.live[id] { continue; }
        if let Value::Phi(parts) = &node.value {
            for &(predecessor, part) in parts {
                use_at(part.value, predecessor, exits[predecessor])?;
            }
        } else if let Some((block, written)) = definitions[id] {
            for input in node.inputs() { use_at(input, block, written - 1)?; }
        }
    }
    for (pc, effect) in plan.effects.iter().enumerate() {
        if !plan.reachable[plan.at[pc]] { continue; }
        match effect {
            Effect::Assert { value, .. } | Effect::Switch { value, .. } | Effect::Return(value) => {
                use_at(*value, plan.at[pc], effect_positions[pc])?;
            }
            _ => {}
        }
    }
    let mut assigned = vec![None; plan.nodes.len()];
    for ids in ordered {
        let mut active: [Option<Id>; N] = [None; N];
        for id in ids {
            if matches!(plan.nodes[id].value,Value::Write{..}) || cross_block[id] || plan.nodes[id].width > 8 { continue; }
            let (_, start) = definitions[id].unwrap();
            ends[id] = ends[id].max(start);
            for slot in &mut active {
                if slot.is_some_and(|previous| ends[previous] < start) { *slot = None; }
            }
            let free = active.iter().position(Option::is_none);
            let slot = if let Some(slot) = free {
                slot
            } else {
                let (slot, previous) = active.iter().enumerate()
                    .max_by_key(|(_, previous)| ends[previous.unwrap()]).unwrap();
                let previous = previous.unwrap();
                if ends[previous] <= ends[id] { continue; }
                // Allocation precedes emission. Spilling the whole previous
                // value needs no runtime move and cannot create a partial spill.
                assigned[previous] = None;
                slot
            };
            assigned[id] = Some(registers[slot]);
            active[slot] = Some(id);
        }
    }
    Ok(assigned)
}

#[cfg(test)]
#[path="native_register_pressure.rs"]
mod pressure;
