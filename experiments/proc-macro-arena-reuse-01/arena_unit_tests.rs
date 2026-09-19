// Source only: future --test build includes the actual patched Arena and its seven tests.
// Requires the matching compiler/library APIs (cfg_select and push_mut are stable in this source).
#[path = "patched/arena.rs"]
mod arena;
