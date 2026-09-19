"""Derive the private direct-rustc wrapper from the immutable Cargo binary source.

Cargo supplies intentionally unused extern crates; the direct wrapper supplies
only its used rustc_driver pair. Remove precisely the Cargo expectation line.
Every other byte, including the allocator override and main body, is retained.
"""
import hashlib
from pathlib import Path

ORIGINAL_SHA256 = 'bfa21d3eced1a7ae4de80cb17e7f8840be640bfdfa96bff32fd6c63282d2c2ab'
DERIVED_SHA256 = '2830149bab94db375ec164229320f060096bd5c1ba2576045148bfc090fdcd68'
EXPECTATION = b'#![expect(unused_crate_dependencies)]\n'


def derive(raw, source, destination):
    if not isinstance(raw, bytes) or len(raw) != 2128 or hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA256:
        raise ValueError('exact immutable Cargo main bytes required')
    if raw.count(EXPECTATION) != 1 or raw.splitlines(keepends=True)[3] != EXPECTATION:
        raise ValueError('exact sole Cargo-specific expectation line required')
    derived = raw.replace(EXPECTATION, b'', 1)
    if hashlib.sha256(derived).hexdigest() != DERIVED_SHA256:
        raise ValueError('unexpected derived stock main')
    return derived, dict(source=str(Path(source)), original_sha256=ORIGINAL_SHA256,
        original_size=len(raw), destination=str(Path(destination)), derived_sha256=DERIVED_SHA256,
        derived_size=len(derived), removed_line=4, removed_bytes=EXPECTATION.decode(),
        policy='remove-exact-cargo-unused-crate-expectation-v1')
