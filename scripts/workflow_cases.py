"""Pinned production refactors and the existing tests that exercise them."""

TESTS = ['determinize_state_codec::tests::'+name for name in [
    'unsigned_roundtrips_boundaries', 'signed_roundtrips_boundaries',
    'malformed_and_one_below_refuse']]
EDITS = [
    ('reverse-continuation-condition',
     '*byte = if value == 0 { low } else { low | 0x80 };',
     '*byte = if value != 0 { low | 0x80 } else { low };'),
    ('express-zigzag-as-xor',
     '    let mut value = i32::from_ne_bytes((decoded.value >> 1).to_ne_bytes());\n'
     '    if decoded.value & 1 != 0 {\n        value = !value;\n    }',
     '    let value = ((decoded.value >> 1) as i32) ^ -((decoded.value & 1) as i32);'),
    ('compute-encoded-length-from-bit-count',
     '''    match value {
        0..=0x7F => 1,
        0x80..=0x3FFF => 2,
        0x4000..=0x1F_FFFF => 3,
        0x20_0000..=0x0FFF_FFFF => 4,
        _ => 5,
    }''',
     '    let bits = 32 - value.leading_zeros();\n'
     '    if bits == 0 { 1 } else { ((bits + 6) / 7) as usize }'),
    ('put-resource-limit-first', 'if needed > limit {', 'if limit < needed {'),
    ('name-signed-encoding-sign',
     '    let zigzag = if value < 0 { !(bits << 1) } else { bits << 1 };\n    encode_u32',
     '    let sign_mask = (value >> 31) as u32;\n'
     '    let zigzag = (bits << 1) ^ sign_mask;\n    encode_u32'),
]


WORKFLOWS = {
    'fre': dict(package='fre-kernels', file='crates/fre-kernels/src/determinize_state_codec.rs',
                tests=TESTS, edits=EDITS,
                negative=('wrong-encoding', '*byte = if value == 0 { low } else { low | 0x80 };', '*byte = 0;'),
                selections=[[0], [1], [0, 1], [2], [0, 1, 2]],
                workload='Three existing integer codec boundary and error tests'),
}

WORKFLOWS['pgrust'] = dict(
    package='hashfn', file='crates/common/hashfn/src/lib.rs',
    workload='All four existing hashfn library unit tests, including the original 100,000-iteration roundtrip loop',
    tests=['tests::'+name for name in ['uint32_paths_match_byte_path',
           'extended_zero_seed_low_word_equals_hash_bytes',
           'murmurhash32_inverse_roundtrips', 'dynahash_wrappers']],
    selections=[[2], [0, 1], [0, 1], [3], [0, 1, 2, 3]],
    negative=('break-hash-multiplier', 'h = h.wrapping_mul(0x85eb_ca6b);',
              'h = h.wrapping_mul(0x85eb_ca6a);'),
    edits=[
        ('name-inverse-xorshift-intermediate',
         '    h ^= (h >> 13) ^ (h >> 26);',
         '    let shifted = h >> 13;\n    h ^= shifted ^ (shifted >> 13);'),
        ('spell-out-four-byte-load',
         '    u32::from_ne_bytes(k[off..off + 4].try_into().unwrap())',
         '    let bytes = [k[off], k[off + 1], k[off + 2], k[off + 3]];\n'
         '    u32::from_ne_bytes(bytes)'),
        ('combine-constant-hash-initializers',
         '    INITVAL.wrapping_add(len as u32).wrapping_add(SALT)',
         '    let start = INITVAL.wrapping_add(SALT);\n    start.wrapping_add(len as u32)'),
        ('name-string-hash-length-bound',
         '    hash_bytes(&key[..strlen.min(keysize.wrapping_sub(1))])',
         '    let limit = keysize.wrapping_sub(1);\n    let used = strlen.min(limit);\n'
         '    hash_bytes(&key[..used])'),
        ('use-immutable-hash-stages',
         '''pub fn murmurhash32(mut h: u32) -> u32 {
    h ^= h >> 16;
    h = h.wrapping_mul(0x85eb_ca6b);
    h ^= h >> 13;
    h = h.wrapping_mul(0xc2b2_ae35);
    h ^= h >> 16;
    h
}''',
         '''pub fn murmurhash32(h: u32) -> u32 {
    let h = h ^ (h >> 16);
    let h = h.wrapping_mul(0x85eb_ca6b);
    let h = h ^ (h >> 13);
    let h = h.wrapping_mul(0xc2b2_ae35);
    h ^ (h >> 16)
}'''),
    ],
)

NU_MEMBERSHIP = 'ALIASABLE_PARSER_KEYWORDS.contains(&name) || UNALIASABLE_PARSER_KEYWORDS.contains(&name)'
NU_ANY = 'ALIASABLE_PARSER_KEYWORDS.iter().any(|keyword| *keyword == name) || UNALIASABLE_PARSER_KEYWORDS.iter().any(|keyword| *keyword == name)'
WORKFLOWS['nushell'] = dict(
    package='nu-parser', file='crates/nu-parser/src/parse_keywords.rs',
    workload='All four existing parser-keyword tests, including collection of single-word keywords',
    tests=['parse_keywords::tests::'+name for name in [
        'is_parser_keyword_matches_single_word_keywords',
        'is_parser_keyword_rejects_ordinary_command_names',
        'is_parser_keyword_includes_multi_word_entries',
        'single_word_parser_keywords_excludes_multi_word_and_matches_is_parser_keyword']],
    selections=[[0, 1, 2], [1], [3], [0, 1, 2, 3], [3]],
    negative=('reject-valid-keywords', NU_MEMBERSHIP, 'false'),
    edits=[
        ('express-membership-with-any', NU_MEMBERSHIP, NU_ANY),
        ('reject-empty-name-early',
         'pub fn is_parser_keyword(name: &[u8]) -> bool {\n',
         'pub fn is_parser_keyword(name: &[u8]) -> bool {\n    if name.is_empty() { return false; }\n'),
        ('filter-spaces-before-utf8-conversion',
         '''        .filter_map(|bytes| {
            let name = std::str::from_utf8(bytes).ok()?;
            (!name.contains(' ')).then_some(name)
        })''',
         '''        .filter(|bytes| !bytes.contains(&b' '))
        .filter_map(|bytes| std::str::from_utf8(bytes).ok())'''),
        ('chain-keyword-tables-for-membership', NU_ANY,
         'ALIASABLE_PARSER_KEYWORDS.iter().chain(UNALIASABLE_PARSER_KEYWORDS.iter()).any(|keyword| *keyword == name)'),
        ('make-utf8-result-handling-explicit',
         '.filter_map(|bytes| std::str::from_utf8(bytes).ok())',
         '.filter_map(|bytes| match std::str::from_utf8(bytes) { Ok(name) => Some(name), Err(_) => None })'),
    ],
)

