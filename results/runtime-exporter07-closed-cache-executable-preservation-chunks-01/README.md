Two ordered parts reproduce the unchanged 274-file preservation archive.

```sh
cat evidence.tar.gz.part-000 evidence.tar.gz.part-001 > evidence.tar.gz
shasum -a 256 evidence.tar.gz
```

Expected SHA-256: 0e14806dfba6261e9bb254c506321b81a1f934de95b41c7339465a07b03786e5
Expected size: 121209508 bytes. The original archive remains retained.
Historical metadata is copied under provenance; retirement passed separately.
