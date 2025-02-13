import os
from models import base_model, image_model
from document_loader import load_document
from database import Database
from auth_service import User, Token, get_user, authenticate_user, create_access_token, get_password_hash, current_user
from langchain_core.prompts import HumanMessagePromptTemplate, AIMessagePromptTemplate
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
import uvicorn

app=FastAPI()

db=Database()

USER_ID=2   # For now, we are assuming that the user is the second user
SESSION_ID=1    # For now, we are assuming that the session is the first session

ACCESS_TOKEN_EXPIRES_MINUTES = 30

ROLE1='User'
ROLE2='Assistant'

chats=db.select_chats(SESSION_ID)

chat_history = base_model.load_chat_history(chats, ROLE1, ROLE2)

# if not db.select_user('admin'):
#     db.insert_user(USER_ID, 'admin', 'admin', 'allpass')
#     print('here')   


'''Authentication Routes'''

@app.post("/token/", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token(data={'sub':user.username}, expires_delta=ACCESS_TOKEN_EXPIRES_MINUTES)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register/")
async def register_user(username: str, email: str, password: str):
    if db.select_user(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")
    hashed_password = get_password_hash(password)
    db.insert_user(USER_ID, username, email, hashed_password)
    return {"message": "User created successfully."}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(current_user)):
    token_data = current_user
    user = get_user(db, token_data.email)
    return user


'''Chat Routes'''

@app.get('/{text}/')
async def text_processing(text: str):
    try:
        response=base_model.chat(chat_history,text)
        new_chat = {ROLE1:text, ROLE2:response}
        db.update_chat(SESSION_ID, new_chat, USER_ID)
    except Exception as e:
        return {'Error':str(e)}
    return new_chat

@app.post('/document/')
async def document_processing(text: Optional[str] = Form(None), file: UploadFile = File(...)):
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx") or file.filename.endswith(".pptx")):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid File type.")
    else: 
        temp_document_path = f"temp_{file.filename}"
        try:
            with open(temp_document_path, "wb") as temp_file:
                temp_file.write(await file.read())
            context=load_document(temp_document_path)
            if text=='':
                text='What is in this document?'
            prompt=context+' '+text
            response=base_model.chat(chat_history,prompt)
            new_chat = {ROLE1:prompt, ROLE2:response}
            db.update_chat(SESSION_ID, new_chat, USER_ID)
        except Exception as e:
            return {'Error':str(e)}
        finally:
            if os.path.exists(temp_document_path):
                os.remove(temp_document_path)
        return new_chat

@app.post('/image/')
async def image_processing(text: Optional[str] = Form(None), file: UploadFile = File(...)):
    if not (file.content_type.startswith("image/")):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid File type.")
    else:
        temp_image_path = f"temp_{file.filename}"
        try:
            with open(temp_image_path, "wb") as temp_file:
                temp_file.write(await file.read())
            if text=='':
                text='What is in this image?'
            prompt=HumanMessagePromptTemplate.from_template(text)
            chat_history.append(prompt)
            response=image_model.chat(temp_image_path,text)
            AIresponse=AIMessagePromptTemplate.from_template(response)
            chat_history.append(AIresponse)
            new_chat = {ROLE1:text, ROLE2:response}
            db.update_chat(SESSION_ID, new_chat, USER_ID)
        except Exception as e:
            return {'Error':str(e)}
        finally:
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
        return new_chat


if __name__=="__main__":
   uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
   db.conn.close()