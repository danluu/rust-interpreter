# Preserved observer compile failure

The initial isolated observer build failed at two Load/Store width conversions (`u8` to `usize`). No candidate tool was published and no benchmark ran. Explicit lossless conversions fixed both sites; build-02 passed all 35 tests. This receipt and its original source/logs remain unchanged.
