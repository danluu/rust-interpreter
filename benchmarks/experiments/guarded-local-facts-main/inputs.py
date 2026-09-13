"""Component and adoption boundaries for the prospective main integration."""
CASES = ['token', 'folded', 'pgrust', 'rg-aot', 'nushell']
VM_KEY = '317a0bf16da0f15f562ab457408ab321b12f25211f8169ec8bcd8205a3cb7dfb'
VM_SHA = 'f0e5f2ea9bbe411c7309ae7283f8040b0549759344c5f81798c1e2eae9e99d9b'


def require_complete(proof, cases):
    assert proof['status'] == 'passed' and proof['all_five_gates_passed']
    assert proof['completed_cases'] == CASES and proof['unstarted_cases'] == []
    assert (proof['commands'], proof['retained_commands'], proof['new_commands'],
            proof['repeated_commands']) == (726, 594, 132, 0)
    assert proof['final_source_and_input_audit_passed'] and proof['complete_parser_tests'] == 114
    assert len(cases) == 5 and [p['case'] for p in cases] == CASES
    for index, case in enumerate(cases):
        assert case['status'] == 'passed' and case['gate_passed'] and case['source_restored']
        assert case['commands'] == (154 if index < 3 else 132)
        assert case['candidate_control_bytecode_matches'] and case['test_source_unchanged']
        assert case['tool_keys']['candidate'] == VM_KEY


def rust_input(name):
    return name in ['Cargo.toml', 'Cargo.lock', 'rust-toolchain.toml'] or (
        name.startswith('crates/') and (name.endswith('.rs') or name.endswith('/Cargo.toml')))


def vm_input(name):
    return rust_input(name) and not name.startswith('crates/mir-export/')


def require_vm_sources(current, qualified):
    # Compare complete sets, including additions and shared Cargo/compiler pins.
    expected = {p: h for p, h in qualified.items() if vm_input(p)}
    actual = {p: h for p, h in current.items() if vm_input(p)}
    assert expected and actual == expected, 'VM or shared build input differs from the measured component'