RUFF_CODE_MATCH = '''                rule.noqa_code()
                    .is_some_and(|rule_code| rule_code.suffix() == code)'''
RUFF_CODE_EXPLICIT = '''                match rule.noqa_code() {
                    Some(rule_code) => rule_code.suffix() == code,
                    None => false,
                }'''
WORKFLOWS['ruff'] = dict(
    package='ruff_linter', file='crates/ruff_linter/src/registry.rs',
    workload='All six existing registry tests, including rule-code roundtrips, naming patterns, and linter sorting',
    tests=['registry::tests::'+name for name in ['documentation', 'rule_naming_convention',
           'check_code_serialization', 'linter_parse_code', 'rule_size', 'linter_sorting']],
    selections=[[2], [1, 2], [2, 3], [2], [0, 1, 2, 3, 4, 5]],
    negative=('reject-valid-rule-codes', RUFF_CODE_MATCH, '                false'),
    edits=[
        ('match-optional-rule-code-explicitly', RUFF_CODE_MATCH, RUFF_CODE_EXPLICIT),
        ('make-name-conversion-explicit',
         "        let name: &'static str = self.into();",
         "        let name = <&'static str>::from(self);"),
        ('match-linter-prefix-result-explicitly',
         '        let (linter, code) = Linter::parse_code(code).ok_or(FromCodeError::Unknown)?;',
         '''        let (linter, code) = match Linter::parse_code(code) {
            Some(parsed) => parsed,
            None => return Err(FromCodeError::Unknown),
        };'''),
        ('name-code-suffix-before-comparison',
         '                    Some(rule_code) => rule_code.suffix() == code,',
         '                    Some(rule_code) => { let suffix = rule_code.suffix(); suffix == code },'),
        ('use-explicit-rule-search-loop',
         '''        linter
            .all_rules()
            .find(|rule| {
                match rule.noqa_code() {
                    Some(rule_code) => { let suffix = rule_code.suffix(); suffix == code },
                    None => false,
                }
            })
            .ok_or(FromCodeError::Unknown)''',
         '''        for rule in linter.all_rules() {
            if let Some(rule_code) = rule.noqa_code() {
                if rule_code.suffix() == code { return Ok(rule); }
            }
        }
        Err(FromCodeError::Unknown)'''),
    ],
)

