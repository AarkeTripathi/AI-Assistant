from groq import Groq
import os
import base64
from dotenv import load_dotenv
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate, ChatPromptTemplate

def load_client():
    load_dotenv()
    api_key=os.getenv('GROQ_API_KEY')
    client = Groq(api_key=api_key)
    return client

# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

# Getting the base64 string
def chat(image_path,text):
    client=load_client()
    base64_image = encode_image(image_path)
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
        model="llama-3.2-11b-vision-preview",
    )
    response = (chat_completion.choices[0].message.content)
    return response


# # Path to your image
# image_path = "Penguins.jpg"
# text="Whats in this image?"
# print(response(image_path,text))