"""Exercise the demo recipient's sealed-release path with synthetic software evidence."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from wcm import SealError, SoftwareProvider, generate_transport_keypair

ROOT = Path(__file__).resolve().parent.parent
DEMOS = ["demo-06-weight-custody", "demo-07-closed-weight", "demo-09-sovereign-threshold"]


def load_demo(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / name / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", DEMOS)
def test_recipient_consumes_channel_bound_release(name, capfd):
    load_demo(name).main()
    out = capfd.readouterr().out
    if "06" in name:
        assert "gate released key  : True" in out
        assert "custody active" in out
    elif "07" in name:
        assert "approved enclave    : key released = True" in out
        assert "unapproved enclave  : key released = False" in out
    else:
        assert "quorum reconstructs the key : True" in out


@pytest.mark.parametrize("name", DEMOS)
def test_missing_transport_binding_cannot_release(name, monkeypatch):
    original = SoftwareProvider.produce

    def without_binding(self, *args, **kwargs):
        kwargs.pop("transport_public_key", None)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(SoftwareProvider, "produce", without_binding)
    with pytest.raises(RuntimeError, match="channel-bound sealed"):
        load_demo(name).main()


@pytest.mark.parametrize("name", DEMOS)
def test_wrong_recipient_private_key_cannot_consume(name, monkeypatch):
    demo = load_demo(name)

    def mismatched_keys():
        _, public = generate_transport_keypair()
        private, _ = generate_transport_keypair()
        return private, public

    monkeypatch.setattr(demo, "generate_transport_keypair", mismatched_keys)
    with pytest.raises((ValueError, SealError)):
        demo.main()
