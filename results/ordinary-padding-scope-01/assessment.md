One release metadata extraction passed (PID 51870, 19.3115 s). Attribution then
failed its extra assertion that the padding helper began at span offset zero.
The exact typed ordinary call_frame_clear span also owns four preceding setup
instructions, so the exact13-word helper begins at byte16. This is an observer
boundary mistake, not a runtime or guest failure. No guest ran or code was
published. Independent closure preserved the terminal failure, successful child,
raw typed metadata and source bindings. No performance conclusion is supported.

Resume by qualifying the four setup words and reusing this successful metadata
output; do not replay its compiler child to repair attribution. The remaining
three captures have not been extracted. Retain this closed failure unchanged.
