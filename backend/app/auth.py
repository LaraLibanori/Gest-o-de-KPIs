from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .config import AUDIENCE, ISSUER, JWKS_URL

# auto_error desligado para responder 401, e não o 403 que vem de fábrica.
bearer = HTTPBearer(auto_error=False)

_jwks: PyJWKClient | None = None


def _chaves() -> PyJWKClient:
    global _jwks
    if _jwks is None:
        _jwks = PyJWKClient(JWKS_URL, timeout=5)
    return _jwks


@dataclass
class User:
    id: UUID
    email: str | None


def _recusar() -> HTTPException:
    return HTTPException(401, "token inválido ou expirado")


# Função sync: o FastAPI roda ela em threadpool e não trava o event loop.
def get_user(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if cred is None:
        raise HTTPException(401, "não autenticado")

    try:
        chave = _chaves().get_signing_key_from_jwt(cred.credentials).key
        claims = jwt.decode(
            cred.credentials,
            chave,
            algorithms=["ES256", "RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
    except jwt.PyJWTError:
        raise _recusar()

    # O sub precisa existir e ser uuid: sem isso vira erro 500 lá na query.
    try:
        return User(id=UUID(claims["sub"]), email=claims.get("email"))
    except (KeyError, ValueError, TypeError):
        raise _recusar()


CurrentUser = Annotated[User, Depends(get_user)]
