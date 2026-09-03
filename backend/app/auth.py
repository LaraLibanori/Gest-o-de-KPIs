from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .config import AUDIENCE, ISSUER, JWKS_URL, JWT_SECRET

bearer = HTTPBearer()
_jwks = PyJWKClient(JWKS_URL) if not JWT_SECRET else None


@dataclass
class User:
    id: str
    email: str | None


# Função sync: o FastAPI roda ela em threadpool e não trava o event loop.
def get_user(cred: Annotated[HTTPAuthorizationCredentials, Depends(bearer)]) -> User:
    try:
        if JWT_SECRET:
            claims = jwt.decode(
                cred.credentials,
                JWT_SECRET,
                algorithms=["HS256"],
                audience=AUDIENCE,
            )
        else:
            key = _jwks.get_signing_key_from_jwt(cred.credentials).key
            claims = jwt.decode(
                cred.credentials,
                key,
                algorithms=["ES256", "RS256"],
                audience=AUDIENCE,
                issuer=ISSUER,
            )
    except jwt.PyJWTError:
        raise HTTPException(401, "token inválido ou expirado")

    return User(id=claims["sub"], email=claims.get("email"))


CurrentUser = Annotated[User, Depends(get_user)]
