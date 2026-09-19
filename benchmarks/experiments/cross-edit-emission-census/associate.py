"""Associate original diagnostic intervals with identity masks; never predict savings."""
MASKS=['same_function_at_same_id','same_function_and_direct_layouts',
       'same_function_and_direct_callees','same_closed_direct_call_graph']
PHASES=['ordinary_emission','ordinary_regions','ordinary_liveness','ordinary_reads',
        'ordinary_fills','ordinary_call_slots','ordinary_layout','ordinary_relocations','ordinary_publication']

def associate(comparison,workers):
    functions=comparison['functions'];by_id={f['function']:f for f in functions}
    assert len(by_id)==len(functions)
    assert len({w['worker'] for w in workers})==len(workers)
    output=[]
    for worker in workers:
        observation=worker['observation'];metadata=observation['functions']
        assert len({f['function'] for f in metadata})==len(metadata)
        for f in metadata:
            identity=by_id[f['function']]
            assert identity['previous_name']==f['name']
            assert identity['previous_operations']==f['bytecode_operations']
            assert isinstance(identity['previous_sha256'],str) and len(identity['previous_sha256'])==64
            assert all(type(identity[k]) is bool for k in MASKS)
            assert type(f['ordinary_prepared']) is bool
            assert type(f['ordinary_native_entries']) is int and f['ordinary_native_entries']>=0
            assert not f['ordinary_native_entries'] or f['ordinary_prepared']
        buckets={}
        for fid,phase,interval in observation['trace']['rows']:
            assert (fid,phase) not in buckets
            assert type(interval['nanos']) is int and interval['nanos']>=0
            buckets[fid,phase]=interval['nanos']
        all_ids={f['function'] for f in metadata}
        published={f['function'] for f in metadata if f['ordinary_native_entries']>0}
        def intervals(ids):
            return {phase:sum(buckets.get((fid,phase),0) for fid in ids) for phase in PHASES}
        masks={}
        for mask in MASKS:
            selected={fid for fid in published if by_id[fid][mask]}
            masks[mask]=dict(functions=len(selected),original_phase_ns=intervals(selected))
        output.append(dict(worker=worker['worker'],observed_functions=len(all_ids),
            ordinary_published_functions=len(published),original_phase_ns=intervals(all_ids),
            no_published_entry_phase_ns=intervals(all_ids-published),candidates=masks))
    return output
