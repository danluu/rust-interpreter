# Heap layout metadata: primary failed, candidate parked

All40 whole commands and2 strict unreachable type/borrow probes completed with
original12-test outcomes preserved, matching candidate/control artifacts and
restored source. Independent closure rederived the complete history and gate.

| Edited-command ratio | Candidate/adopted | A/A envelope | Ratio + margin |
| --- | ---: | ---: | ---: |
| Wall | 0.981239792 | 0.051989623 | 1.033229416 |
| CPU | 0.979778617 | 0.040559047 | 1.020337664 |

The nominal1.88% wall decrease does not clear5.20% A/A variation. CPU gates pass,
but the wall gate fails. The verdict is failed (A/A remains below the existing8%
unmeasurable threshold). Candidate/native wall ratio is1.625525;
CPU ratio is2.029024. These results do not establish a speedup.

Park tool da1779094da6a44c2ff63cae3767e18407050a63f54380465a9fb7fb51d70db1.
Cancel all unstarted heap-layout full/public/private/parser/Nushell guards. No
unchanged repeat, gate relaxation or runtime default change. Keep the exact
allocator controls, source-bound workspace/profile results, ASLR relocation proof
and all earlier controller/resource failures. Runtime source remains on the
experimental branch; subsequent candidates start from adopted fca687eb.
