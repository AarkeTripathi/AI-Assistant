from pydantic import BaseModel
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError
from passlib.context import CryptContext
import logging
from datetime import datetime, timedelta

SECRET_KEY = "15311fde7d554538063abda0d6a763dc6dd05327177abbeab9efe903ef3d93f0"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logging.getLogger('passlib').setLevel(logging.ERROR)

class User(BaseModel):
    id: int
    username: str
    email: str
    # disabled: bool  # This is not needed for now (for disabling inactive users)

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):    
    return pwd_context.hash(password)  

def get_user(db, email: str):
    user = db.select_user(email)
    if not user:
        return False
    dic={'id':user[0],'username':user[1],'email':user[2],'hashed_password':user[3]}
    return UserInDB(**dic)

def authenticate_user(db, email, password):
    user = get_user(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data, expires_delta):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def current_user(token = Depends(OAuth2PasswordBearer(tokenUrl="token"))):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get('sub')
        if not email:
            raise credentials_exception
        token_data = TokenData(email=email)
    except PyJWTError:
        raise credentials_exception
    return token_data
    # user = get_user(db, token_data.email)
    # if not user:
    #     raise credentials_exception
    # return user

async def get_current_active_user(current_user: User = Depends(current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

if __name__ == '__main__':
    print(get_password_hash('allpass'))
