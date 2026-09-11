"""Conservative admission estimate for a fresh isolated workflow history.

The per-command free-space floor must remain available after caches grow.
Archive and metadata reserves are additional headroom, not substitutes for it.
This estimate cannot prevent unrelated use of a shared volume.
"""


def required_bytes(*, cache_bytes, growth_percent, command_floor_bytes,
                   archive_reserve_bytes, evidence_reserve_bytes):
    values = [cache_bytes, growth_percent, command_floor_bytes,
              archive_reserve_bytes, evidence_reserve_bytes]
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError('space estimates must be nonnegative integer counts')
    if cache_bytes == 0 or command_floor_bytes == 0:
        raise ValueError('a fresh history needs a cache estimate and a running floor')
    cache_with_growth = (cache_bytes * (100 + growth_percent) + 99) // 100
    return dict(cache_bytes_with_allowance=cache_with_growth,
        command_floor_bytes=command_floor_bytes,
        first_archive_reserve_bytes=archive_reserve_bytes,
        metadata_and_evidence_allowance_bytes=evidence_reserve_bytes,
        minimum_free_bytes=cache_with_growth + command_floor_bytes +
            archive_reserve_bytes + evidence_reserve_bytes)


def admit(free_bytes, estimate):
    if type(free_bytes) is not int or free_bytes < 0:
        raise ValueError('available bytes must be a nonnegative integer count')
    return free_bytes >= estimate['minimum_free_bytes']
