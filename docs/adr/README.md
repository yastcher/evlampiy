# Architecture decisions

A decision that is still in force and has a reason is written here, one file per
decision: `ADR-NNN-<the-decision-as-a-phrase>.md`. Specs in `docs/spec/` describe their own
day; this folder describes what holds now.

Sections: Status (the date and the files that implement it), Context, Decision, Why,
Consequences. A decision that changes keeps its text and gains a dated line,
"Now (date): …", or a new ADR that names the old one.

- [ADR-002](ADR-002-pii-is-masked-where-each-llm-client-hands-a-request-to-providers.md) — PII is masked where each LLM client hands a request to its providers.
