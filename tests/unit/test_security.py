from typing import Any
from uuid import uuid4

import httpx
import pytest

from lendup_reputation.config.settings import Settings
from lendup_reputation.domain.exceptions import (
    AuthenticationError,
    IdentityNotResolvedError,
    IdentityUnavailableError,
)
from lendup_reputation.infrastructure.security import FirebaseTokenVerifier, HttpIdentityResolver


class InvalidIdTokenError(Exception):
    pass


class ExpiredIdTokenError(InvalidIdTokenError):
    pass


class RevokedIdTokenError(InvalidIdTokenError):
    pass


class FakeAuth:
    InvalidIdTokenError = InvalidIdTokenError
    ExpiredIdTokenError = ExpiredIdTokenError
    RevokedIdTokenError = RevokedIdTokenError

    def __init__(self, result: dict[str, Any] | Exception) -> None:
        self.result = result

    def verify_id_token(self, *_args: object, **_kwargs: object) -> dict[str, Any]:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def verifier(result: dict[str, Any] | Exception) -> FirebaseTokenVerifier:
    instance = FirebaseTokenVerifier(Settings())
    auth = FakeAuth(result)
    instance._app = lambda: (auth, object())  # type: ignore[method-assign]
    return instance


def valid_claims() -> dict[str, Any]:
    return {
        "aud": "lendup-3cb42",
        "uid": "firebase-uid",
        "email_verified": True,
    }


def test_valid_firebase_claims_return_uid() -> None:
    assert verifier(valid_claims()).verify("token") == "firebase-uid"


@pytest.mark.parametrize(
    "error", [InvalidIdTokenError(), ExpiredIdTokenError(), RevokedIdTokenError()]
)
def test_invalid_expired_and_revoked_tokens_fail(error: Exception) -> None:
    with pytest.raises(AuthenticationError):
        verifier(error).verify("token")


def test_other_project_and_unverified_email_fail() -> None:
    claims = valid_claims()
    claims["aud"] = "other-project"
    with pytest.raises(AuthenticationError):
        verifier(claims).verify("token")
    claims = valid_claims()
    claims["email_verified"] = False
    with pytest.raises(AuthenticationError):
        verifier(claims).verify("token")


def test_identity_resolution_is_fail_closed_without_configuration() -> None:
    with pytest.raises(IdentityUnavailableError):
        HttpIdentityResolver(Settings(identity_base_url=None)).resolve_internal_user_id(
            "uid", "token"
        )


def test_identity_resolver_uses_me_contract_and_checks_uid(monkeypatch: pytest.MonkeyPatch) -> None:
    internal_id = uuid4()

    def response(url: str, **kwargs: object) -> httpx.Response:
        assert url.endswith("/api/v1/estudiantes/me")
        assert kwargs["headers"] == {"Authorization": "Bearer token"}
        return httpx.Response(
            200, json={"usuario": {"id": str(internal_id), "firebase_uid": "uid"}}
        )

    monkeypatch.setattr(httpx, "get", response)
    resolver = HttpIdentityResolver(Settings(identity_base_url="https://identity.example"))
    assert resolver.resolve_internal_user_id("uid", "token") == internal_id


def test_identity_resolver_rejects_unbound_or_mismatched_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *_args, **_kwargs: httpx.Response(
            200, json={"usuario": {"id": str(uuid4()), "firebase_uid": "another"}}
        ),
    )
    resolver = HttpIdentityResolver(Settings(identity_base_url="https://identity.example"))
    with pytest.raises(IdentityNotResolvedError):
        resolver.resolve_internal_user_id("uid", "token")
