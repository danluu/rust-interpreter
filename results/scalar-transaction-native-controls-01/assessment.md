# First native-store build stopped at test compilation

The source-frozen debug command found a missing new field in the existing
emitter test constructor and two tests reaching a private operation-map method.
No native store control executed. Preserve the closed failure, update that
constructor and expose a test-only serialized map helper, then retry separately.
