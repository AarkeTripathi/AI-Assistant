import os
from models import base_model, image_model
from models.document_loader import load_document
from database import Database
from auth_service import User, Token, TokenData, get_user, authenticate_user, create_access_token, get_password_hash, current_user
from langchain_core.prompts import HumanMessagePromptTemplate, AIMessagePromptTemplate
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import uuid

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"]
)

db=Database()

ACCESS_TOKEN_EXPIRES_MINUTES = 30
MAX_FILE_SIZE = 5242880   #5MB

ROLE1='User'
ROLE2='Assistant'

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
async def register_user(username: str = Form(), email: str = Form(), password: str = Form()):
    if db.select_user(username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")
    hashed_password = get_password_hash(password)
    db.insert_user(username, email, hashed_password)
    return {"message": "User created successfully."}


'''Authorized Routes'''

@app.get("/user/", response_model = User)
async def read_users_me(current_user: TokenData = Depends(current_user)):
    user = get_user(db, current_user.username)
    return user

@app.get('/user/chats/', response_model=list)
async def get_sessions(current_user: TokenData = Depends(current_user)):
    user = get_user(db, current_user.username)
    session_ids = db.get_session_ids(user.id)
    return session_ids
    # for session in sessions:
    #     chats = db.select_chats(session, user.id)
    #     chat_history = base_model.load_chat_history(chats, ROLE1, ROLE2)
    #     text = 'Give a title for this chat session in under 7 words'
    #     prompt = HumanMessagePromptTemplate.from_template(text)

@app.get('/user/chats/{session_id}/')
async def get_chats(session_id: str, current_user: TokenData = Depends(current_user)):
    global current_session_history
    user = get_user(db, current_user.username)
    chats=db.select_chats(session_id)
    chat_history = base_model.load_chat_history(chats, ROLE1, ROLE2)
    current_session_history = {user.id:chat_history}
    return {'session_id':session_id, 'chats':chats}

@app.delete('/user/chats/{session_id}/del/')
async def delete_session(session_id: str, current_user: TokenData = Depends(current_user)):
    try:
        db.delete_session(session_id)
    except Exception as e:
        return {'Error':str(e)}
    return {'message':'Session deleted successfully.'}


'''Chat Routes'''

@app.post('/user/chats/{session_id}/text/')
async def text_processing(session_id: str, text: str = Form(), current_user: TokenData = Depends(current_user)):
    try:
        user = get_user(db, current_user.username)
        if session_id=='new':
            new_session_id = uuid.uuid4()
            chat_history = base_model.create_chat_history()
        else:
            new_session_id = uuid.UUID(session_id)
            chat_history = current_session_history[user.id]
        chat_history, response=base_model.chat(chat_history, text)
        if session_id != "new":
            current_session_history[user.id] = chat_history
        new_chat = {ROLE1:text, ROLE2:response}
        db.insert_chat(new_chat, new_session_id, user.id)
    except Exception as e:
        return {'Error':str(e)}
    return {'chat':new_chat,'session_id':new_session_id}

@app.post('/user/chats/{session_id}/document/')
async def document_processing(session_id: str, 
                              text: Optional[str] = Form(None), 
                              file: UploadFile = File(...), 
                              current_user: TokenData = Depends(current_user)):
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx") or file.filename.endswith(".pptx")):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid File type.")
    
    contents = await file.read(MAX_FILE_SIZE + 1)
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File size exceeds 5MB.")
    file.file.seek(0)
    
    user = get_user(db, current_user.username)
    if session_id=='new':
        new_session_id = uuid.uuid4()
        chat_history = base_model.create_chat_history() 
    else:
        new_session_id = uuid.UUID(session_id)
        chat_history = current_session_history[user.id]
    temp_document_path = f"temp_{file.filename}"
    try:
        with open(temp_document_path, "wb") as temp_file:
            temp_file.write(await file.read())
        context=load_document(temp_document_path)
        if text=='':
            text='What is in this document?'
        prompt=context+' '+text
        chat_history, response=base_model.chat(chat_history, prompt)
        if session_id != "new":
            current_session_history[user.id] = chat_history
        new_chat = {ROLE1:text, ROLE2:response}
        db.insert_chat(new_chat, new_session_id, user.id)
    except Exception as e:
        return {'Error':str(e)}
    finally:
        if os.path.exists(temp_document_path):
            os.remove(temp_document_path)
    return {'chat':new_chat,'session_id':new_session_id}

@app.post('/user/chats/{session_id}/image/')
async def image_processing(session_id: str, 
                           text: Optional[str] = Form(None), 
                           file: UploadFile = File(...), 
                           current_user: TokenData = Depends(current_user)):
    if not (file.content_type.startswith("image/")):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid File type.")
    
    contents = await file.read(MAX_FILE_SIZE + 1)
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File size exceeds 5MB.")
    file.file.seek(0)
    
    user = get_user(db, current_user.username)
    if session_id=='new':
        new_session_id = uuid.uuid4()
        chat_history = base_model.create_chat_history()
    else:
        new_session_id = uuid.UUID(session_id)
        chat_history = current_session_history[user.id]
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
        if session_id != "new":
            current_session_history[user.id] = chat_history
        new_chat = {ROLE1:text, ROLE2:response}
        db.insert_chat(new_chat, new_session_id, user.id)
    except Exception as e:
        return {'Error':str(e)}
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
    return {'chat':new_chat,'session_id':new_session_id}


if __name__=="__main__":
    port = int(os.getenv("PORT", 8000))
    # uvicorn.run("main:app", host="localhost", port=port, reload=True)   #For development
    uvicorn.run("main:app", host="0.0.0.0", port=port)   #For production
    db.conn.close()