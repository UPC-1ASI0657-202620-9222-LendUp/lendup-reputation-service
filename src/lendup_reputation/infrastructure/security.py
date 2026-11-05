from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from lendup_reputation.config.settings import Settings
from lendup_reputation.domain.exceptions import (
    AuthenticationError,
    IdentityNotResolvedError,
    IdentityUnavailableError,
)


class FirebaseTokenVerifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _app(self) -> tuple[Any, Any]:
        import firebase_admin  # type: ignore[import-untyped]
        from firebase_admin import auth, credentials

        if not firebase_admin._apps:
            firebase_admin.initialize_app(
                credentials.ApplicationDefault(),
                {"projectId": self._settings.firebase_project_id},
            )
        app = firebase_admin.get_app()
        if app.project_id != self._settings.firebase_project_id:
            raise RuntimeError("La aplicación Firebase inicializada pertenece a otro proyecto")
        return auth, app

    def verify(self, token: str) -> str:
        try:
            auth, app = self._app()
        except Exception as exc:
            raise IdentityUnavailableError("No se pudo inicializar Firebase") from exc
        try:
            decoded = auth.verify_id_token(
                token,
                check_revoked=self._settings.firebase_check_revoked,
                app=app,
            )
        except (
            auth.InvalidIdTokenError,
            auth.ExpiredIdTokenError,
            auth.RevokedIdTokenError,
        ) as exc:
            raise AuthenticationError("Token Firebase no válido") from exc
        except Exception as exc:
            raise IdentityUnavailableError("No se pudo verificar la identidad") from exc
        if decoded.get("aud") != self._settings.firebase_project_id:
            raise AuthenticationError("Token emitido para otro proyecto")
        if self._settings.require_verified_email and decoded.get("email_verified") is not True:
            raise AuthenticationError("El correo Firebase debe estar verificado")
        uid = decoded.get("uid") or decoded.get("sub")
        if not isinstance(uid, str) or not uid:
            raise AuthenticationError("Token sin Firebase UID")
        return uid


class HttpIdentityResolver:
    """Resolves Firebase UID through Identity's confirmed `/estudiantes/me` contract."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def resolve_internal_user_id(self, firebase_uid: str, bearer_token: str) -> UUID:
        if self._settings.identity_base_url is None:
            raise IdentityUnavailableError("La integración con Identidad no está configurada")
        url = str(self._settings.identity_base_url).rstrip("/") + self._settings.identity_me_path
        try:
            response = httpx.get(
                url,
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=self._settings.identity_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise IdentityUnavailableError("Identidad no está disponible") from exc
        if response.status_code in (401, 403, 404):
            raise IdentityNotResolvedError("Firebase UID sin UUID interno de LendUp")
        if response.status_code >= 500:
            raise IdentityUnavailableError("Identidad no está disponible")
        if response.status_code != 200:
            raise IdentityNotResolvedError("Identidad no pudo resolver al usuario")
        try:
            body = response.json()
            user = body.get("usuario", body)
            returned_uid = user.get("firebase_uid")
            if returned_uid is not None and returned_uid != firebase_uid:
                raise IdentityNotResolvedError("La vinculación de identidad no coincide")
            return UUID(str(user["id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise IdentityNotResolvedError("Respuesta inválida de Identidad") from exc
