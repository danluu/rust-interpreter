# Guarded retention enables a narrow set of additional forwards

All three offline comparisons reproduced the saved native code bytes and
operation maps exactly. No alternative native code was published or executed.
The three selected ignored tests passed and 137 frozen inputs verified.

| Saved profile | Additional frequency-weighted forwards | Lost forwards | Changed functions | Staged bytes removed |
| --- | ---: | ---: | ---: | ---: |
| Token block boundaries | 60,720,128 | 0 | 3 | 192 |
| Token exhaustive partitions | 119,886 | 0 | 3 | 192 |
| Folded matching | 0 | 0 | 0 | 0 |

No function declined under cumulative 16 MiB staging. All added forwards carry
dynamic cached values. In the primary profile, two SipHash routines account
for every dynamically reached additional forward; a third changed routine's
sites have zero recorded hits. The weighted static word reduction is confined
to operation spans. Flush, transition, guard and other overhead span totals do
not change in that profile. Static weights do not establish retired instruction
counts or latency, and 192 fewer static bytes do not indicate a 192-byte total
working-set improvement.

The primary baseline already forwards weighted counts of 105,120,193 immediate
facts and 25,382,174 current-frame pointer facts, as well as 740,850,359 cached
and 7,701,750 persistent physical-register facts. The next bounded question is
whether exact immediate and full-eight-byte local-pointer facts can remain
static after Load rather than becoming a new dynamic cache owner. Narrow local
pointers and shared dynamic owners cannot be treated this way. Inspect a
distinct composed offline treatment before deciding whether to implement and
qualify a runtime candidate; do not time this narrow retention change alone.

The first admission failed while reading an incompletely postprocessed old
profile record, before any build or guest command. Its source and failure remain
in [the admission report](../guarded-local-facts-census-admission-01/summary.json).
The corrected driver binds all three cases to the completed profile repair and
each original selection receipt. Supervisor 41869 and driver 41872 completed
with exit 0. [Summary and evidence hashes](summary.json).