# Additional workloads retain their own identity so older comparisons keep
# selecting the original package, test group, and production edits.
WORKFLOW_VARIANTS = {
    ('fre', 'fixed-predicate-word64'): dict(
        package='fre-kernels', file='crates/fre-kernels/src/fixed_predicate_word64.rs',
        workload='All twelve existing fixed-predicate word-matcher tests, including exhaustive reference comparisons',
        tests=['fixed_predicate_word64::tests::'+name for name in [
            'build_attempt_receipts_close_success_partial_failure_and_preflight_refusal',
            'build_limits_accept_exact_and_refuse_one_below',
            'fixed_anchor_matches_exhaustive_short_reference_and_restarts_on_accept',
            'inclusive_full_byte_ranges_union_without_allocation',
            'one_byte_anchor_compact_values_match_exhaustive_reference',
            'partially_overlapping_predicates_match_the_reference',
            'reduce_limits_accept_exact_and_refuse_every_nonzero_one_below',
            'secondary_exact_anchor_rejects_false_candidates_before_broad_predicates',
            'sherlock_shape_accepts_all_cases_for_count_and_span_sum',
            'shift_and_fallback_matches_exhaustive_short_reference_and_resets_on_accept',
            'width_and_range_semantic_boundaries_are_closed',
            'width_one_value_projection_closes_every_prospective_limit']],
        selections=[list(range(12)) for _ in range(5)],
        negative=('reject-valid-anchor-predicates',
                  '        Ok(self.masks[usize::from(byte)] & bit != 0)',
                  '        Ok(self.masks[usize::from(byte)] & bit == 0)'),
        edits=[
            ('separate-compact-state-advance-from-mask',
             '            state = (state.wrapping_shl(1) | 1) & self.masks[usize::from(byte)];',
             '''            let candidates = state.wrapping_shl(1) | 1;
            let mask = self.masks[usize::from(byte)];
            state = candidates & mask;'''),
            ('separate-accounted-state-advance-from-mask',
             '            state = (state.wrapping_shl(1) | 1) & mask;',
             '''            let candidates = state.wrapping_shl(1) | 1;
            state = candidates & mask;'''),
            ('name-predicate-word-before-membership-test',
             '        Ok(self.masks[usize::from(byte)] & bit != 0)',
             '''        let mask = self.masks[usize::from(byte)];
        Ok(mask & bit != 0)'''),
            ('match-compact-secondary-offset-explicitly',
             '''        let secondary_offset = secondary.and_then(Anchor::offset).map(usize::from);
        if let Some(anchor) = secondary {
            let position = secondary_offset?;''',
             '''        let secondary_offset = match secondary {
            Some(anchor) => anchor.offset().map(usize::from),
            None => None,
        };
        if let Some(anchor) = secondary {
            let position = secondary_offset?;'''),
            ('share-compact-anchor-cursor-advance',
             '''            if self.anchor_candidate_matches_value(haystack, start, anchor_offset)? {
                count = count.checked_add(1)?;
                cursor = anchor.checked_add(self.width)?;
            } else {
                cursor = anchor.checked_add(1)?;
            }''',
             '''            let matched = self.anchor_candidate_matches_value(haystack, start, anchor_offset)?;
            if matched { count = count.checked_add(1)?; }
            let advance = if matched { self.width } else { 1 };
            cursor = anchor.checked_add(advance)?;'''),
        ],
    ),
    ('fre', 'bounded-class-sequence'): dict(
        package='fre-kernels', file='crates/fre-kernels/src/bounded_class_sequence.rs',
        workload='All six existing bounded class-sequence tests: greedy matching, scaling, accounting, and exact resource boundaries',
        tests=['bounded_class_sequence::tests::'+name for name in [
            'capitals_sequence_exact_work_boundary_is_hand_derived',
            'execution_scales_with_n_and_not_source_range_count',
            'greedy_maximal_chunks_do_not_rebalance_a_short_remainder',
            'every_nonzero_build_limit_has_an_exact_and_one_below_boundary',
            'every_nonzero_reduce_limit_is_preflighted_at_exact_and_one_below',
            'build_attempt_reports_exact_success_and_partial_failure']],
        selections=[list(range(6)) for _ in range(5)],
        negative=('break-byte-class-membership',
                  '        self.words[word] & (1_u64 << bit) != 0',
                  '        self.words[word] & (1_u64 << bit) == 0'),
        edits=[
            ('separate-byte-class-word-and-mask',
             '''        let word = usize::from(byte) >> 6;
        let bit = u32::from(byte) & 63;
        self.words[word] & (1_u64 << bit) != 0''',
             '''        let word = self.words[usize::from(byte) / 64];
        let mask = 1_u64 << (u32::from(byte) % 64);
        word & mask != 0'''),
            ('return-complete-run-emission-directly',
             '''        if self.units >= self.minimum {
            self.emit_match()?;
        } else {
            self.discarded_units = self
                .discarded_units
                .checked_add(u64::from(self.units))
                .ok_or(ReduceError::ArithmeticOverflow {
                    computation: "discarded units",
                })?;
            self.units = 0;
        }
        Ok(())''',
             '''        if self.units >= self.minimum {
            return self.emit_match();
        }
        self.discarded_units = self.discarded_units
            .checked_add(u64::from(self.units))
            .ok_or(ReduceError::ArithmeticOverflow { computation: "discarded units" })?;
        self.units = 0;
        Ok(())'''),
            ('separate-match-width-conversion',
             '''        self.matched_bytes = self
            .matched_bytes
            .checked_add(
                u64::try_from(width).map_err(|_| ReduceError::ArithmeticOverflow {
                    computation: "matched byte width as u64",
                })?,
            )''',
             '''        let width = u64::try_from(width).map_err(|_| ReduceError::ArithmeticOverflow {
            computation: "matched byte width as u64",
        })?;
        self.matched_bytes = self.matched_bytes.checked_add(width)'''),
            ('express-final-unit-selection-with-if-let',
             '''        match state {
            State::Body { start } | State::Trail { start } => {
                reducer.complete_unit(start, haystack.len())?;
            }
            State::NeedBody { .. } | State::Seeking => {}
        }''',
             '''        if let State::Body { start } | State::Trail { start } = state {
            reducer.complete_unit(start, haystack.len())?;
        }'''),
            ('share-checked-input-scaling',
             '''        let class_comparisons =
            input_bytes
                .checked_mul(3)
                .ok_or(ReduceError::ArithmeticOverflow {
                    computation: "class comparison bound",
                })?;
        let branch_charges = input_bytes
            .checked_mul(8)
            .ok_or(ReduceError::ArithmeticOverflow {
                computation: "branch charge bound",
            })?;
        // A maximum-one unit can write run_start, units, completed_units,
        // run_end, matches, matched_bytes, reset units, and the outer state.
        let state_writes = input_bytes
            .checked_mul(8)
            .ok_or(ReduceError::ArithmeticOverflow {
                computation: "state write bound",
            })?;
        let arithmetic_charges =
            input_bytes
                .checked_mul(8)
                .ok_or(ReduceError::ArithmeticOverflow {
                    computation: "arithmetic charge bound",
                })?;''',
             '''        let scale = |factor: usize, computation: &'static str| {
            input_bytes.checked_mul(factor)
                .ok_or(ReduceError::ArithmeticOverflow { computation })
        };
        let class_comparisons = scale(3, "class comparison bound")?;
        let branch_charges = scale(8, "branch charge bound")?;
        // A maximum-one unit can write run_start, units, completed_units,
        // run_end, matches, matched_bytes, reset units, and the outer state.
        let state_writes = scale(8, "state write bound")?;
        let arithmetic_charges = scale(8, "arithmetic charge bound")?;'''),
        ],
    ),
    ('nushell', 'float-ranges'): dict(
        package='nu-protocol', file='crates/nu-protocol/src/value/range.rs',
        workload='Seven existing fractional, decreasing, and rounded floating-point range tests',
        tests=['value::range::tests::'+name for name in [
            'float_range_small_step_inclusive', 'float_range_tiny_step_inclusive',
            'float_range_integer_step_noninteger_start', 'float_range_decreasing',
            'float_range_explicit_step_clean_values', 'float_range_rounds_last_value',
            'float_range_clean_serialization']],
        selections=[[0, 1, 5, 6], [0, 1, 5, 6], [2, 3, 4], [0, 1, 2, 3], list(range(7))],
        negative=('double-each-range-step',
                  'let current = self.start + self.step * iter as f64;',
                  'let current = self.start + self.step * iter as f64 * 2.0;'),
        edits=[
            ('compute-rounded-quotient-once',
             '''                let value = if (quotient - quotient.round()).abs() < 1e-10 {
                    quotient.round() * self.step''',
             '''                let rounded = quotient.round();
                let value = if (quotient - rounded).abs() < 1e-10 {
                    rounded * self.step'''),
            ('name-scaled-value-before-rounding',
             '                    (value * self.round_factor).round() / self.round_factor',
             '''                    let scaled = value * self.round_factor;
                    scaled.round() / self.round_factor'''),
            ('name-range-direction',
             '                let not_end = match (self.step < 0.0, self.end) {',
             '''                let decreasing = self.step < 0.0;
                let not_end = match (decreasing, self.end) {'''),
            ('compute-step-magnitude-once',
             '''            let round_factor = if self.step.abs() >= 1.0 || self.step == 0.0 {
                0.0 // sentinel: no rounding
            } else {
                let precision = (-self.step.abs().log10()).max(0.0).ceil() as i32;''',
             '''            let magnitude = self.step.abs();
            let round_factor = if magnitude >= 1.0 || self.step == 0.0 {
                0.0 // sentinel: no rounding
            } else {
                let precision = (-magnitude.log10()).max(0.0).ceil() as i32;'''),
            ('return-next-value-before-exhaustion',
             '''                if not_end && !self.signals.interrupted() {
                    self.iter = iter.checked_add(1);
                    Some(value)
                } else {
                    self.iter = None;
                    None
                }''',
             '''                if not_end && !self.signals.interrupted() {
                    self.iter = iter.checked_add(1);
                    return Some(value);
                }
                self.iter = None;
                None'''),
        ],
    ),
}

