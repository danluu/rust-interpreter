# Effective native test profiles

Fifteen Cargo unit-graph queries passed across the five pinned projects. They executed no compiler or test.

| Project | Repository debuginfo | Split debuginfo | Distinct presets |
| --- | --- | --- | ---: |
| fre | full | unpacked | 3 |
| pgrust | line-tables-only | unpacked | 2 |
| Nushell | full | unpacked | 3 |
| Ruff | line-tables-only | unpacked | 2 |
| rg-aot | full | unpacked | 3 |

The prescribed alternatives are line-tables-only/unpacked and debug=0/unpacked. Debug=0 also makes Cargo resolve stripping to debuginfo; symbol stripping is not enabled. All other root profile fields match. Thus line-tables-only is a duplicate control for pgrust/Ruff, and unpacked split debuginfo is already present everywhere.

The first query attempt stopped when its overly strict guard encountered Cargo's automatic stripping change. The second records that change explicitly. Raw private unit graphs remain local; the summary exposes only profile settings and counts. These are effective settings, not timing results.
