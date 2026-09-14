# Compile-only failure

The first focused build failed before any unit test ran: two existing manual
ResumeCursor fixtures omitted the new optional scalar-profile table pointer.
They exercise ordinary resumable code and must supply null. No generated guest
code ran, and no qualification or performance result is claimed. Source,
terminal, plan and build-output hashes are retained. The corrected revision
uses a new run identity.
