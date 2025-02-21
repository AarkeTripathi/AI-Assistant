import pickle
from redis.asyncio import Redis

class Cache:
    def __init__(self):
        self.redis_client = Redis(host="localhost", port=6379, decode_responses=False)

    async def store_chat_history(self, session_id, chat_history):
        try:
            session_id = str(session_id)
            serialized_data = pickle.dumps(chat_history)
            await self.redis_client.set(session_id, serialized_data, ex=1800)
        except Exception as e:
            return {"Redis Fetch Error": str(e)}

    async def get_chat_history(self, session_id):
        try:
            session_id = str(session_id)
            data = await self.redis_client.get(session_id)
            return pickle.loads(data) if data else None
        except Exception as e:
            return {"Redis Fetch Error": str(e)}
        

if __name__=='__main__':
    r = Cache()