WORKFLOW_VARIANTS['nushell', 'last-result'] = dict(
    package='nu-protocol', file='crates/nu-protocol/src/last_result.rs',
    workload='All ten existing last-result tests: list/table/record/string/binary budgets and error-only detection; original 100-item, 50-row, and 10,000-byte inputs retained',
    tests=['last_result::tests::'+name for name in [
        'under_budget_unchanged', 'list_prefix_respects_budget',
        'string_prefix_respects_budget', 'binary_prefix_respects_budget',
        'zero_budget_yields_nothing', 'table_like_list_keeps_whole_records_only',
        'record_fields_respect_budget', 'error_only_detects_error_value',
        'error_only_detects_nonempty_error_list', 'error_only_rejects_mixed_list',
    ]],
    negative=('mark-untruncated-values-as-truncated',
              '    if value.memory_size() <= budget {\n        return (value, false);\n    }',
              '    if value.memory_size() <= budget {\n        return (value, true);\n    }'),
    selections=[[0, 4], [1, 5], [6], [2], [7, 8, 9]],
    edits=[
        ('name-whole-value-budget-check',
         '    if value.memory_size() <= budget {\n        return (value, false);\n    }',
         '    let fits_whole = value.memory_size() <= budget;\n'
         '    if fits_whole {\n        return (value, false);\n    }'),
        ('name-list-item-budget-check',
         '        if used.saturating_add(item_size) <= budget {\n            used += item_size;',
         '        let next_size = used.saturating_add(item_size);\n'
         '        if next_size <= budget {\n            used += item_size;'),
        ('return-record-truncation-tuple-directly',
         '''            let (v, t) = truncate_value_to_budget(val, remaining);
            (v, t)''',
         '            truncate_value_to_budget(val, remaining)'),
        ('use-character-boundary-as-prefix-loop-guard',
         '''    // Shrink content until Value::memory_size fits. capacity of a freshly built String equals len.
    let mut end = budget
        .saturating_sub(std::mem::size_of::<Value>())
        .min(val.len());
    while end > 0 && !val.is_char_boundary(end) {
        end -= 1;
    }''',
         '''    // Shrink content until Value::memory_size fits. capacity of a freshly built String equals len.
    let mut end = budget
        .saturating_sub(std::mem::size_of::<Value>())
        .min(val.len());
    // Zero is always a character boundary, so this loop cannot underflow.
    while !val.is_char_boundary(end) {
        end -= 1;
    }'''),
        ('scan-error-only-lists-with-explicit-early-return',
         '        Value::List { vals, .. } => !vals.is_empty() && vals.iter().all(Value::is_error),',
         '''        Value::List { vals, .. } => {
            if vals.is_empty() {
                return false;
            }
            for item in vals.iter() {
                if !item.is_error() {
                    return false;
                }
            }
            true
        }'''),
    ],
)

WORKFLOW_VARIANTS['nushell', 'span-signals'] = dict(
    package='nu-protocol', file='crates/nu-protocol/src/span.rs',
    workload='All eight existing row/column span tests, including the original 20,000-byte signal-interruption input, short-input polling behavior, and end-of-input boundaries',
    tests=['span::tests::'+name for name in [
        'try_from_row_column_first_line', 'try_from_row_column_second_line',
        'try_from_row_column_last_char', 'try_from_row_column_beyond_input',
        'try_from_row_column_interrupted_triggers_error',
        'try_from_row_column_short_input_skips_signal_check',
        'try_from_row_column_not_interrupted',
        'try_from_row_column_start_matches_from_row_column',
    ]],
    negative=('delay-signal-check-past-original-test-input',
              '            if offset > 0 && offset % 16384 == 0 {',
              '            if offset > 0 && offset % 32768 == 0 {'),
    selections=[[4, 5, 6], [0, 1, 2, 3], [0, 2, 7], [0, 1, 7], [3]],
    edits=[
        ('express-poll-interval-with-bit-mask',
         '            if offset > 0 && offset % 16384 == 0 {',
         '            let poll_signals = offset != 0 && (offset & 16383) == 0;\n'
         '            if poll_signals {'),
        ('iterate-copied-bytes-explicitly',
         '        for (offset, curr_byte) in contents.bytes().enumerate() {\n'
         '            let poll_signals = offset != 0 && (offset & 16383) == 0;',
         '        for (offset, curr_byte) in contents.as_bytes().iter().copied().enumerate() {\n'
         '            let poll_signals = offset != 0 && (offset & 16383) == 0;'),
        ('derive-highlight-end-from-current-byte',
         '                let end = contents.len().min(offset + 1);',
         '                // The current byte proves offset + 1 is within contents.\n'
         '                let end = offset + 1;'),
        ('continue-after-advancing-the-row',
         r'''            if curr_byte == b'\n' {
                cur_row += 1;
                cur_col = 1;
            } else if cur_row >= row && cur_col >= col {
                // Return a span covering at least one byte for visible error highlighting
                // The current byte proves offset + 1 is within contents.
                let end = offset + 1;
                return Ok(Span::new(offset, end));
            } else {
                cur_col += 1;
            }''',
         r'''            if curr_byte == b'\n' {
                cur_row += 1;
                cur_col = 1;
                continue;
            }
            if cur_row >= row && cur_col >= col {
                // Return a span covering at least one byte for visible error highlighting
                // The current byte proves offset + 1 is within contents.
                let end = offset + 1;
                return Ok(Span::new(offset, end));
            }
            cur_col += 1;'''),
        ('name-end-of-input-position',
         '        Ok(Span::point(contents.len()))',
         '        let end = contents.len();\n        Ok(Span::point(end))'),
    ],
)

