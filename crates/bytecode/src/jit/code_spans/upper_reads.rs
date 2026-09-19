//! Typed diagnostic of upper words with no full-width consumer. No emission changes.
use super::*;
use serde_json::json;

const MAX_REGISTERS: usize = 65_536;
const MAX_PCS: usize = 65_536;
const MAX_OPERANDS: usize = 262_144;

fn prove(f: &Function) -> Option<Vec<bool>> { prove_with_budget(f, MAX_OPERANDS) }

fn narrow(bits: u8) -> bool { matches!(bits, 8 | 16 | 32 | 64) }

fn prove_with_budget(f: &Function, budget: usize) -> Option<Vec<bool>> {
    if usize::BITS != 64 || f.registers > MAX_REGISTERS || f.code.len() > MAX_PCS { return None; }
    let mut seen = vec![false; f.registers];
    let mut full = vec![false; f.registers];
    let mut used = 0usize;
    for op in &f.code {
        let mut valid = true;
        crate::registers::visit_registers(op, |r| {
            used = used.saturating_add(1);
            valid &= (r as usize) < f.registers;
        }, |_| {});
        let mut valid_writes = true;
        crate::registers::visit_registers(op, |_| {}, |r| {
            used = used.saturating_add(1);
            valid_writes &= (r as usize) < f.registers;
        });
        if !valid || !valid_writes || used > budget { return None; }
        let mut read = |r: Reg, high: bool| {
            seen[r as usize] = true;
            full[r as usize] |= high;
        };
        // These consumers explicitly truncate in the VM. Every role counts:
        // a register that is both an address and a wide value remains full.
        match op {
            Op::Load { address, .. } => read(*address, false),
            Op::Store { address, src, size } => {
                read(*address, false); read(*src, *size > 8);
            }
            Op::Copy { dst, src, .. } => { read(*dst, false); read(*src, false); }
            Op::CopyDynamic { dst, src, size } => {
                read(*dst, false); read(*src, false); read(*size, false);
            }
            Op::FillBytes { address, value, size } => {
                read(*address, false); read(*value, false); read(*size, false);
            }
            Op::CompareBytes { left, right, size, .. } => {
                read(*left, false); read(*right, false); read(*size, false);
            }
            Op::Call { args, destination, .. } => {
                read(*destination, false); for &r in args { read(r, false); }
            }
            Op::CallIndirect { callee, args, destination, .. } => {
                // The VM rejects high bits in a function handle before calling.
                read(*callee, true); read(*destination, false);
                for &r in args { read(r, false); }
            }
            // binary() masks both operands and the shift count; unary masks
            // before dispatch; signed/unsigned casts first use the from width.
            Op::Binary { a, b, bits, .. } if narrow(*bits) => {
                read(*a, false); read(*b, false);
            }
            Op::Unary { src, bits, .. } if narrow(*bits) => read(*src, false),
            Op::Cast { src, from, .. } if narrow(*from) => read(*src, false),
            // Includes assertions, switches, conditions, wide/unknown arithmetic and all
            // runtime builtins. Unknown/new consumers cannot become low-only.
            _ => crate::registers::visit_registers(op, |r| read(r, true), |_| {}),
        }
    }
    Some(seen.into_iter().zip(full).map(|(seen, full)| seen && !full).collect())
}

fn fixture(code: Vec<Op>, registers: usize) -> Function {
    Function { name: "upper-read proof".into(), frame_size: 32, frame_align: 16,
        registers, args: vec![], result: crate::Slot { offset: 0, size: 0 }, code }
}

#[test]
fn upper_read_alias_roles_retain_wide_store_values() {
    for size in [0, 1, 8, 9, 16] {
        let f = fixture(vec![Op::Store { address: 0, src: 0, size }], 1);
        assert_eq!(prove(&f).unwrap(), [size <= 8]);
    }
    let f = fixture(vec![Op::CopyDynamic { dst: 0, src: 1, size: 2 },
        Op::FillBytes { address: 0, value: 3, size: 2 },
        Op::CompareBytes { dst: 4, left: 0, right: 1, size: 2 }], 5);
    assert_eq!(prove(&f).unwrap(), [true, true, true, true, false]);
}

#[test]
fn upper_read_unreachable_assertions_and_control_uses_stay_full() {
    for op in [Op::Assert { value: 0, expected: false, message: "full".into() },
        Op::Switch { value: 0, cases: vec![(0, 0)], otherwise: 0 },
        Op::Select { dst: 1, condition: 0, yes: 0, no: 0 }] {
        let f = fixture(vec![Op::Copy { dst: 0, src: 0, size: 0 }, Op::Return, op], 2);
        assert_eq!(prove(&f).unwrap(), [false, false]);
    }
}

#[test]
fn upper_read_indirect_handles_keep_their_high_bit_validation() {
    let f = fixture(vec![Op::CallIndirect { callee: 0, args: vec![0, 1],
        arg_sizes: vec![8, 8], destination: 2, result_size: 0 }], 3);
    assert_eq!(prove(&f).unwrap(), [false, true, true]);
    let f = fixture(vec![Op::Call { function: 0, args: vec![0], destination: 0 }], 1);
    assert_eq!(prove(&f).unwrap(), [true]);
}

