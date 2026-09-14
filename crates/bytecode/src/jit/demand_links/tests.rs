use super::*;

fn run(code: &platform::Code, offset: usize) -> usize {
    // SAFETY: these fixtures only branch between owned entries, write x0 and
    // return. They read no pointers and preserve the host ABI.
    let output = unsafe { code.abi_probe(offset, [0; 8]) };
    assert_eq!(output[1], 0x1357);
    assert_eq!(output[2], output[3]);
    output[0]
}

fn source() -> Vec<u32> { vec![jump(0, 1).unwrap(), 0xd2800020, 0xd65f03c0] }

#[test]
fn pending_fan_in_and_ready_backward_edges_preserve_stable_native_entries() {
    let mut links = Links::new(7, &[0, 10, 20, 30], MAX_METADATA_BYTES).unwrap();
    let mut code = platform::Code::reserve(64).unwrap();
    let before = links.charge();
    let first = links.prepare(7, 0, 0, 0,
        vec![jump(0, 2).unwrap(), jump(1, 2).unwrap(), 0xd2800020, 0xd65f03c0],
        &[(0, 10, 2), (1, 10, 2)], MAX_METADATA_BYTES - before).unwrap();
    let growth = first.additional_charge();
    assert_eq!(first.publish(&mut code).unwrap(), 0);
    assert_eq!(links.charge(), before + growth);
    assert_eq!(links.edges.len(), 2);
    assert_eq!((run(&code, 0), run(&code, 4)), (1, 1));
    let before = links.charge();
    let growing = links.prepare(7, 20, 4, 0, source(), &[(0, 10, 1)], MAX_METADATA_BYTES - before).unwrap();
    assert!(growing.additional_charge() > 0);
    drop(growing);
    assert_eq!(links.charge(), before);
    assert_eq!(links.edges.len(), 2);
    links.prepare(7, 20, 4, 0, source(), &[(0, 10, 1)], MAX_METADATA_BYTES - before).unwrap().publish(&mut code).unwrap();
    assert_eq!(links.edges.len(), 3);
    assert_eq!(run(&code, 16), 1);
    let before = links.charge();
    let second = links.prepare(7, 10, 7, 0, vec![0xd2800040, 0xd65f03c0], &[], 0).unwrap();
    assert_eq!(second.patches.len(), 3);
    assert_eq!(second.additional_charge(), 0);
    assert_eq!(second.publish(&mut code).unwrap(), 28);
    assert_eq!(links.nodes[1].head, NONE);
    assert_eq!((run(&code, 0), run(&code, 4)), (2, 2));
    assert_eq!(run(&code, 16), 2);
    let third = links.prepare(7, 30, 9, 0, source(), &[(0, 0, 1)], 0).unwrap();
    assert_eq!(third.outgoing.len(), 0);
    assert_eq!(third.publish(&mut code).unwrap(), 36);
    assert_eq!(run(&code, 36), 2);
    assert_eq!(links.charge(), before);
    assert_eq!((links.internal(0), links.internal(10), links.internal(20), links.internal(30)),
        (Some(0), Some(7), Some(4), Some(9)));
}

#[test]
fn dropped_and_refused_transactions_keep_pending_metadata_and_fallback_code() {
    let mut links = Links::new(1, &[0, 10], MAX_METADATA_BYTES).unwrap();
    let mut code = platform::Code::reserve(20).unwrap();
    let before = links.charge();
    for available in [0, std::mem::size_of::<Pending>() - 1] {
        assert!(links.prepare(1, 0, 0, 0, source(), &[(0, 10, 1)], available).is_err());
        assert_eq!(links.charge(), before);
        assert!(links.edges.is_empty() && links.internal(0).is_none());
    }
    let first = links.prepare(1, 0, 0, 0, source(), &[(0, 10, 1)], std::mem::size_of::<Pending>()).unwrap();
    assert_eq!(first.additional_charge(), std::mem::size_of::<Pending>());
    drop(first);
    assert_eq!(links.charge(), before);
    assert!(links.edges.is_empty() && links.internal(0).is_none());
    links.prepare(1, 0, 0, 0, source(), &[(0, 10, 1)], std::mem::size_of::<Pending>()).unwrap().publish(&mut code).unwrap();
    let old_words = code.published().1.to_vec();
    let old_charge = links.charge();
    let too_large = links.prepare(1, 10, 3, 0, vec![0xd2800040, 0xd65f03c0, 0xd65f03c0], &[], 0).unwrap();
    assert!(too_large.publish(&mut code).is_err());
    assert_eq!(code.published().1, old_words);
    assert_eq!(links.charge(), old_charge);
    assert!(links.internal(10).is_none());
    assert_ne!(links.nodes[1].head, NONE);
    assert_eq!(run(&code, 0), 1);
    links.prepare(1, 10, 3, 0, vec![0xd2800040, 0xd65f03c0], &[], 0).unwrap().publish(&mut code).unwrap();
    assert_eq!(run(&code, 0), 2);
}