WORKFLOW_VARIANTS['nushell', 'type-relations'] = dict(
    package='nu-protocol', file='crates/nu-protocol/src/ty.rs',
    workload='All fourteen existing type-relation tests: enum cross-product covariance, OneOf hashing/deduplication, nested collections, and the original 100-step widening chain',
    tests=['ty::tests::'+name for name in [
        'oneof::oneof_lhs', 'oneof::oneof_rhs',
        'oneof_flattening::test_oneof_creation_flattens',
        'oneof_flattening::test_oneof_deduplicates',
        'oneof_flattening::test_widen_flattens_oneof',
        'subtype_relation::table_list_oneof_covariance',
        'subtype_relation::test_any_is_top_type',
        'subtype_relation::test_list_covariance',
        'subtype_relation::test_number_supertype',
        'subtype_relation::test_reflexivity',
        'widen_shortcuts::test_chain_shortcut',
        'widen_shortcuts::test_glob_string_union',
        'widen_shortcuts::test_list_table_widen_preserves_list',
        'widen_shortcuts::test_widen_subtype_shortcut',
    ]],
    negative=('reverse-top-type-relation',
              '            (_, Type::Any) => Some(TypeRelation::Subtype),',
              '            (_, Type::Any) => Some(TypeRelation::Supertype),'),
    selections=[[8, 13], [2, 3, 4], [5, 10, 11, 12, 13], [6, 7, 9], [0, 1, 10, 11]],
    edits=[
        ('combine-equal-and-supertype-widening-arms',
         '                    TypeRelation::Equal => lhs,\n                    TypeRelation::Supertype => lhs,',
         '                    TypeRelation::Equal | TypeRelation::Supertype => lhs,'),
        ('collect-oneof-from-explicit-iterator',
         '        Self::OneOf(OneOf::from_iter(types))',
         '        Self::OneOf(types.into_iter().collect())'),
        ('return-unrelated-widening-pair-early',
         '''            (lhs, rhs) => match lhs.compare_types(&rhs) {
                Some(rel) => Ok(match rel {
                    TypeRelation::Subtype => rhs,
                    TypeRelation::Equal | TypeRelation::Supertype => lhs,
                }),
                // Fallback - the two types are unrelated. Move them out so that callers don't have to clone again.
                None => Err((lhs, rhs)),
            },''',
         '''            (lhs, rhs) => {
                let Some(rel) = lhs.compare_types(&rhs) else {
                    return Err((lhs, rhs));
                };
                Ok(match rel {
                    TypeRelation::Subtype => rhs,
                    TypeRelation::Equal | TypeRelation::Supertype => lhs,
                })
            }'''),
        ('express-subtype-test-with-is-some-and',
         '''        matches!(
            self.compare_types(other),
            Some(TypeRelation::Subtype | TypeRelation::Equal)
        )''',
         '''        self.compare_types(other).is_some_and(|relation| {
            matches!(relation, TypeRelation::Subtype | TypeRelation::Equal)
        })'''),
        ('make-union-pair-iterator-explicit',
         '            (this, other) => Type::one_of([this, other]),',
         '            (this, other) => Type::one_of([this, other].into_iter()),'),
    ],
)

# Keep the original million-byte reference vector and incremental test intact.
WORKFLOW_VARIANTS['pgrust', 'sha1-vectors'] = {'package': 'pg_sha1',
 'file': 'crates/common/sha1/src/lib.rs',
 'workload': 'Both existing SHA-1 unit tests: standard vectors including the original million-byte '
             'input, plus incremental hashing in seven-byte chunks',
 'tests': ['tests::vectors', 'tests::incremental_matches_oneshot'],
 'selections': [[0, 1], [0, 1], [0, 1], [0, 1], [0, 1]],
 'negative': ('perturb-first-round-constant', '0x5a827999, 0x6ed9eba1', '0x5a827998, 0x6ed9eba1'),
 'edits': [('name-schedule-read-range',
            '    u32::from_be_bytes(m[n * 4..n * 4 + 4].try_into().unwrap())',
            '    let start = n * 4;\n'
            '    u32::from_be_bytes(m[start..start + 4].try_into().unwrap())'),
           ('name-schedule-write-range',
            '    m[n * 4..n * 4 + 4].copy_from_slice(&v.to_be_bytes());',
            '    let start = n * 4;\n    m[start..start + 4].copy_from_slice(&v.to_be_bytes());'),
           ('share-round-index-for-function-and-constant',
            '        let f = match t / 20 {\n'
            '            0 => (b & c) | ((!b) & d),\n'
            '            2 => (b & c) | (b & d) | (c & d),\n'
            '            _ => b ^ c ^ d,\n'
            '        };\n'
            '        let tmp = a\n'
            '            .rotate_left(5)\n'
            '            .wrapping_add(f)\n'
            '            .wrapping_add(e)\n'
            '            .wrapping_add(w_get(&ctx.m, sidx))\n'
            '            .wrapping_add(K[t / 20]);',
            '        let round = t / 20;\n'
            '        let f = match round {\n'
            '            0 => (b & c) | ((!b) & d),\n'
            '            2 => (b & c) | (b & d) | (c & d),\n'
            '            _ => b ^ c ^ d,\n'
            '        };\n'
            '        let tmp = a\n'
            '            .rotate_left(5)\n'
            '            .wrapping_add(f)\n'
            '            .wrapping_add(e)\n'
            '            .wrapping_add(w_get(&ctx.m, sidx))\n'
            '            .wrapping_add(K[round]);'),
           ('name-input-and-block-remaining-capacity',
            '            let copysiz = (BLOCK - gapstart).min(data.len() - off);',
            '            let block_remaining = BLOCK - gapstart;\n'
            '            let input_remaining = data.len() - off;\n'
            '            let copysiz = block_remaining.min(input_remaining);'),
           ('write-digest-by-exact-output-chunks',
            '        for (n, word) in self.h.iter().enumerate() {\n'
            '            digest[n * 4..n * 4 + 4].copy_from_slice(&word.to_be_bytes());\n'
            '        }',
            '        for (output, word) in digest.chunks_exact_mut(4).zip(self.h.iter()) {\n'
            '            output.copy_from_slice(&word.to_be_bytes());\n'
            '        }')]}


