"""Tool wrappers exposed to the agent runtime.

Each module here turns a numerical engine (solver or surrogate) into a
single `predict(scenario)` callable that takes a plain-dict scenario and
returns a common-schema dict of fields + grid metadata.
"""