#[test]
fn upper_read_proof_does_not_assume_zero_or_even_narrow_definitions() {
    let f = fixture(vec![Op::Load { dst: 1, address: 0, size: 16 },
        Op::Imm { dst: 0, value: u128::MAX }, Op::Store { address: 0, src: 1, size: 8 }], 3);
    assert_eq!(prove(&f).unwrap(), [true, true, false]);
    // A later full-width observation invalidates the classification, irrespective
    // of zero-producing definitions or a preceding low-only use.
    let f = fixture(vec![Op::Imm { dst: 0, value: 0 },
        Op::Load { dst: 1, address: 0, size: 0 },
        Op::Assert { value: 0, expected: false, message: "full".into() }], 2);
    assert_eq!(prove(&f).unwrap(), [false, false]);
}

#[test]
fn upper_read_other_consumers_are_conservatively_full_width() {
    let f = fixture(vec![Op::Allocate { dst: 2, size: 0, align: 1, zeroed: true },
        Op::Copy { dst: 0, src: 1, size: 0 }], 3);
    assert_eq!(prove(&f).unwrap(), [false, false, false]);
    let f = fixture(vec![Op::Cast { dst: 0, src: 1, from: 128, to: 8, signed: false }], 2);
    assert_eq!(prove(&f).unwrap(), [false, false]);
}

#[test]
fn upper_read_masked_widths_do_not_erase_full_width_uses() {
    for bits in [8, 16, 32, 64, 128] {
        let f = fixture(vec![Op::Binary { dst: 2, overflow: 3, op: crate::Binary::Add,
            a: 0, b: 1, bits, signed: true },
            Op::Unary { dst: 4, src: 0, op: crate::Unary::Not, bits },
            Op::Cast { dst: 5, src: 1, from: bits, to: 128, signed: true }], 6);
        assert_eq!(prove(&f).unwrap(), [bits < 128, bits < 128, false, false, false, false]);
        let mut f = f;
        f.code.push(Op::Assert { value: 0, expected: false, message: "full".into() });
        assert!(!prove(&f).unwrap()[0]);
    }
}

#[test]
fn upper_read_actual_integer_semantics_ignore_poisoned_high_bits() {
    use crate::Binary::*;
    let operations = [Add, Sub, Mul, Div, Rem, And, Or, Xor, Shl, Shr, Eq, Ne,
        Lt, Le, Gt, Ge, Cmp, RotateLeft, RotateRight];
    for bits in [8, 16, 32, 64] { for signed in [false, true] {
        for a in [0, 1, 127, 1u128 << 63, u64::MAX as u128] {
            for b in [0, 1, 63, 64, u64::MAX as u128] {
                for op in operations {
                    let expected = crate::binary(op, a, b, bits, signed);
                    let actual = crate::binary(op, a | (u128::MAX << 64), b | (1u128 << 127), bits, signed);
                    assert_eq!(actual, expected, "{op:?} bits={bits} signed={signed} a={a} b={b}");
                }
                assert_eq!(crate::signed(a, bits), crate::signed(a | (u128::MAX << 64), bits));
            }
        }
    } }
}

#[test]
fn upper_read_bounds_and_malformed_operands_decline_completely() {
    let f = fixture(vec![Op::Copy { dst: 0, src: 0, size: 0 }], 1);
    assert!(prove_with_budget(&f, 1).is_none());
    assert_eq!(prove_with_budget(&f, 2).unwrap(), [true]);
    assert!(prove(&fixture(vec![Op::Load { dst: 1, address: 0, size: 0 }], 1)).is_none());
    assert!(prove(&fixture(vec![Op::Load { dst: 0, address: 1, size: 0 }], 1)).is_none());
    assert!(prove(&fixture(vec![], MAX_REGISTERS + 1)).is_none());
    assert!(prove(&fixture(vec![Op::Return; MAX_PCS + 1], 0)).is_none());
}

#[test]
#[ignore = "Requires a retained validated program; emits only diagnostic JSON"]
fn observe_saved_upper_reads() {
    let bytes = std::fs::read(std::env::var("UPPER_READ_ARTIFACT").unwrap()).unwrap();
    assert!(bytes.len() <= 128 * 1024 * 1024);
    let program: Program = bincode::deserialize(&bytes).unwrap();
    crate::validate(&program).unwrap();
    assert!(program.functions.len() <= 100_000);
    let functions: Vec<_> = program.functions.iter().enumerate().map(|(id, f)| {
        let proof = prove(f);
        json!({"function": id, "name": f.name, "registers": f.registers,
            "declined": proof.is_none(), "low_only": proof.map(|p| p.into_iter().enumerate()
                .filter_map(|(r, low)| low.then_some(r)).collect::<Vec<_>>())})
    }).collect();
    let output = std::fs::OpenOptions::new().write(true).create_new(true)
        .open(std::env::var("UPPER_READ_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(output, &json!({"status": "passed", "functions": functions,
        "artifact_sha256": format!("{:x}", Sha256::digest(&bytes)),
        "guest_commands": 0, "executable_code_publications": 0,
        "production_runtime_changes": 0})).unwrap();
}
