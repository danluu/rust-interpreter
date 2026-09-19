# Hash prerequisite controls 05

All 66 pure controls passed in one test process, followed by an independent audit of all 18 frozen inputs, raw test names, receipts and supervisor closure. This suite contains nine command-history controls, 29 wrapper/reconciliation controls and 28 snapshot-binding controls. It retains all 63 existing test methods and adds three focused historical-order regressions. No compiler or provider workload ran.

The first read-only hash preparation stopped before producing a plan or launch packet. Its generic reader incorrectly required the historical snapshot selection list to be serialized in sorted order. Both audited historical preparers sort their names and then append `plan.json`; their snapshot writers sort the unique names during reconstruction. The complete logical records, identities, projection and manifest mappings were intact.

The correction requires a list of unique strings, membership in the original freeze and exclusion of the freeze itself, then reconstructs the sorted records. Full projection, manifest, identity, blob, receipt, audit and allocation checks remain in force. The new tests cover appended-plan order, arbitrary unique ordering and duplicate rejection for each owner. The new hash stage's own sorted-selection contract and all resource thresholds are unchanged.

The complete failed first preparation source/raw/record and three partial provider catalogs are retained, along with original and corrected source, diffs, reviews, actual66 raw evidence, bounded launcher and independent audit execution. Second-preparation outputs are outside this publication; its reviewed source and predecessor references are retained as source only. Native03's original failed receipt and the separately passed read-only reconciliation retain their distinct meanings.

`manifest.json` maps each byte copy to its original absolute path, content hash and observed source identity. Copies are independent ordinary files; originals remain unchanged and copied inode identities do not replace historical observations. All 18 frozen input payloads are present, including exact identity-tool and Python executable bytes as evidence only. The wrapper's missing independent PS/cwd observation is explicit, and any fast-child cwd limitation is retained in the summary and audit.

These controls do not execute or qualify the three-command hash workload and establish no application timing or sub-0.5-second result.
