The candidate passes all 114 original pgrust parser tests, including reference
vectors, using the exact bytecode and catalog from the qualified current
compiler. The retained native 114-test control is revalidated. No source or
assertion is changed; all 4,958 frozen inputs verify. Two prepared workers and
the default 16 MiB native code limit remain unchanged. This is one compatibility
command, not performance evidence. The earlier 45-second lock refusal ran no
guest command and remains recorded.
