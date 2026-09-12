The first compiler qualification stopped on one new test's invalid input:
it supplied a full-u128 value to a narrower entry argument. Both existing and
scalar execution deliberately reject that input. The other eleven new compiler
tests passed. This was a harness expectation error, not an observed execution
miscompile. No release qualification or performance measurement ran.

The exact source, logs and terminal supervisor/controller chain are retained
in execution.json. Revision 2 supplies in-range inputs and separately asserts
oversized entry rejection. It also narrows capture's visibility to remove the
private-interface warning. The transformation algorithm is unchanged.