#[test]
fn malformed_owner_sites_and_duplicate_publication_do_not_change_link_state() {
    assert!(Links::new(1, &[2, 1], MAX_METADATA_BYTES).is_err());
    assert!(Links::new(1, &[1, 1], MAX_METADATA_BYTES).is_err());
    assert!(Links::new(1, &[0], 0).is_err());
    assert!(Links::new(1, &[], MAX_METADATA_BYTES + 1).is_err());
    let mut links = Links::new(1, &[0, 10], MAX_METADATA_BYTES).unwrap();
    let before = links.charge();
    for (function, pc, base, internal) in [(2, 0, 0, 0), (1, 1, 0, 0), (1, 0, usize::MAX, 0), (1, 0, 0, 3)] {
        assert!(links.prepare(function, pc, base, internal, source(), &[], 0).is_err());
    }
    for declarations in [vec![(3, 10, 1)], vec![(0, 10, 3)], vec![(1, 10, 2)], vec![(0, 10, 1), (0, 10, 1)]] {
        assert!(links.prepare(1, 0, 0, 0, source(), &declarations, MAX_METADATA_BYTES - before).is_err());
        assert_eq!(links.charge(), before);
        assert!(links.edges.is_empty() && links.internal(0).is_none());
    }
    let mut code = platform::Code::reserve(32).unwrap();
    links.prepare(1, 0, 0, 0, source(), &[(0, 99, 1)], 0).unwrap().publish(&mut code).unwrap();
    // An unsupported/nonleader successor keeps its VM fallback and no edge.
    assert!(links.edges.is_empty());
    assert_eq!(run(&code, 0), 1);
    let old_words = code.published().1.to_vec();
    assert!(links.prepare(1, 0, 3, 0, source(), &[], 0).is_err());
    assert_eq!(code.published().1, old_words);
}

#[test]
fn stale_or_different_arenas_refuse_before_metadata_commit() {
    let mut links = Links::new(1, &[0, 10], MAX_METADATA_BYTES).unwrap();
    let mut code = platform::Code::reserve(64).unwrap();
    links.prepare(1, 0, 0, 0, source(), &[(0, 10, 1)], MAX_METADATA_BYTES).unwrap().publish(&mut code).unwrap();
    let prepared = links.prepare(1, 10, 3, 0, vec![0xd2800040, 0xd65f03c0], &[], 0).unwrap();
    code.append(&[0xd65f03c0]).unwrap();
    let before = code.published().1.to_vec();
    assert!(prepared.publish(&mut code).is_err());
    assert_eq!(code.published().1, before);
    assert!(links.internal(10).is_none());
    let mut other = platform::Code::reserve(64).unwrap();
    other.append(&[jump(0, 1).unwrap(), 0xd2800020, 0xd65f03c0, 0xd65f03c0]).unwrap();
    let before_other = other.published().1.to_vec();
    assert!(links.prepare(1, 10, 4, 0, vec![0xd2800040, 0xd65f03c0], &[], 0).unwrap().publish(&mut other).is_err());
    assert_eq!(other.published().1, before_other);
    assert!(links.internal(10).is_none());
    assert_eq!(run(&code, 0), 1);
}

#[test]
fn self_edges_resolve_to_the_new_internal_entry_without_pending_storage() {
    let mut links = Links::new(1, &[7], MAX_METADATA_BYTES).unwrap();
    let mut code = platform::Code::reserve(16).unwrap();
    let prepared = links.prepare(1, 7, 0, 0, vec![jump(0, 0).unwrap(), 0xd65f03c0], &[(0, 7, 1)], 0).unwrap();
    assert!(prepared.outgoing.is_empty() && prepared.patches.is_empty());
    assert_eq!(prepared.additional_charge(), 0);
    prepared.publish(&mut code).unwrap();
    assert_eq!(links.internal(7), Some(0));
    assert_eq!(u32::from_le_bytes(code.published().1[..4].try_into().unwrap()), jump(0, 0).unwrap());
    // This static self-loop is deliberately not executed; VM budget/control
    // qualification belongs to the integrated demand engine.
}
