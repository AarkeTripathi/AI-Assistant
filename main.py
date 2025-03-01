import os
from models import base_model, image_model
from models.document_loader import DocumentLoader
from database import Database
from cache import Cache
from auth_service import User, Token, TokenData, get_user, authenticate_user, create_access_token, get_password_hash, current_user
from langchain_core.prompts import HumanMessagePromptTemplate, AIMessagePromptTemplate
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import uuid

ACCESS_TOKEN_EXPIRES_MINUTES = 30
MAX_FILE_SIZE = 5242880   #5MB
ROLE1 = 'User'
ROLE2 = 'Assistant'
TITLE_QUERY = 'Generate a title for this chat in under 7 words.'

db=Database()

r = Cache()

dm = DocumentLoader()

app=FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"]
)

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
    try:
        if db.select_user_by_username(username):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists.")
        if db.select_user_by_email(email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")
        hashed_password = get_password_hash(password)
        db.insert_user(uuid.uuid4(), username, email, hashed_password)
        return {"message": "User created successfully."}
    except Exception as e:
        return {'Error':str(e)}


'''Authorized Routes'''

@app.get("/user/", response_model = User)
async def read_users_me(current_user: TokenData = Depends(current_user)):
    user = get_user(db, current_user.username)
    return user

@app.delete('/user/del/')
async def delete_account(current_user: TokenData = Depends(current_user)):
    try:
        user = get_user(db, current_user.username)
        db.remove_user(user.id)
    except Exception as e:
        return {'Error':str(e)}
    return {'message':'Account deleted successfully.'}

@app.get('/user/chats/')
async def get_sessions(current_user: TokenData = Depends(current_user)):
    try:
        user = get_user(db, current_user.username)
        sessions = db.get_sessions(user.id)
        session_dict = {}
        for session in sessions:
            session_dict[session[0]] = session[1]
        return session_dict
    except Exception as e:
        return {'Error':str(e)}

@app.get('/user/chats/{session_id}/')
async def get_chats(session_id: str, current_user: TokenData = Depends(current_user)):
    # global current_session_history
    try:
        chats = db.select_chats(session_id)
        title = db.get_session_title(session_id)
        chat_history = base_model.load_chat_history(chats, ROLE1, ROLE2)
        # current_session_history = {user.id:chat_history}
        await r.store_chat_history(session_id, chat_history)
    except Exception as e:
        return {'Error':str(e)}
    return {'chats':chats, 'session_id':session_id, 'session_title':title}

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
            chat_history = base_model.create_chat_history()
        else:
            # chat_history = current_session_history[user.id]
            chat_history = await r.get_chat_history(session_id)
        
        response=base_model.chat(chat_history, text)
        if session_id == "new":
            session_id = uuid.uuid4()
            title = base_model.chat(chat_history, TITLE_QUERY)
            db.insert_session(session_id, title, user.id)
        else:
            session_id = uuid.UUID(session_id)
            title = db.get_session_title(session_id)
        # current_session_history[user.id] = chat_history
        await r.store_chat_history(session_id, chat_history)
        new_chat = {ROLE1:text, ROLE2:response}
        db.insert_chat(uuid.uuid4(), new_chat, session_id)
    except Exception as e:
        return {'Error':str(e)}
    return {'chat':new_chat, 'session_id':session_id, 'session_title':title}
    

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

    try:
        user = get_user(db, current_user.username)
        if session_id=='new':
            chat_history = base_model.create_chat_history()
        else:
            # chat_history = current_session_history[user.id]
            chat_history = await r.get_chat_history(session_id)
        temp_document_path = f"temp_{file.filename}"
        with open(temp_document_path, "wb") as temp_file:
            temp_file.write(await file.read())
        context=dm.load_document(temp_document_path)
        if text=='':
            text='What is in this document?'
        prompt=context+' '+text
        
        response=base_model.chat(chat_history, prompt)
        if session_id == "new":
            session_id = uuid.uuid4()
            title = base_model.chat(chat_history, TITLE_QUERY)
            db.insert_session(session_id, title, user.id)
        else:
            session_id = uuid.UUID(session_id)
            title = db.get_session_title(session_id)
        # current_session_history[user.id] = chat_history
        await r.store_chat_history(session_id, chat_history)
        new_chat = {ROLE1:text, ROLE2:response}
        db.insert_chat(uuid.uuid4(), new_chat, session_id)
    except Exception as e:
        return {'Error':str(e)}
    finally:
        if os.path.exists(temp_document_path):
            os.remove(temp_document_path)
    return {'chat':new_chat, 'session_id':session_id, 'session_title':title}


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
    
    try:
        user = get_user(db, current_user.username)
        if session_id=='new':
            chat_history = base_model.create_chat_history()
        else:
            # chat_history = current_session_history[user.id]
            chat_history = await r.get_chat_history(session_id)
        temp_image_path = f"temp_{file.filename}"
        with open(temp_image_path, "wb") as temp_file:
            temp_file.write(await file.read())
        if text=='':
            text='What is in this image?'
        prompt = text.replace("{", "{{").replace("}", "}}")
        prompt=HumanMessagePromptTemplate.from_template(prompt)
        chat_history.append(prompt)
        response=image_model.chat(temp_image_path,text)
        AIresponse = response.replace("{", "{{").replace("}", "}}")
        AIresponse=AIMessagePromptTemplate.from_template(AIresponse)
        chat_history.append(AIresponse)
        if session_id == "new":
            session_id = uuid.uuid4()
            title = base_model.chat(chat_history, TITLE_QUERY)
            db.insert_session(session_id, title, user.id)
        else:
            session_id = uuid.UUID(session_id)
            title = db.get_session_title(session_id)
        # current_session_history[user.id] = chat_history
        await r.store_chat_history(session_id, chat_history)
        new_chat = {ROLE1:text, ROLE2:response}
        db.insert_chat(uuid.uuid4(), new_chat, session_id)
    except Exception as e:
        return {'Error':str(e)}
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
    return {'chat':new_chat, 'session_id':session_id, 'session_title':title}


if __name__=="__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="localhost", port=port, reload=True)   #For development
    # uvicorn.run("main:app", host="0.0.0.0", port=port)   #For production
    db.conn.close()