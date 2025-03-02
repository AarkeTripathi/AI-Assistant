import os
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError
from passlib.context import CryptContext
import logging
from datetime import datetime, timedelta
from uuid import UUID

load_dotenv()
secret_key = os.getenv('SECRET_KEY')

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logging.getLogger('passlib').setLevel(logging.ERROR)


class User(BaseModel):
    id: UUID
    username: str
    email: str
    # disabled: bool  # This is not needed for now (for disabling inactive users)

class UserInDB(User):
    hashed_password: str

class AccessToken(BaseModel):
    access_token: str
    token_type: str

class Token(AccessToken):
    refresh_token: str | None = None

class TokenData(BaseModel):
    username: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):    
    return pwd_context.hash(password)  

def get_user(db, username: str):
    user = db.select_user_by_username(username)
    if not user:
        return False
    dic={'id':user[0],'username':user[1],'email':user[2],'hashed_password':user[3]}
    return UserInDB(**dic)

def authenticate_user(db, username, password):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_token(data, expires_delta, refresh: bool = False):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire, "refresh": refresh})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt

async def current_user(token = Depends(OAuth2PasswordBearer(tokenUrl="token"))):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        username = payload.get('sub')
        if not username:
            raise credentials_exception
        token_data = TokenData(username=username)
    except PyJWTError:
        raise credentials_exception
    return token_data   #Did not use get_user() here because we are not using the database in this module

async def get_current_active_user(current_user: User = Depends(current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

if __name__ == '__main__':
    print(get_password_hash('allpass'))
    access_token = create_token(data={'sub':"aarke"}, expires_delta=30)
    print(type(access_token))
