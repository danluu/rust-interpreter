# Coordinated function-count capacity

The complete parser census reaches10,009 registrations with9,995 required
bodies and only14 unused placeholders; it spans3,115 definitions. This does not
prove optimal reachability, but simply removing unneeded handles is inadequate.
Use a shared finite32,768-function admission count for lowering, cache read and
write, and optional per-function cost/reuse observers. Keep128MiB cache-file,
64MiB per-payload and16MiB observer-report bounds unchanged. Match inclusive
count admission in the pre/post-lowering checks. No scheduling or guest ABI
change, source reduction, alternate backend or performance claim.

Add a cache round-trip at10,001 and32,768 entries, then independently construct
a correctly checksummed32,769-entry file to verify reader rejection as well as
writer rejection. Run89 exporter tests per profile, retain the exact qualified
VM/wrapper, and require the original boxed callback/sized dispatch qualification.
Run the complete original114-entry parser command in a new owned namespace,
reusing the sealed successful native proof. Keep failure diagnostics and any
next support failure. If support succeeds, qualify original/edited/restored
source under matching native/custom incremental profiles before timing claims.

Shared45-second benchmark admission, two Cargo jobs,12GiB build admission and
16GiB parser admission,8GiB each command. No other sessions, tools, source trees
or processes are changed. Do not publish an unqualified capacity experiment.
