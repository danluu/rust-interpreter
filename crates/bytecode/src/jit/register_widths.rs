//! Whole-function upper-half proof for diagnostics; code emission is unchanged.
use crate::{Binary, Function, Op, Reg, Unary};

const MAX_REGISTERS: usize = 65_536;
const MAX_PCS: usize = 65_536;
const MAX_OPERANDS: usize = 262_144;

fn narrow_width(bits: u8) -> bool { matches!(bits, 8 | 16 | 32 | 64) }

fn clears_upper_half(op: &Op, written: Reg) -> bool {
    match op {
        Op::Imm { value, .. } => *value <= u128::from(u64::MAX),
        // Validated Local addresses are represented by the 64-bit guest ABI.
        Op::Local { .. } => true,
        Op::Load { size, .. } => *size <= 8,
        Op::Cast { to, .. } => narrow_width(*to),
        Op::Unary { op, bits, .. } => narrow_width(*bits)
            || matches!(op, Unary::CountOnes | Unary::LeadingZeros | Unary::TrailingZeros),
        Op::Binary { dst, overflow, op, bits, .. } => {
            // When outputs alias, conservatively require the value definition
            // to be narrow too, although the final overflow write is Boolean.
            (written == *overflow && written != *dst) || narrow_width(*bits)
                || matches!(op, Binary::Eq | Binary::Ne | Binary::Lt | Binary::Le
                    | Binary::Gt | Binary::Ge | Binary::Cmp)
        }
        // Do not infer bounds from sampled values, Rust types, a narrow input,
        // or currently unreachable control flow. Unknown definitions decline.
        _ => false,
    }
}

/// Program validation and the VM's initial-zero register semantics are assumed.
/// Every definition participates, including unreachable code and overwrites.
/// Undefined registers conservatively remain unclassified instead of exploiting
/// initial zeroes. Memory/Call destinations are reads, never register writes.
pub(super) fn prove(function: &Function) -> Option<Vec<bool>> {
    if function.registers > MAX_REGISTERS || function.code.len() > MAX_PCS { return None; }
    let mut seen = vec![false; function.registers];
    let mut narrow = vec![true; function.registers];
    let mut operands = 0usize;
    for op in &function.code {
        let accesses = match op {
            Op::Call { args, .. } => args.len().checked_add(1)?,
            Op::CallIndirect { args, .. } => args.len().checked_add(2)?,
            _ => 7, // Conservative bound for the remaining fixed-arity ops.
        };
        operands = operands.checked_add(accesses)?;
        if operands > MAX_OPERANDS { return None; }
        let mut invalid_read = false;
        let mut invalid_write = false;
        crate::registers::visit_registers(op,
            |r| invalid_read |= r as usize >= function.registers,
            |r| {
                if let Some(is_narrow) = narrow.get_mut(r as usize) {
                    seen[r as usize] = true;
                    *is_narrow &= clears_upper_half(op, r);
                } else { invalid_write = true; }
            });
        if invalid_read || invalid_write { return None; }
    }
    Some(narrow.into_iter().zip(seen).map(|(narrow, seen)| narrow && seen).collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Slot;

    fn function(code: Vec<Op>, registers: usize) -> Function {
        Function { name:"width-proof".into(), frame_size:32, frame_align:16, registers,
            args:vec![], result:Slot {offset:0,size:0}, code }
    }
    #[test]
    fn all_definitions_including_unreachable_overwrites_must_clear_the_upper_half() {
        let f = function(vec![Op::Imm {dst:0,value:7}, Op::Local {dst:1,offset:0},
            Op::Jump {target:5}, Op::Imm {dst:0,value:1<<100},
            Op::Load {dst:1,address:2,size:16}, Op::Return], 3);
        assert_eq!(prove(&f).unwrap(), [false,false,false]);
        let f = function(vec![Op::Imm {dst:0,value:7}, Op::Load {dst:1,address:0,size:8},
            Op::Local {dst:2,offset:0}, Op::Store {address:2,src:1,size:8},
            Op::Call {function:0,args:vec![2],destination:2}, Op::Return], 3);
        assert_eq!(prove(&f).unwrap(), [true,true,true]);
    }
    #[test]
    fn narrow_arithmetic_overflow_and_comparisons_are_distinguished_from_wide_values() {
        let f = function(vec![
            Op::Binary {dst:0,overflow:1,op:Binary::Sub,a:0,b:1,bits:64,signed:true},
            Op::Binary {dst:2,overflow:3,op:Binary::Mul,a:0,b:1,bits:128,signed:false},
            Op::Binary {dst:4,overflow:4,op:Binary::Add,a:2,b:3,bits:128,signed:false},
            Op::Binary {dst:5,overflow:5,op:Binary::Cmp,a:2,b:3,bits:128,signed:true}, Op::Return], 6);
        assert_eq!(prove(&f).unwrap(), [true,true,false,true,false,true]);
        for op in [Binary::Add,Binary::Sub,Binary::Mul,Binary::Shr,Binary::RotateLeft,Binary::Cmp] {
            for bits in [8,16,32,64] { for a in [0,1,u128::MAX,1<<127] { for b in [0,1,u128::MAX] {
                let (value, _) = crate::binary(op,a,b,bits,true).unwrap();
                assert_eq!(value>>64,0);
            } } }
        }
    }
    #[test]
    fn casts_counts_and_unknown_selects_are_conservative() {
        let f = function(vec![Op::Cast {dst:0,src:0,from:128,to:64,signed:true},
            Op::Cast {dst:1,src:0,from:64,to:128,signed:true},
            Op::Unary {dst:2,src:1,op:Unary::CountOnes,bits:128},
            Op::Unary {dst:3,src:1,op:Unary::Not,bits:128},
            Op::Select {dst:4,condition:0,yes:0,no:2},Op::Jump {target:0}], 5);
        assert_eq!(prove(&f).unwrap(), [true,false,true,false,false]);
    }
    #[test]
    fn register_operand_and_size_bounds_decline_without_indexing_invalid_storage() {
        for op in [Op::Imm {dst:4,value:0},Op::Load {dst:0,address:4,size:8}] {
            assert!(prove(&function(vec![op],4)).is_none());
        }
        assert!(prove(&function(vec![],MAX_REGISTERS+1)).is_none());
        assert!(prove(&function(vec![Op::Return;MAX_PCS+1],0)).is_none());
        assert!(prove(&function(vec![Op::Call {function:0,args:vec![0;MAX_OPERANDS],destination:0}],1)).is_none());
    }
}
