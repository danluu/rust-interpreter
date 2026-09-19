# Qualified feature-enabled VM with retained passing workspace evidence

Reconstructed and reused the three closed passing commands from workspace01:
446 Python tests with22 skips, and622 Rust tests with13 ignores in each debug
and release profile. Every frozen source hash remained unchanged. No test was
repeated.

The one previously unstarted release VM build passed after fresh disk admission;
its binary and explicit Cargo feature are retained and independently closed.
VM SHA-256:887b8b138519f79abff80c9ea61477c7cb1a6f708e79efb14e8e89a05af53849.
The installed/default runtime is unchanged. Original-suite profiles and the real
changed-source primary/full guards are still required before adoption.
