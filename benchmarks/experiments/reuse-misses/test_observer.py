import copy
import json
import unittest
from observe import COUNTS, LOOKUPS, NESTED, PHASES, observation


def fixture():
    rows = []
    groups = {key: {field: 0 for field in [*COUNTS, *PHASES, *NESTED]} for key in LOOKUPS}
    for index, (lookup, kind) in enumerate(zip(LOOKUPS, ['reused', 'declined', 'staged', 'declined'])):
        action = dict(kind=kind)
        if kind == 'declined': action['first_reason'] = 'no current recipe'
        row = dict(index=index, name='duplicate display name', lookup=lookup, action=action,
                   operations=10, replay=None, **{key: 0 for key in PHASES})
        if kind == 'reused':
            row.update(binding_seconds=.007, template_decode_seconds=.001,
                replay=dict(events=0, recipe_requires_current_mir=False, current_context_seconds=.005))
        else:
            row.update(prepare_seconds=.001, lower_seconds=.002)
            if kind == 'staged': row['template_encode_seconds'] = .003
        rows.append(row)
        group = groups[lookup]; group.update(functions=1, operations=10); group[kind] = 1
        for key in PHASES: group[key] = row[key]
        if kind == 'reused':
            group.update(replay_body_free_functions=1, replay_current_context_seconds=.005,
                         replay_body_free_context_seconds=.005)
    report = dict(schema_version=1, complete=True, performance_measurement=False,
        cache_load_note='loaded', loaded_entries=2, observed_functions=4, reused=1, lowered=3,
        staged_new=1, declined=2, by_lookup=groups, first_decline_reasons={'no current recipe':2}, functions=rows)
    cache = dict(schema_version=1, mode='reuse', load_note='loaded', loaded_entries=2,
        previous_payload_uses=1, skipped_functions=1, lowered_functions=3, declined_functions=2,
        staged_entries=2, green_missing=1, red_functions=2, previous_binding_seconds=.007,
        previous_template_decoding_seconds=.001, current_template_encoding_seconds=.003)
    return report, cache


def text(report, cache):
    return 'rust-interp-reuse-misses: '+json.dumps(report)+'\nrust-interp-function-cache: '+json.dumps(cache)


class ObservationTests(unittest.TestCase):
    def test_complete_join_keeps_green_declines_distinct_from_red(self):
        report,cache=fixture()
        self.assertEqual(observation(text(report,cache),True),report)
        self.assertIsNone(observation('ordinary diagnostics',False))

    def test_missing_duplicate_and_disabled_reports_reject(self):
        report,cache=fixture();valid=text(report,cache)
        for stderr,enabled in [('',True),(valid+'\n'+valid,True),(valid,False)]:
            with self.assertRaises(ValueError):observation(stderr,enabled)

    def test_row_coverage_actions_and_first_declines_are_recomputed(self):
        for change in ['index','action','reason','removed','group']:
            report,cache=fixture()
            if change=='index':report['functions'][1]['index']=0
            elif change=='action':report['functions'][0]['action']['kind']='staged'
            elif change=='reason':report['functions'][1]['action']['first_reason']='another'
            elif change=='removed':report['functions'].pop()
            else:report['by_lookup']['red_present']['staged']=2
            with self.subTest(change=change),self.assertRaises(ValueError):observation(text(report,cache),True)

    def test_negative_nonfinite_boolean_and_misnested_times_reject(self):
        for value in [-1,float('nan'),float('inf'),True,.008]:
            report,cache=fixture();report['functions'][0]['replay']['current_context_seconds']=value
            with self.subTest(value=value),self.assertRaises(ValueError):observation(text(report,cache),True)

    def test_original_cache_counts_and_timing_must_match(self):
        for key in ['previous_payload_uses','red_functions','green_missing','lowered_functions',
                    'declined_functions','staged_entries','previous_binding_seconds']:
            report,cache=fixture();cache[key]+=1
            with self.subTest(key=key),self.assertRaises(ValueError):observation(text(report,cache),True)

    def test_recipe_presence_and_body_requirements_are_consistent(self):
        for change in ['empty-needs-body','no-hit-recipe','recipe-on-miss']:
            report,cache=fixture()
            if change=='empty-needs-body':report['functions'][0]['replay']['recipe_requires_current_mir']=True
            elif change=='no-hit-recipe':report['functions'][0]['replay']=None
            else:report['functions'][1]['replay']=copy.deepcopy(report['functions'][0]['replay'])
            with self.subTest(change=change),self.assertRaises(ValueError):observation(text(report,cache),True)

    def test_boolean_schema_and_counters_are_not_integer_counts(self):
        for location,key in [('report','schema_version'),('cache','schema_version'),
                             ('report','reused'),('cache','previous_payload_uses')]:
            report,cache=fixture();(report if location=='report' else cache)[key]=True
            with self.subTest(location=location,key=key),self.assertRaises(ValueError):
                observation(text(report,cache),True)

    def test_name_and_index_bounds_reject(self):
        for key,value in [('name','x'*4097),('index',10000),('index',-1)]:
            report,cache=fixture();report['functions'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):observation(text(report,cache),True)


if __name__ == '__main__':unittest.main()
