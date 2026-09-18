# Single-operation register cleanup has little sampled coverage

Fourteen controls pass, and both exact adopted native captures reconcile all
generated-PC samples. The conservative recognizer finds 20,985 / 25,433 static
dead pure definitions within individual operation spans, but only 6 / 4 saved
self-PC samples at those words out of 1,561 / 1,231. No collapsed samples have
mixed candidate status. Memory operations, branches, unknown instructions and
all final register values remain observable.

Do not implement a runtime pass from these small sample counts. The next census
will test whether calculations become dead across adjacent bytecode operations
inside one native region. Preserve every region and control-flow boundary, keep
unknown encodings conservative, and require the narrower candidates to remain a
subset. No build, guest execution or code publication occurred.

The closure verifies 68 source/artifact bindings. Detailed sites remain under the
summary's local raw path and hash. [Summary](summary.json), [closure](closure.json).
