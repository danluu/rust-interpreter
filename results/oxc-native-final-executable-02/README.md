# Retained final Oxc native executable

This supplement preserves the exact final test executable from the completed [clean native history](../oxc-native-compatibility-02/README.md) before separately reviewed cleanup of its derived target directory. No compiler or test was run while creating this retention artifact.

The 107,592,208-byte executable has SHA-256 `978ad3e35b22d457ee8f8017d38290b6054c62850ee70a4b7365ab6e9a681751`, matching the final native receipt. An exclusive copy outside the target directory retained its bytes and mode on an independent inode. The original stamp and hash remained unchanged before and after copying and compression.

`evidence.tar.gz` contains the copied executable, its retention receipt and the exact native-cache assessment. All three regular members and the full gzip CRC/EOF were verified. This is additional byte retention for an existing successful run, not another native compatibility result or permission to remove any source, registry, toolchain or installed artifact.

- Retention receipt SHA-256: `8779faeabe21969a8c8c5fe625348038feb2fa55ee9acf88accd2eca1547bb00`.
- Archive: 26,892,816 compressed bytes; SHA-256 `abf80ca5c05c148c0cbe07a1327d8fbd75878c4b3f2f56c6150a63da808fc6a1`.
- Manifest SHA-256: `09e43ca9e40287affebd76f653e10215adcc2044360349dee9ee42e37478eb18`.
