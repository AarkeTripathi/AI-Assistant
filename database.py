import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, Column, ForeignKey, Integer, String, JSON, func, select, insert, distinct, and_
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Database:
    def __init__(self):
        load_dotenv()
        database_url = os.getenv('DATABASE_URL')
        self.engine = create_engine(database_url, echo=True)
        self.conn = self.engine.connect()

        self.metadata = MetaData()

        self.users_table = Table(
            'users', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('username', String, nullable=False),
            Column('email', String, unique=True, nullable=False),
            Column('hashed_password', String, nullable=False)
        )

        self.chats_table = Table(
            'chats', self.metadata,
            Column('id', UUID(as_uuid=True), primary_key=True),
            Column('conversation', JSON),
            Column('session_id',  UUID(as_uuid=True), nullable=False),
            Column('user_id', Integer, ForeignKey('users.id'), nullable=False)
        )


    def create_tables(self):
        self.metadata.create_all(self.engine)


    def generate_user_id(self, conn):  
        query = func.max(self.users_table.c.id)
        last_user_id = conn.execute(query).scalar()
        if not last_user_id:
            return 1
        new_user_id = last_user_id + 1
        return new_user_id


    def get_sessions(self, user_id):
        conn = self.conn
        trans = conn.begin()
        query = select(distinct(self.chats_table.c.session_id)).where(self.chats_table.c.user_id == user_id)
        result = conn.execute(query)
        trans.commit()
        session_ids = result.fetchall()
        sessions = [session_id[0] for session_id in session_ids]
        return sessions
    
    
    # def last_session_id(self, user_id):
    #     sessions = self.get_sessions(user_id)
    #     if not sessions:
    #         return None
    #     return max(sessions)


    def select_user(self, email):
        conn = self.conn
        trans = conn.begin()
        query = select(self.users_table).where(self.users_table.c.email == email)
        result = conn.execute(query)
        trans.commit()
        return result.fetchone()


    def insert_user(self, name, email, hashed_pwd):
        conn = self.conn
        trans = conn.begin()
        try:
            query = insert(self.users_table).values(id=self.generate_user_id(conn), username=name, email=email, hashed_password=hashed_pwd)
            conn.execute(query)
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


    def select_chats(self, session_id, user_id):
        conn = self.conn
        trans = conn.begin()
        try:
            query = select(self.chats_table).where(and_(self.chats_table.c.session_id == session_id, self.chats_table.c.user_id == user_id))
            result = conn.execute(query)
            trans.commit()
            rows = result.fetchall()
            conversation_list=[]
            if not rows:
                return conversation_list
            for row in rows:
                conversation_list.append(row[1])
            return conversation_list
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


    def insert_chat(self, new_conversation, session_id, user_id):
        conn = self.conn
        trans = conn.begin()
        try:
            query = insert(self.chats_table).values(id = uuid.uuid4(), conversation=new_conversation, session_id=session_id, user_id=user_id)
            conn.execute(query)
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


if __name__ == '__main__':
    db = Database()
    db.create_tables()
    if not db.select_user('admin'):
        db.insert_user('admin', 'admin', '$2b$12$LtjXxkWkFo5LsZSuc23rLuraQIaCI0rublhaTYeaVyEByzbIlFpqa')
    print(db.select_user('admin'))
    temp_session_id = uuid.uuid4()
    db.insert_chat({'User': 'hello', 'Assistant': 'Hi, how may I help?'}, temp_session_id, 1)
    db.insert_chat({'User': 'namaste', 'Assistant': 'Namaste, Aap kaise hain'}, temp_session_id, 1)
    print(db.select_chats(temp_session_id,1))