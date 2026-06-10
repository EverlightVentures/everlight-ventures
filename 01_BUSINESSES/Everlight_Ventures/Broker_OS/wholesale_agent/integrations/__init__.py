"""External integrations for the wholesale pipeline.

Every client in this package returns a typed dataclass and never raises on
missing credentials. Callers must check `.ok` on results before using data.
"""