# Selected from the native/custom execution survey; the complete original test module is preserved.
WORKFLOW_VARIANTS[('fre', 'grapheme-scalar-dfa')] = {'package': 'fre-kernels',
 'file': 'crates/fre-kernels/src/grapheme_scalar_dfa.rs',
 'workload': 'All seventeen existing grapheme scalar DFA tests: UTF-8 decoding, cluster semantics, exact '
             'resource bounds, overflow and publication failures',
 'tests': ['grapheme_scalar_dfa::tests::arithmetic_overflow_paths_are_named_and_fail_closed',
           'grapheme_scalar_dfa::tests::build_attempt_reports_exact_success_and_partial_stream_failure',
           'grapheme_scalar_dfa::tests::build_rejects_missing_and_inexact_derived_roles',
           'grapheme_scalar_dfa::tests::counted_stream_length_mismatch_fails_before_plan_publication',
           'grapheme_scalar_dfa::tests::default_empty_reductions_admit_exact_fixed_scratch',
           'grapheme_scalar_dfa::tests::direct_limits_precede_overflow_prone_derived_bounds',
           'grapheme_scalar_dfa::tests::every_build_resource_is_exact_and_one_below',
           'grapheme_scalar_dfa::tests::every_count_resource_is_exact_and_one_below',
           'grapheme_scalar_dfa::tests::every_published_actual_counter_is_reconciled',
           'grapheme_scalar_dfa::tests::every_span_sum_resource_is_exact_and_one_below',
           'grapheme_scalar_dfa::tests::exact_reduce_bounds_are_enforced_before_traversal',
           'grapheme_scalar_dfa::tests::hand_calculated_n_scaling',
           'grapheme_scalar_dfa::tests::hand_calculated_q_scaling',
           'grapheme_scalar_dfa::tests::large_input_transition_bound_is_exact_and_one_below',
           'grapheme_scalar_dfa::tests::malformed_utf8_advances_one_byte_without_matching',
           'grapheme_scalar_dfa::tests::max_event_preflight_and_transitions_stay_bounded',
           'grapheme_scalar_dfa::tests::ordered_cluster_traps'],
 'selections': [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]],
 'negative': ('reject-ascii-in-decoder', '    if first <= 0x7F {', '    if first > 0x7F {'),
 'edits': [('convert-ascii-with-cast', '            scalar: Some(u32::from(first)),', '            scalar: Some(first as u32),'),
           ('recognize-ascii-by-high-bit', '    if first <= 0x7F {', '    if first & 0x80 == 0 {'),
           ('match-reduce-multiplication-overflow-explicitly',
            '    left.checked_mul(right)\n        .ok_or(ReduceError::ArithmeticOverflow { computation })',
            '    match left.checked_mul(right) {\n        Some(product) => Ok(product),\n        None => Err(ReduceError::ArithmeticOverflow { computation }),\n    }'),
           ('match-classification-segment-explicitly',
            '            let segment = self\n'
            '                .segments\n'
            '                .get(middle)\n'
            '                .ok_or(ReduceError::ArithmeticOverflow {\n'
            '                    computation: "segment access",\n'
            '                })?;',
            '            let segment = match self.segments.get(middle) {\n'
            '                Some(segment) => segment,\n'
            '                None => return Err(ReduceError::ArithmeticOverflow {\n'
            '                    computation: "segment access",\n'
            '                }),\n'
            '            };'),
           ('halve-comparison-bound-with-shift', '        segments /= 2;', '        segments >>= 1;')]}

# Five previously TBL-blocked bodies plus the existing factored-cardinality test.
WORKFLOW_VARIANTS[('fre', 'packed-literal-set')] = {'package': 'fre-kernels',
 'file': 'crates/fre-kernels/src/packed_literal_set.rs',
 'workload': 'Six existing packed literal-set tests covering SIMD matcher, factored byte classes, windows, '
             'resource accounting and shape refusal; the seventh regex-reference test remains '
             'lowering-blocked.',
 'tests': ['packed_literal_set::tests::cardinality_above_teddy_requires_a_complete_factored_language',
           'packed_literal_set::tests::complete_cartesian_columns_use_one_anchored_scan_and_reject_missing_tuples',
           'packed_literal_set::tests::factored_search_covers_two_and_three_byte_anchor_classes',
           'packed_literal_set::tests::leftmost_first_and_window_offsets_match_the_contract',
           'packed_literal_set::tests::native_and_factored_certificates_preserve_windows_limits_and_accounting',
           'packed_literal_set::tests::unsupported_shapes_and_work_caps_are_explicit'],
 'selections': [[0, 1, 2, 3, 4, 5],
                [0, 1, 2, 3, 4, 5],
                [0, 1, 2, 3, 4, 5],
                [0, 1, 2, 3, 4, 5],
                [0, 1, 2, 3, 4, 5]],
 'negative': ('invert-byte-class-membership',
              '    class[word] & (1_u64 << (byte & 63)) != 0',
              '    class[word] & (1_u64 << (byte & 63)) == 0'),
 'edits': [('name-byte-class-bit-mask',
            '    class[word] & (1_u64 << (byte & 63)) != 0',
            '    let mask = 1_u64 << (byte & 63);\n    class[word] & mask != 0'),
           ('name-preceding-rank-mask',
            '    let preceding_bits = class[word] & ((1_u64 << (byte & 63)).wrapping_sub(1));',
            '    let preceding_mask = (1_u64 << (byte & 63)).wrapping_sub(1);\n'
            '    let preceding_bits = class[word] & preceding_mask;'),
           ('spell-out-factored-width-bounds',
            '    if !(FULL_TEDDY_FILTER_BYTES..=MAX_FACTORED_COLUMNS).contains(&width)',
            '    if width < FULL_TEDDY_FILTER_BYTES || width > MAX_FACTORED_COLUMNS'),
           ('match-search-work-overflow-explicitly',
            '        let work_upper_bound = positions_upper_bound\n'
            '            .checked_mul(verification_bytes_per_position)\n'
            '            .ok_or(PackedLiteralSetError::ArithmeticOverflow {\n'
            '                computation: "packed literal search work",\n'
            '            })?;',
            '        let work_upper_bound = match '
            'positions_upper_bound.checked_mul(verification_bytes_per_position) {\n'
            '            Some(work) => work,\n'
            '            None => return Err(PackedLiteralSetError::ArithmeticOverflow {\n'
            '                computation: "packed literal search work",\n'
            '            }),\n'
            '        };'),
           ('reuse-window-origin-in-result-offsets',
            '        let matched = matched.map(|(relative_start, relative_end)| {\n'
            '            (\n'
            '                window.start() + relative_start,\n'
            '                window.start() + relative_end,\n'
            '            )\n'
            '        });',
            '        let origin = window.start();\n'
            '        let matched = matched.map(|(relative_start, relative_end)| {\n'
            '            (origin + relative_start, origin + relative_end)\n'
            '        });')]}

