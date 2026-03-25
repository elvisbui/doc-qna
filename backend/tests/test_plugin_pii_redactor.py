"""Tests for the PII redactor plugin."""

import pytest

from app.plugins.pii_redactor import PIIRedactorPlugin


@pytest.fixture
def plugin() -> PIIRedactorPlugin:
    return PIIRedactorPlugin()


# ---- Email -----------------------------------------------------------------


@pytest.mark.parametrize(
    "email",
    [
        "alice@example.com",
        "bob.jones+work@company.co.uk",
        "user_123@sub.domain.org",
    ],
)
def test_email_redacted(plugin: PIIRedactorPlugin, email: str) -> None:
    result = plugin.on_chunk(f"Contact {email} for details.", {})
    assert "[EMAIL]" in result
    assert email not in result


# ---- Phone numbers ---------------------------------------------------------


@pytest.mark.parametrize(
    "phone",
    [
        "555-123-4567",
        "(555) 123-4567",
        "555.123.4567",
        "+1 555 123 4567",
        "15551234567",
    ],
)
def test_phone_redacted(plugin: PIIRedactorPlugin, phone: str) -> None:
    result = plugin.on_chunk(f"Call me at {phone} please.", {})
    assert "[PHONE]" in result
    assert phone not in result


# ---- SSN -------------------------------------------------------------------


@pytest.mark.parametrize(
    "ssn",
    [
        "123-45-6789",
        "000-00-0000",
    ],
)
def test_ssn_redacted(plugin: PIIRedactorPlugin, ssn: str) -> None:
    result = plugin.on_chunk(f"SSN: {ssn}", {})
    assert "[SSN]" in result
    assert ssn not in result


# ---- Credit card numbers ---------------------------------------------------


@pytest.mark.parametrize(
    "cc",
    [
        "4111111111111111",
        "4111 1111 1111 1111",
        "4111-1111-1111-1111",
    ],
)
def test_credit_card_redacted(plugin: PIIRedactorPlugin, cc: str) -> None:
    result = plugin.on_chunk(f"Card: {cc}", {})
    assert "[CREDIT_CARD]" in result
    assert cc not in result


# ---- IP addresses ----------------------------------------------------------


@pytest.mark.parametrize(
    "ip",
    [
        "192.168.1.1",
        "10.0.0.255",
        "255.255.255.255",
    ],
)
def test_ip_address_redacted(plugin: PIIRedactorPlugin, ip: str) -> None:
    result = plugin.on_chunk(f"Server at {ip}.", {})
    assert "[IP_ADDRESS]" in result
    assert ip not in result


# ---- Mixed content ---------------------------------------------------------


def test_mixed_pii(plugin: PIIRedactorPlugin) -> None:
    text = "Send to alice@example.com or call 555-123-4567. SSN 123-45-6789, card 4111-1111-1111-1111, host 10.0.0.1."
    result = plugin.on_chunk(text, {})
    assert "[EMAIL]" in result
    assert "[PHONE]" in result
    assert "[SSN]" in result
    assert "[CREDIT_CARD]" in result
    assert "[IP_ADDRESS]" in result
    assert "alice@example.com" not in result


# ---- No false positives ----------------------------------------------------


@pytest.mark.parametrize(
    "safe_text",
    [
        "The quick brown fox jumps over the lazy dog.",
        "Order #12345 was placed on 2025-01-15.",
        "Version 3.8.10 is now available.",
        "See section 12.4 for details.",
        "Total: $1,234.56",
    ],
)
def test_no_false_positives(plugin: PIIRedactorPlugin, safe_text: str) -> None:
    result = plugin.on_chunk(safe_text, {})
    assert result == safe_text


# ---- Plugin metadata -------------------------------------------------------


def test_plugin_name_and_description(plugin: PIIRedactorPlugin) -> None:
    assert plugin.name == "pii_redactor"
    assert plugin.description


def test_register() -> None:
    from app.plugins.pii_redactor import register

    instance = register(None)
    assert isinstance(instance, PIIRedactorPlugin)
