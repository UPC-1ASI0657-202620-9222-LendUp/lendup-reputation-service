from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lendup_reputation.application.ports import IdentityResolver, TokenVerifier

bearer = HTTPBearer(auto_error=False, scheme_name="FirebaseBearer")


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    firebase_uid: str
    internal_user_id: UUID


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> AuthenticatedUser:
    from lendup_reputation.domain.exceptions import AuthenticationError

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Se requiere un Bearer token")
    verifier: TokenVerifier = request.app.state.token_verifier
    resolver: IdentityResolver = request.app.state.identity_resolver
    uid = verifier.verify(credentials.credentials)
    internal_id = resolver.resolve_internal_user_id(uid, credentials.credentials)
    return AuthenticatedUser(uid, internal_id)
