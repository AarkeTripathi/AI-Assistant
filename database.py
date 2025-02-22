import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, Column, ForeignKey, String, JSON, select, insert, delete
from sqlalchemy.dialects.postgresql import UUID

class Database:
    def __init__(self):
        load_dotenv()
        database_url = os.getenv('DATABASE_URL')
        self.engine = create_engine(database_url, echo=True)
        self.conn = self.engine.connect()

        self.metadata = MetaData()

        self.users_table = Table(
            'users', self.metadata,
            Column('id', UUID(as_uuid=True), primary_key=True),
            Column('username', String, unique=True, nullable=False),
            Column('email', String, unique=True, nullable=False),
            Column('hashed_password', String, nullable=False)
        )

        self.sessions_table = Table(
            'sessions', self.metadata,
            Column('id', UUID(as_uuid=True), primary_key=True),
            Column('name', String),
            Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
        )

        self.chats_table = Table(
            'chats', self.metadata,
            Column('id', UUID(as_uuid=True), primary_key=True),
            Column('conversation', JSON),
            Column('session_id',  UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False)
        )

    def create_tables(self):
        self.metadata.create_all(self.engine)
    
    def delete_tables(self):
        self.metadata.drop_all(self.engine)

    '''User related queries'''

    def insert_user(self, id, name, email, hashed_pwd):
        conn = self.conn
        trans = conn.begin()
        try:
            query = insert(self.users_table).values(id=id, username=name, email=email, hashed_password=hashed_pwd)
            conn.execute(query)
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


    def select_user_by_username(self, username):
        conn = self.conn
        trans = conn.begin()
        try:
            query = select(self.users_table).where(self.users_table.c.username == username)
            result = conn.execute(query)
            trans.commit()
            return result.fetchone()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")
    

    def select_user_by_email(self, email):
        conn = self.conn
        trans = conn.begin()
        try:
            query = select(self.users_table).where(self.users_table.c.email == email)
            result = conn.execute(query)
            trans.commit()
            return result.fetchone()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")
    

    def remove_user(self, user_id):
        sessions = self.get_sessions(user_id)
        session_ids = [session[0] for session in sessions]
        conn = self.conn
        trans = conn.begin()
        try:
            for session_id in session_ids:
                chat_query = delete(self.chats_table).where(self.chats_table.c.session_id == session_id)
                conn.execute(chat_query)
            session_query = delete(self.sessions_table).where(self.sessions_table.c.user_id == user_id)
            conn.execute(session_query)
            user_query = delete(self.users_table).where(self.users_table.c.id == user_id)
            conn.execute(user_query)
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


    '''Session related queries'''

    def insert_session(self, id, title, user_id):
        conn = self.conn
        trans = conn.begin()
        try:
            query = insert(self.sessions_table).values(id=id, name=title, user_id=user_id)
            conn.execute(query)
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


    def get_sessions(self, user_id):
        conn = self.conn
        trans = conn.begin()
        try:
            query = select(self.sessions_table).where(self.sessions_table.c.user_id == user_id)
            result = conn.execute(query)
            trans.commit()
            sessions = result.fetchall()
            return sessions
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")
    

    def get_session_title(self, session_id):
        conn = self.conn
        trans = conn.begin()
        try:
            query = select(self.sessions_table.c.name).where(self.sessions_table.c.id == session_id)
            result = conn.execute(query)
            trans.commit()
            title = result.fetchone()
            return title[0]
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


    def delete_session(self, session_id):
        conn = self.conn
        trans = conn.begin()
        try:
            chat_query = delete(self.chats_table).where(self.chats_table.c.session_id == session_id)
            conn.execute(chat_query)
            session_query = delete(self.sessions_table).where(self.sessions_table.c.id == session_id)
            conn.execute(session_query)
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


    '''Chat related queries'''

    def insert_chat(self, id, new_conversation, session_id):
        conn = self.conn
        trans = conn.begin()
        try:
            query = insert(self.chats_table).values(id=id, conversation=new_conversation, session_id=session_id)
            conn.execute(query)
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


    def select_chats(self, session_id):
        conn = self.conn
        trans = conn.begin()
        try:
            query = select(self.chats_table).where(self.chats_table.c.session_id == session_id)
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


if __name__ == '__main__':
    db = Database()
    # db.create_tables()
    # if not db.select_user_by_username('admin'):
    #     db.insert_user('admin', 'admin', '$2b$12$LtjXxkWkFo5LsZSuc23rLuraQIaCI0rublhaTYeaVyEByzbIlFpqa')
    # print(db.select_user_by_email('admin'))
    # print(db.get_sessions('ada6ac8d-22b5-45d9-8c2d-0b899f5aa204'))
    # temp_session_id = uuid.uuid4()
    # db.insert_chat({'User': 'hello', 'Assistant': 'Hi, how may I help?'}, temp_session_id, 1)
    # db.insert_chat({'User': 'namaste', 'Assistant': 'Namaste, Aap kaise hain'}, temp_session_id, 1)
    # print(db.select_chats(temp_session_id,1))