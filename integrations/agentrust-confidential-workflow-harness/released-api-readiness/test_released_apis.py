"""Offline release API probes; not integrated workflow or hardware acceptance."""
from __future__ import annotations

import importlib.metadata
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from ca2a_runtime.attestation import VerifiedPeer
from ca2a_runtime.errors import ResponseAuthenticationFailed
from ca2a_runtime.response import PendingResponse, ResponseProducer, decode, encode
from cmcp_runtime.disclosure import (
    DisclosureGate,
    ReleaseAuthority,
    ReleaseRecipient,
    ReleaseRequest,
    ReplayStore,
    approve_exact_output,
)


class ReleasedResponses(unittest.TestCase):
    def setUp(self):
        self.private = X25519PrivateKey.generate()
        self.peer = VerifiedPeer(self.private.public_key().public_bytes_raw().hex(),
                                 "none", "synthetic-test-measurement")
        self.now = 10.0

    def exchange(self):
        pending = PendingResponse(self.peer, {"task": "public-fixture"},
                                  timeout=5, clock=lambda: self.now)
        producer = ResponseProducer(self.private, decode(pending.request_bytes))
        return pending, producer

    def test_release_versions(self):
        self.assertEqual(importlib.metadata.version("cmcp-runtime"), "0.7.0")
        self.assertEqual(importlib.metadata.version("ca2a-runtime"), "0.4.0")

    def test_valid_response_remains_software_assurance(self):
        pending, producer = self.exchange()
        result = pending.verify(200, encode(producer.finish(200, {"accepted": True})))
        self.assertEqual(result.peer_assurance, "none")
        self.assertEqual(result.authentication()["audience"], "live-caller-only")

    def test_tampered_body_refuses(self):
        pending, producer = self.exchange()
        response = producer.finish(200, {"accepted": True, "value": "original"})
        response["body"] = {"accepted": True, "value": "substituted"}
        with self.assertRaises(ResponseAuthenticationFailed):
            pending.verify(200, encode(response))

    def test_cross_request_response_refuses(self):
        first, producer = self.exchange()
        second, _ = self.exchange()
        self.assertNotEqual(first.request_sha256, second.request_sha256)
        with self.assertRaises(ResponseAuthenticationFailed):
            second.verify(200, encode(producer.finish(200, {"accepted": True})))

    def test_replay_refuses(self):
        pending, producer = self.exchange()
        response = encode(producer.finish(200, {"accepted": True}))
        pending.verify(200, response)
        with self.assertRaises(ResponseAuthenticationFailed):
            pending.verify(200, response)

    def test_exact_deadline_refuses(self):
        pending, producer = self.exchange()
        self.now = 15.0
        with self.assertRaises(ResponseAuthenticationFailed):
            pending.verify(200, encode(producer.finish(200, {"accepted": True})))

    def test_failed_verification_consumes_occurrence(self):
        pending, producer = self.exchange()
        response = encode(producer.finish(200, {"accepted": True}))
        with self.assertRaises(ResponseAuthenticationFailed):
            pending.verify(500, response)
        with self.assertRaises(ResponseAuthenticationFailed):
            pending.verify(200, response)


class ReleasedDisclosure(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.deliveries = []
        self.now = 100
        self.signer = Ed25519PrivateKey.generate()
        self.request = ReleaseRequest(b"public fixture bytes", "workload", "scope",
                                      ("secret",), "recipient", "purpose", "policy-v1")
        self.gate = DisclosureGate(
            policy_version="policy-v1", source_scopes=frozenset({"scope"}),
            sensitivity_order={"public": 0, "secret": 1},
            recipients={"recipient": ReleaseRecipient("public", "external", self.deliveries.append)},
            authorities={"owner": ReleaseAuthority(self.signer.public_key(),
                frozenset({"scope"}), frozenset({"recipient"}), frozenset({"purpose"}))},
            replay_store=ReplayStore(Path(self.temp.name)/"replay.db"), now=lambda: self.now,
        )
        self.approval = approve_exact_output(self.request, principal="owner", key=self.signer,
                                             not_before=100, expires_at=110)

    def test_signed_exact_output_delivers_once(self):
        result = self.gate.release(self.request, self.approval)
        self.assertEqual((result.disposition, result.delivery),
                         ("authorized_disclosure", "acknowledged"))
        self.assertEqual(self.deliveries, [self.request.payload])

    def test_payload_substitution_refuses_without_delivery(self):
        result = self.gate.release(replace(self.request, payload=b"changed"), self.approval)
        self.assertEqual(result.reason, "approval_binding")
        self.assertEqual(self.deliveries, [])

    def test_missing_approval_is_unavailable_without_delivery(self):
        result = self.gate.release(self.request)
        self.assertEqual(result.disposition, "unavailable")
        self.assertEqual(self.deliveries, [])

    def test_policy_substitution_refuses_without_delivery(self):
        result = self.gate.release(replace(self.request, policy_version="policy-v2"), self.approval)
        self.assertEqual(result.reason, "policy_mismatch")
        self.assertEqual(self.deliveries, [])

    def test_exact_expiry_refuses_without_delivery(self):
        self.now = 110
        result = self.gate.release(self.request, self.approval)
        self.assertEqual(result.reason, "approval_expired_or_early")
        self.assertEqual(self.deliveries, [])

    def test_replay_does_not_deliver_twice(self):
        self.gate.release(self.request, self.approval)
        result = self.gate.release(self.request, self.approval)
        self.assertEqual(result.reason, "replay")
        self.assertEqual(self.deliveries, [self.request.payload])

    def test_sink_failure_preserves_unknown_delivery(self):
        attempts = []

        def failing_sink(payload):
            attempts.append(payload)
            raise TimeoutError("test-only failure")

        self.gate._recipients = {"recipient": ReleaseRecipient("public", "external", failing_sink)}
        result = self.gate.release(self.request, self.approval)
        self.assertEqual(result.delivery, "unknown")
        self.assertEqual(result.reason, "delivery_unknown")
        self.assertEqual(attempts, [self.request.payload])
        self.assertEqual(self.gate.release(self.request, self.approval).reason, "replay")
        self.assertEqual(len(attempts), 1)


if __name__ == "__main__":
    unittest.main()
