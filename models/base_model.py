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
    model = ChatGroq(api_key=api_key, model="llama-3.3-70b-versatile")
    return model

def create_chat_history():
    ai_theme="You are a helpful AI assistant."
    system_message=SystemMessagePromptTemplate.from_template(ai_theme)
    chat_history=[system_message]
    return chat_history

def load_chat_history(chats, role1, role2):
    chat_history=create_chat_history()
    if chats:
        for chat in chats:
            user_msg=chat[role1]
            ai_msg=chat[role2]
            chat_history.append(HumanMessagePromptTemplate.from_template(user_msg))
            chat_history.append(AIMessagePromptTemplate.from_template(ai_msg))
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
    AIresponse = response.replace("{", "{{").replace("}", "}}")
    AIresponse=AIMessagePromptTemplate.from_template(response)
    chat_history.append(AIresponse)
    return chat_history, response

if __name__=='__main__':
    chat_history = create_chat_history()
    while True:
        text = input('User: ')
        chat_history, response = chat(chat_history, text)
        print(f'\nAssistant: {response}')