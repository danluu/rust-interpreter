# Standard-library adapter source and development checks

The adapter passed 12 focused tests once. Independent source review verified
that it runs the original standard-library CLI with the selected runtime loader,
preserving the original module path, supervisor body and ordinary arguments.
The tests use temporary fixtures and do not prepare a standard library.

This capsule retains the exact tested sources, raw output, closure and reviews,
including the initial draft and its correction before the test execution.
The plan is unbound in this snapshot. No standard-library, exporter, application
or performance result is claimed. Runtime installation and its audit have
separate records; later binding must consume their actual completed results.
