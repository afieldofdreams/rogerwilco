"""rogerwilco: one-line typed messages for handing work between AI agents, with a readback the sender checks in code.

    import rogerwilco as rw
    rb = rw.make_rb(ho_line, "payer-1", "pay")              # the receiver's readback, with h=
    problems, notes = rw.check_rb_full(ho_line, rb, "pay")  # the sender's check: empty problems means roger, wilco

The reference codec lives in scripts/rogerwilco.py (standard library only) and is re-exported here.
"""
from .scripts.rogerwilco import (  # noqa: F401
    VERSION, PROFILES, FormError, load_core, load_profile, parse, validate, encode, to_json, from_json,
    canonical, digest, compare_acc, check_rb_full, check_rb, make_rb, legend,
)

__all__ = [
    "VERSION", "PROFILES", "FormError", "load_core", "load_profile", "parse", "validate", "encode", "to_json",
    "from_json", "canonical", "digest", "compare_acc", "check_rb_full", "check_rb", "make_rb", "legend",
]
