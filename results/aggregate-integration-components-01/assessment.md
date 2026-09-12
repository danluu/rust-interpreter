# Normal aggregate compiler component rebuild

A fresh ordinary release build of the qualified compiler source reproduces all three installed component hashes exactly: VM `21d1e163`, exporter `556776f6`, wrapper `ba366dd3`. No component was copied into this new target or substituted in the installed tool.

The next step is exact source integration followed by normal workspace checks and a fresh root build. This rebuild is identity evidence, not a new performance measurement.