# All eleven fresh native-matching bodies unlocked by explicit unavailable calls.
WORKFLOW_VARIANTS[('fre', 'forward-anchored')] = {'package': 'fre-kernels',
 'file': 'crates/fre-kernels/src/forward_anchored.rs',
 'tests': ['forward_anchored::tests::bitset_probe_rejects_a_short_anchored_run_before_whole_window_prefiltering',
           'forward_anchored::tests::candidate_prefix_change_preserves_range_and_bitset_paths',
           'forward_anchored::tests::empty_one_byte_mismatch_and_anchor_cases_are_exact',
           'forward_anchored::tests::exhaustive_kernel_differential_covers_arbitrary_classes_and_suffix_borders',
           'forward_anchored::tests::late_full_block_mismatch_charges_the_rescan_before_execution',
           'forward_anchored::tests::search_limits_are_checked_before_scanning',
           'forward_anchored::tests::selects_canonical_small_sets_and_unchanged_floors',
           'forward_anchored::tests::start_range_swar8_high_bit_ranges_preserve_boundary_and_accounting',
           'forward_anchored::tests::start_range_swar8_threshold_and_failed_word_lanes_are_exact',
           'forward_anchored::tests::theorem_accepts_bordered_suffix_and_rejects_disjointness_failures',
           'forward_anchored::tests::windows_keep_original_anchor_context_and_validate_first'],
 'selections': [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]],
 'workload': 'All eleven newly executable forward-anchored original tests, including the exhaustive '
             'arbitrary-class/suffix differential, windows, canonical class selection, exact limits and work '
             'accounting; unavailable-call stops are explicit and reached boundaries are failures',
 'negative': ('invert-byte-class-membership',
              '        self.words[word] & (1_u64 << bit) != 0',
              '        self.words[word] & (1_u64 << bit) == 0'),
 'edits': [('name-byte-class-membership-mask',
            '        self.words[word] & (1_u64 << bit) != 0',
            '        let mask = 1_u64 << bit;\n        self.words[word] & mask != 0'),
           ('combine-empty-class-words',
            '        self.words[0] == 0 && self.words[1] == 0 && self.words[2] == 0 && self.words[3] == 0',
            '        (self.words[0] | self.words[1] | self.words[2] | self.words[3]) == 0'),
           ('match-canonical-member-count-explicitly',
            '        (member_count == N).then_some(members)',
            '        if member_count == N { Some(members) } else { None }'),
           ('match-inclusive-range-cardinality',
            '        if self.cardinality() != span {\n'
            '            return None;\n'
            '        }\n'
            '        Some((u8::try_from(first).ok()?, u8::try_from(last).ok()?))',
            '        match self.cardinality() == span {\n'
            '            true => Some((u8::try_from(first).ok()?, u8::try_from(last).ok()?)),\n'
            '            false => None,\n'
            '        }'),
           ('use-iterator-for-inclusive-insertion',
            '    pub fn insert_inclusive(&mut self, start: u8, end: u8) {\n'
            '        if start > end {\n'
            '            return;\n'
            '        }\n'
            '        for byte in start..=end {\n'
            '            self.insert(byte);\n'
            '        }\n'
            '    }',
            '    pub fn insert_inclusive(&mut self, start: u8, end: u8) {\n'
            '        if start > end {\n'
            '            return;\n'
            '        }\n'
            '        (start..=end).for_each(|byte| self.insert(byte));\n'
            '    }')]}


