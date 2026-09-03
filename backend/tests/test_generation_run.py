from app.agent.run import _sanitize_error


def test_sanitize_error_redacts_secret_values():
    message = "Provider rejected api key sk-secret-value with status 401"
    sanitized = _sanitize_error(message, secrets=["sk-secret-value"])

    assert "sk-secret-value" not in sanitized
    assert "[REDACTED]" in sanitized


def test_sanitize_error_ignores_empty_secret_inputs():
    message = "plain error"
    sanitized = _sanitize_error(message, secrets=["", "   "])

    assert sanitized == message
