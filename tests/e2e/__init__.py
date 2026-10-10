"""System-level (end-to-end) tests: the `autocv` CLI exercised as a whole.

Each test drives real components — CVML/profile parsing, the workflow's
prompt building, retry/validation logic, and PDF rendering — end to end
through the CLI. Only the outermost boundary (the `claude` subprocess) is
replaced with a scripted double, since these tests must be deterministic
and network-free; see `route_by_role` in `conftest.py`.
"""
