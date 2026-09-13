The first original native control passes all 12 token tests. The driver then
fails to capture its executable because it assumes the library is at the
workspace root; Cargo correctly reports the nested `fre-kernels` member. No
candidate commands or edited pairs ran, and there is no performance result.

The serialized audit verifies the exact original command, source pin,
restoration and every frozen input, then retains the actual native executable
and all outcomes in a new audit record. Original raw failure files are unchanged.
The repaired continuation will reuse this control and its native cache, and run
only the 39 unstarted commands under the same schedule and criteria.
