use super::*;
fn slot(offset: usize, size: usize) -> Slot {
    Slot { offset, size }
}
fn fixture() -> (
    Function,
    Vec<Slot>,
    Vec<Slot>,
    Vec<(usize, usize)>,
    Vec<bool>,
    BTreeMap<Reg, usize>,
) {
    let old = vec![
        slot(0, 8),
        slot(8, 16),
        slot(24, 8),
        slot(24, 8),
        slot(32, 32),
        slot(64, 32),
    ];
    let new = vec![
        slot(0, 8),
        slot(8, 16),
        slot(24, 8),
        slot(32, 8),
        slot(40, 32),
        slot(40, 32),
    ];
    let f = Function {
        name: "relocation".into(),
        frame_size: 128,
        frame_align: 16,
        registers: 8,
        args: vec![slot(16, 8), slot(96, 8)],
        result: old[0],
        code: vec![
            Op::Local { dst: 0, offset: 24 },
            Op::Local { dst: 1, offset: 24 },
            Op::Local { dst: 2, offset: 96 },
            Op::Local {
                dst: 3,
                offset: 112,
            },
            Op::Return,
        ],
    };
    let shapes = old.iter().map(|s| (s.size, 8)).collect();
    (
        f,
        old,
        new,
        shapes,
        vec![false, false, true, true, true, true],
        BTreeMap::from([(0, 2), (1, 3)]),
    )
}
#[test]
fn named_origins_split_old_aliases_and_preserve_scratch_spread_and_caller_abi() {
    let (mut f, old, new, shapes, eligible, origins) = fixture();
    let r = prepare(&f, &old, &new, &shapes, &eligible, 96, 72, 2, &origins).unwrap();
    apply(&mut f, r);
    assert_eq!(f.frame_size, 112); // 24-byte local gain rounded down to 16
    assert_eq!(f.frame_align, 16);
    assert_eq!(
        f.args
            .iter()
            .map(|s| (s.offset, s.size))
            .collect::<Vec<_>>(),
        vec![(16, 8), (80, 8)]
    );
    assert!(matches!(f.code[0], Op::Local { dst: 0, offset: 24 }));
    assert!(matches!(f.code[1], Op::Local { dst: 1, offset: 32 }));
    assert!(matches!(f.code[2], Op::Local { dst: 2, offset: 80 }));
    assert!(matches!(f.code[3], Op::Local { dst: 3, offset: 96 }));
}
#[test]
fn zero_sized_return_and_deleted_promoted_origins_are_supported() {
    let (mut f, mut old, mut new, mut shapes, eligible, mut origins) = fixture();
    old[0] = slot(0, 0);
    new[0] = slot(16, 0);
    shapes[0] = (0, 16);
    f.result = old[0];
    origins.insert(7, 5); // the corresponding address was removed by promotion
    let r = prepare(&f, &old, &new, &shapes, &eligible, 96, 72, 2, &origins).unwrap();
    apply(&mut f, r);
    assert!(same(f.result, slot(16, 0)));
}
#[test]
fn failed_certificates_leave_the_original_function_unchanged() {
    for bad in 0..16 {
        let (mut f, mut old, mut new, mut shapes, mut eligible, mut origins) = fixture();
        let (mut extent, mut proposed, mut abi) = (96, 72, 2);
        match bad {
            0 => {
                origins.remove(&0);
            }
            1 => {
                origins.insert(0, 3);
                old[3].offset = 32;
            }
            2 => new[3].offset = 48,
            3 => eligible[4] = false,
            4 => shapes[4].1 = 3,
            5 => f.args[0] = slot(23, 8),
            6 => f.args[1] = slot(127, 8),
            7 => new[5].size = usize::MAX,
            8 => f.frame_align = 3,
            9 => extent = 129,
            10 => proposed = 96,
            11 => abi = 7,
            12 => f.result.offset = 8,
            13 => f.code.push(Op::Local { dst: 0, offset: 24 }),
            14 => eligible[1] = true,
            15 => f.args.push(slot(0, 0)),
            _ => unreachable!(),
        }
        let original = format!("{f:?}");
        let r = prepare(
            &f, &old, &new, &shapes, &eligible, extent, proposed, abi, &origins,
        );
        assert!(r.is_none(), "accepted mutant {bad}");
        assert_eq!(format!("{f:?}"), original);
    }
}
#[test]
fn relocation_preserves_each_addressed_byte_across_alignment_gaps() {
    // Independent address-to-byte comparison, including ABI subfields and
    // anonymous scratch, for several larger frame alignments and local gaps.
    for align in [16usize, 32, 64, 128] {
        for gap in 0..align {
            let extent = align * 4 + gap;
            let proposed = align + gap;
            let old = vec![slot(0, 8), slot(8, 8), slot(16, extent - 16)];
            let new = vec![slot(0, 8), slot(8, 8), slot(16, extent - 16)];
            // No pretend shrinking a single slot: four disjoint-lived equal
            // aggregates pack into one, leaving the ABI prefix untouched.
            let mut old = old[..2].to_vec();
            let mut new = new[..2].to_vec();
            for i in 0..4 {
                old.push(slot(16 + i * align, align));
                new.push(slot(16, align));
            }
            let extent = extent + 16;
            let proposed = proposed + 16;
            let mut f = Function {
                name: "bytes".into(),
                frame_size: extent + align * 2,
                frame_align: align,
                registers: 7,
                args: vec![old[1]],
                result: old[0],
                code: (0..6)
                    .map(|i| Op::Local {
                        dst: i as Reg,
                        offset: old[i].offset,
                    })
                    .collect(),
            };
            f.code.push(Op::Local {
                dst: 6,
                offset: extent + align,
            });
            let origins = (0..6).map(|i| (i as Reg, i)).collect();
            let shapes = old.iter().map(|s| (s.size, 8)).collect::<Vec<_>>();
            let r = prepare(
                &f,
                &old,
                &new,
                &shapes,
                &[false, false, true, true, true, true],
                extent,
                proposed,
                2,
                &origins,
            )
            .unwrap();
            let delta = f.frame_size - r.frame_size;
            assert_eq!(delta, align * 3);
            for (pc, offset) in &r.locals {
                if *pc < 6 {
                    for byte in 0..old[*pc].size {
                        assert_eq!(offset + byte, new[*pc].offset + byte);
                    }
                } else {
                    assert_eq!(*offset + delta, extent + align);
                }
            }
        }
    }
}
