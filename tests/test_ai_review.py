import json
from io import BytesIO

import pytest

from tools.ai_review import _validate_findings, request_review, sanitize_diff


def test_sanitize_diff_excludes_sensitive_paths_and_redacts_credentials():
    diff = (
        "diff --git a/app/sample.py b/app/sample.py\n"
        "--- a/app/sample.py\n"
        "+++ b/app/sample.py\n"
        "@@ -1 +1 @@\n"
        '-API_KEY = "example-credential-value"\n'
        '+message = "safe change"\n'
        "diff --git a/.env b/.env\n"
        "--- a/.env\n"
        "+++ b/.env\n"
        "+PASSWORD=do-not-send-this\n"
        "diff --git a/keys/private.pem b/keys/private.pem\n"
        "--- a/keys/private.pem\n"
        "+++ b/keys/private.pem\n"
        "+private key material\n"
    )

    sanitized = sanitize_diff(diff)

    assert "app/sample.py" in sanitized
    assert "safe change" in sanitized
    assert "example-credential-value" not in sanitized
    assert "do-not-send-this" not in sanitized
    assert "private key material" not in sanitized


def test_sanitize_diff_redacts_token_shaped_and_high_entropy_strings():
    diff = (
        "diff --git a/app/sample.py b/app/sample.py\n"
        "--- a/app/sample.py\n"
        "+++ b/app/sample.py\n"
        '+token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"\n'
        '+value = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"\n'
    )

    sanitized = sanitize_diff(diff)

    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890" not in sanitized
    assert "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in sanitized
    assert "[REDACTED" in sanitized


def test_validate_findings_rejects_malformed_ai_response():
    with pytest.raises(ValueError, match="severity"):
        _validate_findings('{"findings":[{"title":"missing required fields"}]}')


def test_request_review_parses_openai_compatible_response(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "local-test-key")
    monkeypatch.delenv("AI_API_URL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://api.openai.com/v1/chat/completions"
        assert timeout == 45
        body = json.loads(request.data.decode("utf-8"))
        assert body["model"] == "gpt-4o-mini"
        return BytesIO(
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "findings": [
                                            {
                                                "severity": "medium",
                                                "file": "app/sample.py",
                                                "line": "12",
                                                "category": "Bug",
                                                "title": "Handle missing value",
                                                "recommendation": "Return a 404 response.",
                                            }
                                        ]
                                    }
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("tools.ai_review.urllib.request.urlopen", fake_urlopen)

    findings = request_review("safe diff")

    assert findings[0]["title"] == "Handle missing value"
    assert findings[0]["recommendation"] == "Return a 404 response."


def test_request_review_rejects_non_https_endpoint(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "local-test-key")
    monkeypatch.setenv("AI_API_URL", "http://example.invalid/api")

    with pytest.raises(ValueError, match="HTTPS"):
        request_review("safe diff")
