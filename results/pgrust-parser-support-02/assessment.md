# Parser support after boxed-callback fix

One new custom command selected all114 original parser test bodies with tool
`15574904`. The successful native114-test command was reused after executable,
source, inventory and log validation. Project source/assertions/profile settings
remain unchanged; all4,918 frozen inputs verify after the new command.

The exporter gets past the previous boxed FnOnce failure, then exits101 with
`function expansion limit reached`. It produces no guest suite report; no
parser guest test executes. This is a support limitation, not a timing result.
Inspect actual registered/lowered/indirectly retained functions before deciding
whether the10,000-function guard is too small or avoidable expansion dominates.
Keep the full parser selection and original assertions.
