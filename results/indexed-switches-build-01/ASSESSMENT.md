The first debug test compilation failed because the new synthetic Program
fixture omitted its empty statics and thread_locals fields. No tests or project
guest commands ran and no candidate was installed. Fix those fixture fields
under a new run ID; retain the compiler diagnostic and frozen-source closure.
