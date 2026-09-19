# Preserved first profile and observer failure

Source877cfddf passed six Python controls and the first original guest.
PID60173 returned0 with exact adopted logical counts, peak memory and entropy,
zero JIT declines and a complete reconstructed operation map. Supervisor
60138/child60168 then failed the additional native byte comparison. The other
two guests never started.

The observer accepted only the bare `Call` label; real profiles render
`Call { function: ..., args: ..., destination: ... }`. It consequently
normalized zero scalar sites. All854 different words were in Call transitions.
The native layouts and PC execution arrays already matched. This is an observer
recognition error, not an observed guest failure or timing result.

The closure preserves all four capture files, frozen source bindings and logs.
A corrected observer must revalidate this exact capture before running only
the two unstarted profiles. Add an operand-rendering regression control; keep
the native comparison contract and runtime binary unchanged.
