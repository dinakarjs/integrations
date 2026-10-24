# Retained execution evidence

`tested_against` is a declaration. A version floor check alone does not show
that a command ran against those versions. The opt-in recorder links an
explicit command to a source revision, installed distribution versions,
manifest digest, timestamps, exit status and the digest of its retained log.

Run from a clean checkout in the same environment that runs the test:

```sh
python scripts/test_evidence.py capture \
  --integration integrations/<name> \
  --output /tmp/integration-evidence \
  --evidence-class synthetic \
  -- python -m pytest integrations/<name>/tests -q
python scripts/test_evidence.py check /tmp/integration-evidence
```

The output directory must be new and outside the checkout (or ignored by Git).
Use a unique directory per run. Only explicitly requested Python commands run;
the tool does not discover or execute vendor code. Dependencies are installed
by the caller from existing released-package locks. It records installed
metadata, so tests that switch environments or install dependencies internally
are outside its supported model. Use the same interpreter throughout.

In an integration's existing GitHub workflow, wrap its current Python test
command, then upload the entire directory with `if: always()` and an explicit
retention period. Both `receipt.json` and `output.log` are needed. The recorder
captures the Actions run URL when running in Actions. A timeout or failed test
still produces a receipt and a failing command status. Do not upload logs that
contain credentials or sensitive workload data.

The check returns `consistent` only for a clean matching revision, unchanged
manifest, exact declared/installed versions, successful command and matching
log digest. Missing evidence, undeclared dependencies, failed runs and stale
or mismatched content fail the check. A declaration without a receipt remains
declaration-only; absence does not prove the integration was never tested.
Evidence expiry after artifact retention likewise requires a new run.

Evidence class is explicitly chosen: synthetic fixtures, captured evidence,
or live operation. The tool cannot independently verify that classification.
Receipts are unsigned local observations, not attestations: a digest catches
accidental substitution but not someone rewriting both receipt and log.
Review command coverage and trusted CI provenance separately. A successful
command can run zero tests; the tool does not infer conformance or completeness.
Neither a consistent receipt nor a passing test changes community/verified
tiers, compatibility floors, or maintainer approval requirements.

The recorder tests exercise real subprocess success, failure and timeout plus
missing evidence, changed manifests, mismatched versions/revisions and log
substitution. Run `python -m pytest tests/test_test_evidence.py -q`.

The proposed expansion wraps the existing Google ADK and LlamaIndex test commands.
It preserves their dependency installation, fixture-only execution and tiers.
Google ADK inherits TRACE from the first installation pass; LlamaIndex uses its
existing exact interop requirements. LlamaIndex additionally installs the existing
hash-locked maintenance dependency (PyYAML) for the recorder. Both jobs retain
receipts/logs for 30 days and run the consistency check even after command failure.
A stale declaration is a failing result, not grounds to skip the check.

Local reproduction for this expansion: Google ADK 40 tests pass with TRACE
0.11.0 and trace-tests 0.5.1; its prior 0.10.0 declaration is corrected to the
observed version. LlamaIndex 63 tests pass with its existing TRACE 0.9.0 and
trace-tests 0.5.1 declaration. No tier or compatibility floor changes.
