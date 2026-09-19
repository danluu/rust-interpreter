# Retire completed primary03 and strict-control intermediates

Audit all three closed40-command session parser histories, then retire only the
five primary03 compiler caches and the three separate strict-control namespaces.
Primary01/02 measured caches were already retired and are excluded. Keep all
executables, artifacts, catalogs, source, proofs and frozen inputs; delete only
nonexecutable compiler intermediates under the existing exact suffix/path rules.
No shared build target, installed tool, source or peer cache is eligible.

Strict namespace derivation requires byte-bound historical launcher source and
exact strict commands differing from the observed candidate only in report path
and namespace. Cross-check the same derivation against the observed successful
workspace. Both strict controls must reject with original diagnostic codes and
next session sequence1, without reports. This proves the selected scope rather
than inferring ownership from cache age or names.

Hold benchmark and each invocation lock; check successful owned supervisors,
original outcomes/restoration, all retained hashes and historical source bindings.
Reject unexpected open files and replacement symlinks. Record exact inode/device/
size/mtime/mode before each unlink; preserve a protected-file manifest and verify
all hashes after deletion and again at closure. No signaling, guest or compiler
commands.8GiB floor. Host free-space change is not an exact physical-byte claim.
