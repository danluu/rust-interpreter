# Fixed chains retain modest potential coverage

All12 controls pass and independent closure recomputes both cases. The model
checks semantic instruction/fault prefixes and distinguishes native current-
region precharge from interpreter fault accounting. Refunds preserve canonical
budget at modeled exits. This is not native emitter or ABI qualification.

| Saved native self samples | Block | Exhaustive |
| --- | ---: | ---: |
| Generated code | 1933 | 1429 |
| All region budget words | 184 | 80 |
| Cost materialization / compare / branch / debit | 174 / 1 / 2 / 7 | 77 / 0 / 3 / 0 |
| Budget words at potential fixed-chain fast targets | 39 | 23 |

Most budget samples land at the first word, cost materialization. This is a PC
attribution, not evidence that loading a constant takes that fraction of time;
sampling skid, entry frequency and pipeline effects are not separated here.
In particular, do not infer a budget-subtraction dependency bottleneck from the
whole budget bucket. That inference is not supported by the exact partition.

Potential fast targets cover2.02%/1.61% of generated samples. Entry paths are not
recorded in these windows, so this overstates what can be attributed to actual
fast visits. The separately bound full profiles contain32436817/42031915 normal
visits across the single-successor certified edges; potential destinations have
75673712/98510491 visits from all sources. Neither ratio can be applied directly
to samples from a different entropy/window as a latency estimate.

Defer a standalone fixed-chain implementation. No runtime or timing candidate
was built. The first occupied-lock attempt remains closed with zero work.
A broader branch-aware reservation model would need explicit per-edge refunds
and their dispatch costs. It must account for those costs before any production
decision, rather than assuming all potential budget samples disappear.
