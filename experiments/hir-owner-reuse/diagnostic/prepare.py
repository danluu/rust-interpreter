#!/usr/bin/env python3
"""Prepare source-bound reason instrumentation, without executing any compiler."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GATE = ROOT.parent / 'candidate/owner_cache/input.rs'


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare() -> None:
    patch = json.loads((ROOT.parent / 'patch.json').read_text())
    source = GATE.read_bytes()
    expected = patch['candidate_inputs']['candidate/owner_cache/input.rs']
    if digest(source) != expected:
        raise ValueError('gate differs from the reviewed compiler patch input')
    # This is instrumentation of the exact frozen source, not a source-code coverage
    # heuristic. No token in the reviewed gate's literals/comments matches these
    # failure spellings. Refuse that shape if the gate is extended later.
    rows = []
    sites = {}
    method = ''
    for number, line in enumerate(source.decode().splitlines(keepends=True), 1):
        if line.lstrip().startswith('fn ') or line.lstrip().startswith('pub(super) fn '):
            method = line.split('fn ', 1)[1].split('(', 1)[0].split('<', 1)[0]
        if '?' in line or 'return None' in line:
            if '//' in line or '"' in line:
                # The one-line parenthesized/return branches contain harmless tag
                # literals. Only permit the exact current spellings; no generic Rust
                # lexer or approximate future transformation is claimed here.
                permitted = ('self.tag("paren")', 'self.tag("block-expr")',
                             'self.tag("initialized")', 'self.tag("expr-stmt")',
                             'self.tag("semi-stmt")', 'walk.tag("default-return")',
                             'walk.tag("typed-return")')
                if '//' in line or not any(value in line for value in permitted):
                    raise ValueError(f'unsupported instrumentation source at gate line {number}')
            sites[str(number)] = {'method': method, 'source': line.strip(),
                                  'option_propagations': line.count('?'),
                                  'explicit_rejections': line.count('return None')}
            # Every ? here propagates Option. The first inner failure wins, so
            # propagation through callers retains the causal source line.
            line = line.replace('?', f'.or_else(|| diagnostic_reject({number}))?')
            line = line.replace('return None', f'return diagnostic_reject({number})')
        rows.append(line)
    instrumentation = '''
std::thread_local! {
    static DIAGNOSTIC_REJECTION: std::cell::Cell<Option<u32>> = const { std::cell::Cell::new(None) };
}
fn diagnostic_reject<T>(line: u32) -> Option<T> {
    DIAGNOSTIC_REJECTION.with(|value| { if value.get().is_none() { value.set(Some(line)); } });
    None
}
pub(super) fn diagnostic_reset() { DIAGNOSTIC_REJECTION.with(|value| value.set(None)); }
pub(super) fn diagnostic_reason() -> Option<u32> { DIAGNOSTIC_REJECTION.with(|value| value.get()) }
'''
    generated = ROOT / 'generated'
    (generated / 'input_instrumented.rs').write_text(''.join(rows) + instrumentation)
    (generated / 'gate.snapshot').write_bytes(source)
    bindings = (f'pub const GATE_SHA256: &str = "{expected}";\n'
                f'pub const PATCH_SHA256: &str = "{patch["patch_sha256"]}";\n'
                'pub const PUBLIC_COMMIT: &str = "cea272fa356e94bd2ee2cadf376630aa0683867a";\n')
    (generated / 'binding.rs').write_text(bindings)
    records = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in
               (generated / 'input_instrumented.rs', generated / 'gate.snapshot', generated / 'binding.rs')}
    records['prepare.py'] = digest(Path(__file__).read_bytes())
    result = {'policy': 'hir-owner-input-coverage-v1', 'status': 'source-only-uncompiled-unrun',
              'gate_sha256': expected, 'patch_sha256': patch['patch_sha256'],
              'public_commit': 'cea272fa356e94bd2ee2cadf376630aa0683867a',
              'compiler_patch_base': patch['base_commit'], 'files': records,
              'reason_sites': sites, 'exact_gate_is_authoritative': True,
              'instrumented_eligibility_and_key_equality_required': True,
              'builds_or_tests_run': False}
    (ROOT / 'generated.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'gate_sha256': expected,
                      'failure_sites': len(sites)}))


if __name__ == '__main__':
    prepare()
