from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from .models import User
from .db import get_session

# Prefer bcrypt_sha256 to avoid bcrypt's 72-byte password length limit.
# Prefer Argon2 for new hashes, keep bcrypt_sha256 and bcrypt for backward compatibility.
PWD_CTX = CryptContext(schemes=["argon2", "bcrypt_sha256", "bcrypt"], deprecated="auto")
SECRET = "dev-secret-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def hash_password(password: str) -> str:
    # Use CryptContext to hash; preferred algorithm is Argon2 which accepts long passwords.
    return PWD_CTX.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    # Standard verify via CryptContext. For backward compatibility we may
    # attempt a truncated verify in `login` and upgrade the hash there.
    return PWD_CTX.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
    except (JWTError, Exception):
        raise credentials_exception
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise credentials_exception
    return user