# The complete18-test module now has fresh native-matching CPU-query execution.
WORKFLOW_VARIANTS[('fre', 'folded-literal-trie')] = {'package': 'fre-kernels',
 'file': 'crates/fre-kernels/src/folded_literal_trie.rs',
 'tests': ['folded_literal_trie::tests::kelvin_sigma_russian_and_duplicates_keep_original_byte_offsets',
           'folded_literal_trie::tests::malformed_utf8_never_matches_and_advances_one_byte',
           'folded_literal_trie::tests::prefix_lengths_duplicates_and_pattern_priority_have_stable_order',
           'folded_literal_trie::tests::first_candidate_projection_stops_after_one_start_and_keeps_pattern_priority',
           'folded_literal_trie::tests::windows_and_ascii_fold_differential_are_exact',
           'folded_literal_trie::tests::russian_root_uses_rare_common_continuation_offset',
           'folded_literal_trie::tests::lead_only_root_uses_wide_continuation_classifier',
           'folded_literal_trie::tests::four_byte_root_exercises_later_common_offset',
           'folded_literal_trie::tests::four_distinct_root_bytes_use_wide_classifier',
           'folded_literal_trie::tests::wide_classifier_matches_complete_scan_across_blocks_and_tail',
           'folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows',
           'folded_literal_trie::tests::empty_unsorted_and_overlapping_classes_return_typed_fallback',
           'folded_literal_trie::tests::a_window_split_inside_multibyte_scalar_cannot_match_across_boundary',
           'folded_literal_trie::tests::every_build_dimension_has_an_exact_one_below_gate',
           'folded_literal_trie::tests::every_positive_scan_dimension_refuses_before_emission',
           'folded_literal_trie::tests::maximum_state_fanout_bounds_linked_transition_probes',
           'folded_literal_trie::tests::fixed_trie_doubling_counters_are_linear',
           'folded_literal_trie::tests::prospective_overflow_is_typed_without_source_access'],
 'selections': [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]],
 'workload': 'All eighteen original folded-literal-trie tests, including complete short-byte-string/window '
             'differentials, malformed UTF-8, canonical folding, exact resource gates, SIMD prefilters and '
             'accounting',
 'negative': ['break-ascii-scalar-decoding',
              '            scalar: Some(u32::from(first)),',
              '            scalar: Some(0),'],
 'edits': [['test-ascii-leading-bit', '    if first <= 0x7F {', '    if first & 0x80 == 0 {'],
           ['express-continuation-prefix-as-shift', '    byte & 0xC0 == 0x80', '    byte >> 6 == 2'],
           ['name-root-membership-mask',
            '    set[index] & (1_u64 << bit) != 0',
            '    let mask = 1_u64 << bit;\n    set[index] & mask != 0'],
           ['name-two-byte-scalar-fields',
            '        return DecodedScalar {\n'
            '            scalar: Some((u32::from(first & 0x1F) << 6) | u32::from(second & 0x3F)),\n'
            '            width: 2,',
            '        let lead = u32::from(first & 0x1F) << 6;\n'
            '        let continuation = u32::from(second & 0x3F);\n'
            '        return DecodedScalar {\n'
            '            scalar: Some(lead | continuation),\n'
            '            width: 2,'],
           ['match-first-byte-explicitly',
            '    let Some(&first) = bytes.first() else {\n        return invalid(0);\n    };',
            '    let first = match bytes.first() {\n'
            '        Some(&byte) => byte,\n'
            '        None => return invalid(0),\n'
            '    };']]}


# Seventeen TLS-dependent original tests, freshly checked against native Rust.
WORKFLOW_VARIANTS[('fre', 'forward-anchored-tls')] = {'package': 'fre-kernels',
 'file': 'crates/fre-kernels/src/forward_anchored.rs',
 'tests': ['forward_anchored::tests::asymmetric_partition_is_ordered_disjoint_complete_and_mutation_effective',
           'forward_anchored::tests::asymmetric_witness_confirms_the_returned_first_outsider',
           'forward_anchored::tests::asymmetric_witness_matches_independent_model_at_every_directed_position',
           'forward_anchored::tests::asymmetric_witness_partitions_and_call_counts_are_exact',
           'forward_anchored::tests::asymmetric_witness_plan_preserves_partition_boundary_semantics',
           'forward_anchored::tests::asymmetric_witness_threshold_is_exact_and_overlap_uses_forward',
           'forward_anchored::tests::candidate_prefix_accounting_is_exact_across_equality_block_edges',
           'forward_anchored::tests::dispatch_never_replaces_specialized_or_non_ascii_prefix_paths',
           'forward_anchored::tests::equality_candidate_search_handles_absence_and_earlier_outsiders',
           'forward_anchored::tests::equality_candidate_search_preserves_windows_and_absolute_anchors',
           'forward_anchored::tests::first_suffix_byte_candidate_is_the_only_possible_boundary',
           'forward_anchored::tests::medium_witness_edges_and_middle_have_the_modeled_call_counts',
           'forward_anchored::tests::overlapping_asymmetric_regions_use_one_forward_prefilter',
           'forward_anchored::tests::pair_through_quint_confirm_suffix_at_the_first_outsider',
           'forward_anchored::tests::reverse_asymmetric_witness_handles_a_bordered_suffix',
           'forward_anchored::tests::triple_plan_target_lengths_and_long_boundary_have_exact_calls',
           'forward_anchored::tests::valid_equality_candidate_excludes_the_known_outsider'],
 'selections': [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]],
 'workload': 'Seventeen original forward-anchored tests newly executable with guest TLS destructors: '
             'ordered disjoint witness partitions, directed-position model comparisons, candidate-prefix '
             'accounting, threshold boundaries and exact call counts; real production edits preserve '
             'original tests and tracing instrumentation',
 'negative': ('invert-byte-class-membership',
              '        self.words[word] & (1_u64 << bit) != 0',
              '        self.words[word] & (1_u64 << bit) == 0'),
 'edits': [('name-byte-class-membership-mask',
            '        self.words[word] & (1_u64 << bit) != 0',
            '        let mask = 1_u64 << bit;\n        self.words[word] & mask != 0'),
           ('combine-empty-class-words',
            '        self.words[0] == 0 && self.words[1] == 0 && self.words[2] == 0 && self.words[3] == 0',
            '        (self.words[0] | self.words[1] | self.words[2] | self.words[3]) == 0'),
           ('match-canonical-member-count-explicitly',
            '        (member_count == N).then_some(members)',
            '        if member_count == N { Some(members) } else { None }'),
           ('match-inclusive-range-cardinality',
            '        if self.cardinality() != span {\n'
            '            return None;\n'
            '        }\n'
            '        Some((u8::try_from(first).ok()?, u8::try_from(last).ok()?))',
            '        match self.cardinality() == span {\n'
            '            true => Some((u8::try_from(first).ok()?, u8::try_from(last).ok()?)),\n'
            '            false => None,\n'
            '        }'),
           ('use-iterator-for-inclusive-insertion',
            '    pub fn insert_inclusive(&mut self, start: u8, end: u8) {\n'
            '        if start > end {\n'
            '            return;\n'
            '        }\n'
            '        for byte in start..=end {\n'
            '            self.insert(byte);\n'
            '        }\n'
            '    }',
            '    pub fn insert_inclusive(&mut self, start: u8, end: u8) {\n'
            '        if start > end {\n'
            '            return;\n'
            '        }\n'
            '        (start..=end).for_each(|byte| self.insert(byte));\n'
            '    }')]}
