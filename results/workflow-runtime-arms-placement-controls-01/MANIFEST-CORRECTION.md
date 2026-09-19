# Publication index correction

The original manifest.json was indexed after opening its own output file, so its self-row incorrectly records zero bytes and the empty SHA-256. That original manifest is preserved unchanged at 2,636 bytes and SHA-256 560b97e8fd3d788c5b4f55a0b32cb678bc50ac98b959d99db4fa0e6036f2f7d0. Its other nine rows match the retained files.

manifest-02.json indexes all ten original files and this note using their actual bytes. It deliberately excludes itself. No test, source, raw output, or execution record was changed, and the 13-test suite was not rerun.
