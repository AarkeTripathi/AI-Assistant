import os
from models import base_model, image_model
from document_loader import load_document
import database as db
from langchain_core.prompts import HumanMessagePromptTemplate, AIMessagePromptTemplate
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import uvicorn

app=FastAPI()

conn=db.engine.connect()

USER_ID=1   # For now, we are assuming that the user is the admin
SESSION_ID=1    # For now, we are assuming that the session is the first session

role1=db.role1
role2=db.role2

if not db.select_user('admin', conn):
    db.insert_user(USER_ID, 'admin', 'admin', conn)
    print('here')   

def load_chat_history():
    ai_theme="You are a helpful AI assistant."
    chat_history=base_model.create_chat_history(ai_theme)

    chats=db.select_chats(SESSION_ID, conn)
    if chats:
        for chat in chats:
            user_msg=chat[role1]
            ai_msg=chat[role2]
            chat_history.append(HumanMessagePromptTemplate.from_template(user_msg))
            chat_history.append(AIMessagePromptTemplate.from_template(ai_msg))
    
    return chat_history

chat_history = load_chat_history()


@app.get('/{text}/')
async def text_processing(text: str):
    try:
        response=base_model.chat(chat_history,text)
        new_chat = {role1:text, role2:response}
        db.update_chat(SESSION_ID, new_chat, USER_ID, conn)
    except Exception as e:
        return {'Error':str(e)}
    return new_chat


@app.post('/document/')
async def document_processing(text: Optional[str] = Form(None), file: UploadFile = File(...)):
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx") or file.filename.endswith(".pptx")):
        raise HTTPException(status_code=422, detail="Invalid File type.")
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
            new_chat = {role1:prompt, role2:response}
            db.update_chat(SESSION_ID, new_chat, USER_ID, conn)
        except Exception as e:
            return {'Error':str(e)}
        finally:
            if os.path.exists(temp_document_path):
                os.remove(temp_document_path)
        return new_chat


@app.post('/image/')
async def image_processing(text: Optional[str] = Form(None), file: UploadFile = File(...)):
    if not (file.content_type.startswith("image/")):
        raise HTTPException(status_code=422, detail="Invalid File type.")
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
            new_chat = {role1:text, role2:response}
            db.update_chat(SESSION_ID, new_chat, USER_ID, conn)
        except Exception as e:
            return {'Error':str(e)}
        finally:
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
        return new_chat


if __name__=="__main__":
   uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
   conn.close()