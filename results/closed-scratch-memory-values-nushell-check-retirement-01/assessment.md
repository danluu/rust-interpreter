# Source fixture stops cleanup preflight

The generic hash-binding helper attempted to parse an intentionally invalid JSON
fixture in Nushell's source tree. It stopped before creating an inventory or
entering the deletion phase; no compiler intermediate was removed. Source
fixtures need exact byte hashing, while named metadata documents need parsing.
A fresh run will make that distinction explicit and preserve these logs.
