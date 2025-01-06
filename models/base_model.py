import os
from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate, ChatPromptTemplate

def load_model():
    load_dotenv()
    api_key=os.getenv('GROQ_API_KEY')
    # os.environ["GROQ_API_KEY"]=api_key
    model = ChatGroq(api_key=api_key, model="llama-3.2-11b-vision-preview")
    return model

def create_chat_history(ai_theme):
    system_message=SystemMessagePromptTemplate.from_template(ai_theme)
    chat_history=[system_message]
    return chat_history

def generate_response(chat_history):
    model=load_model()
    chat_template=ChatPromptTemplate.from_messages(chat_history)
    chain=chat_template|model|StrOutputParser()
    response=chain.invoke({})
    return response

def chat(chat_history, text):
    prompt=HumanMessagePromptTemplate.from_template(text)
    chat_history.append(prompt)
    response=generate_response(chat_history)
    # print(f'\nAssistant: {response}\n')
    AIresponse=AIMessagePromptTemplate.from_template(response)
    chat_history.append(AIresponse)
    return response

# chat_history=create_chat_history()
# while True:
#     text=input('User: ')
#     if text=='bye':
#         print('\nAssistant: Goodbye.')
#         break
#     conversation(chat_history,text)