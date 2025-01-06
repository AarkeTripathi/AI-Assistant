import os
from models import base_model,image_model
from document_loader import load_document
from langchain_core.prompts import HumanMessagePromptTemplate, AIMessagePromptTemplate
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import uvicorn

app=FastAPI()

# text=input()
# doc='Final_Year_Project_Paper_conference.docx'
# img='ID_Card_Front.jpg'

# @app.get('/')
# def initiate():
ai_theme="You are a helpful AI assistant."
chat_history=base_model.create_chat_history(ai_theme)
# return chat_history

@app.get('/{text}')
async def text_processing(text):
    response=base_model.chat(chat_history,text)
    return {'User':text,'Assistant':response}

@app.post('/document/')
async def document_processing(text: str = Form(...), file: UploadFile = File(...)):
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx") or file.filename.endswith(".pptx")):
        raise HTTPException(status_code=422, detail="Invalid File type.")
    else:
        temp_document_path = f"temp_{file.filename}"
        try:
            # Save the uploaded file temporarily
            with open(temp_document_path, "wb") as temp_file:
                temp_file.write(await file.read())
            context=load_document(temp_document_path)
            if text=='':
                text='What is in this document?'
            prompt=context+' '+text
            # response=base_model.chat(chat_history,prompt)
            response=base_model.chat(chat_history,prompt)
        finally:
            # Delete the temporary file
            if os.path.exists(temp_document_path):
                os.remove(temp_document_path)
        return {'User':text,'Assistant':response}

@app.post('/image/')
async def image_processing(text: str = Form(...), file: UploadFile = File(...)):
    if not (file.content_type.startswith("image/")):
        raise HTTPException(status_code=422, detail="Invalid File type.")
    else:
        temp_image_path = f"temp_{file.filename}"
        try:
            # Save the uploaded file temporarily
            with open(temp_image_path, "wb") as temp_file:
                temp_file.write(await file.read())
            if text=='':
                text='What is in this image?'
            prompt=HumanMessagePromptTemplate.from_template(text)
            chat_history.append(prompt)
            response=image_model.chat(temp_image_path,text)
            AIresponse=AIMessagePromptTemplate.from_template(response)
            chat_history.append(AIresponse)
        finally:
            # Delete the temporary file
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
        return {'User':text,'Assistant':response}

if __name__=="__main__":
   uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)