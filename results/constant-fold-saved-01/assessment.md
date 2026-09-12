All three saved artifacts transformed and passed exact whole-artifact verification;
no guest execution occurred. Raw inputs remain unchanged. Final operation counts
fell from 1,313,023 to 1,274,315 in token, 292,656 to 263,508 in folded, and 8,839
to 7,387 in pgrust. Diagnostic transformation times were 0.280, 0.168 and 0.005 s;
these are not complete edited-source commands or runtime speedups.

The token pass consumed all 32 million analysis units, leaving 4,427 of 5,468
functions unchanged through a decline. Folded declined 77 of 1,048 functions;
pgrust declined none. ID-order budget allocation is an avoidable limitation.
Before any end-to-end timing, prioritize smaller bodies under the same fixed
budget, using stable IDs for ties and preserving ID-order reports. No profiling
information or project/function-name rule enters the compiler.
