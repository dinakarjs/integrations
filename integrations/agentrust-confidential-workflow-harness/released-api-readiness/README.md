# Released API readiness probes for integrations #199

Supplemental review evidence, not protocol-adapter ownership or completion of
#199. Uses released cmcp-runtime 0.7.0 and ca2a-runtime 0.4.0. No runtime source,
scenario contract, release target in the harness, or production setting changes.

## Reproduce

From this directory on Python 3.12:

```sh
python -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.txt
.venv/bin/python -m unittest discover -s . -p 'test_released_apis.py' -v
.venv/bin/python run_mutations.py
```

The hash lock was resolved for Python 3.12.14. Package hashes authenticate package
bytes against the selected index; they do not establish package safety or
cross-platform dependency compatibility. No test imports an unreleased checkout.

The inspected wheel SHA-256 values are:

- cmcp_runtime-0.7.0-py3-none-any.whl:
  3728a2ade10b7239b81815b2708900d4cfc6b9110091d58d19e62a93904dd06e
- ca2a_runtime-0.4.0-py3-none-any.whl:
  f87a235c2fb31d2bf496e24223f5d95ee2efbca743e89c8ced22a6c87fd18bd5

## Executed scope

14 probes pass:

- cA2A PendingResponse/ResponseProducer: valid software-assurance response,
  tampered body, cross-request substitution, replay, exact expiry, and consumption
  after failed verification, plus installed-version assertions.
- cMCP DisclosureGate: approved exact bytes, changed payload, absent approval,
  changed policy, exact expiry, replay and a callback timeout retaining unknown
  delivery with no automatic second delivery.

Three isolated process-local weakenings are detected while their valid controls
still pass: response MAC comparison, disclosure expiry, and replay reservation.
No weakening edits an installed distribution. This is a bounded sample, not a
complete gate-removal matrix.

The existing deterministic harness separately passes 27 tests at integrations
84d15305fd9d1a4556afc91396d8ff2615f96081. These release
API probes do not wire its adapters or establish one composed transaction.

## Proposed adapter handoff

| Boundary | Released API | Observation rule |
|---|---|---|
| Peer response | PendingResponse.verify | Expose content only after authentication; preserve assurance=none and live-caller-only audience. |
| Exact-output release | DisclosureGate.release | Carry disposition and delivery separately; authorized_disclosure is not proof of delivery. |
| Sink timeout | ReleaseObservation.delivery | Preserve unknown; do not infer no side effects or retry automatically. |
| Restart/recovery | Process-local PendingResponse, trusted ReplayStore | State loss is not replay permission; persistent storage does not establish rollback resistance. |

Actual cMCP mediated-call/confinement wiring, cA2A transport/delegation wiring,
transaction-context binding, release-version selection by the harness owner,
full paired refusal/mutation coverage, live peers and hardware remain open.
Random synthetic test keys and request occurrences are generated in memory;
asserted outcomes are stable, but cryptographic transcripts are not claimed
byte-identical. Public fixtures contain no protected payloads or device IDs.

Ownership coordination: Imran asked Val (@altrudev) on October 15 whether he is
retaining the protocol adapters. This supplement is prepared for integration or
independent review after that answer; it makes no competing ownership claim.
