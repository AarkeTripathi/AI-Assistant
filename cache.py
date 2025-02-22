import os
from dotenv import load_dotenv
import pickle
from redis.asyncio import Redis

class Cache:
    def __init__(self):
        load_dotenv()
        redis_url = os.getenv("REDIS_URL")
        self.client = Redis.from_url(redis_url)

    async def store_chat_history(self, session_id, chat_history):
        try:
            session_id = str(session_id)
            serialized_data = pickle.dumps(chat_history)
            await self.client.set(session_id, serialized_data, ex=1800)
        except Exception as e:
            return {"Redis Store Error": str(e)}

    async def get_chat_history(self, session_id):
        try:
            session_id = str(session_id)
            data = await self.client.get(session_id)
            return pickle.loads(data) if data else None
        except Exception as e:
            return {"Redis Fetch Error": str(e)}
        

if __name__ == '__main__':
    import asyncio
    import uuid
    from models.base_model import chat, create_chat_history

    async def main():
        r = Cache()
        session_id = uuid.uuid4()
        chat_history = create_chat_history()
        await r.store_chat_history(session_id, chat_history)
        while True:
            chat_history = await r.get_chat_history(session_id)
            text = input('User: ')
            chat_history, response = chat(chat_history, text)
            await r.store_chat_history(session_id, chat_history)
            print(f"\nAI: {response}\n")

    asyncio.run(main())