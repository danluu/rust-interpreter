# Controller preflight failure

No build, test or guest command started. The input check incorrectly expected
the parked primary closure to use the census closure schema. Its terminal log
and exact controller revision are retained. Correct the schema check and use a
new run identifier; this result says nothing about the store-log code.
