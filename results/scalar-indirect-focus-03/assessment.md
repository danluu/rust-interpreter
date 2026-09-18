# Complete-memory observer import did not compile

The first memory-control command stopped at a syntax error before any test ran.
The import of the previously qualified snapshot helper ended at its nested
`struct Enabled` marker rather than the outer model marker, truncating the helper.
Restore the complete exact helper from its historical source and retain this
failure. No production execution mechanism or guest benchmark changed.
