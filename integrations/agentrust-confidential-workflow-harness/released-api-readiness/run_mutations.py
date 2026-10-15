"""Bounded process-local gate weakenings; installed distributions stay untouched."""
from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from cmcp_runtime.disclosure import DisclosureGate, ReplayStore
from test_released_apis import ReleasedDisclosure, ReleasedResponses


def run(case, method):
    result = unittest.TextTestRunner(stream=io.StringIO()).run(
        unittest.TestSuite([case(method)])
    )
    if result.errors:
        raise AssertionError(result.errors)
    return result


cases = [
    ("response MAC bypass", patch("ca2a_runtime.response.hmac.compare_digest", return_value=True),
     ReleasedResponses, "test_tampered_body_refuses", "test_valid_response_remains_software_assurance"),
    ("disclosure expiry bypass", patch.object(DisclosureGate, "_validity", return_value=None),
     ReleasedDisclosure, "test_exact_expiry_refuses_without_delivery", "test_signed_exact_output_delivers_once"),
    ("disclosure replay bypass", patch.object(ReplayStore, "consume", return_value=True),
     ReleasedDisclosure, "test_replay_does_not_deliver_twice", "test_signed_exact_output_delivers_once"),
]
for name, mutation, case, negative, positive in cases:
    with mutation:
        refused = run(case, negative)
        admitted = run(case, positive)
    assert len(refused.failures) == 1, (name, refused)
    assert admitted.wasSuccessful(), (name, admitted)
    print(name + ": negative caught weakening; valid control passed")
print("3/3 targeted weakenings detected; no installed source changed")
