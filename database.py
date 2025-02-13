import os
from dotenv import load_dotenv
from ast import literal_eval
from sqlalchemy import create_engine
from sqlalchemy import MetaData, Table, Column, ForeignKey, Integer, String, JSON, PrimaryKeyConstraint

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
            Column('email', String, unique=True),
            Column('hashed_password', String, nullable=False)
        )

        self.chats_table = Table(
            'chats', self.metadata,
            Column('session_id', Integer, nullable=False),
            Column('conversation', JSON, nullable=False),
            Column('user_id', Integer, ForeignKey('users.id'), nullable=False),
            PrimaryKeyConstraint('session_id', 'user_id', name='chats_id_seq')
        )


    def create_tables(self):
        self.metadata.create_all(self.engine)


    def select_user(self, email):
        conn = self.conn
        trans = conn.begin()
        query = self.users_table.select().where(self.users_table.c.email == email)
        result = conn.execute(query)
        trans.commit()
        return result.fetchone()


    def insert_user(self, id, name, email, hashed_pwd):
        conn = self.conn
        trans = conn.begin()
        try:
            query = self.users_table.insert().values(id=id, username=name, email=email, hashed_password=hashed_pwd)
            conn.execute(query)
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


    def select_chats(self, session_id):
        conn = self.conn
        trans = conn.begin()
        query = self.chats_table.select().where(self.chats_table.c.session_id == session_id)
        result = conn.execute(query)
        trans.commit()
        rows = result.fetchall()
        conversation_list=[]
        if not rows:
            return conversation_list
        for row in rows:
            actual_list = literal_eval(row[1])
            conversation_list = conversation_list + actual_list
        return conversation_list


    def update_chat(self, session_id, new_conversation, user_id):
        chats = self.select_chats(session_id)
        chats.append(new_conversation)
        conn = self.conn
        trans = conn.begin()
        try:
            if len(chats)==1:
                query = self.chats_table.insert().values(session_id=session_id, conversation=chats, user_id=user_id)
            else:
                query = self.chats_table.update().where(self.chats_table.c.session_id == session_id).values(conversation=chats, user_id=user_id)
            conn.execute(query)
            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Transaction failed: {e}")


if __name__ == '__main__':
    ai_assistant_db = Database()
    # metadata.create_all(engine)
    if not ai_assistant_db.select_user('admin'):
        ai_assistant_db.insert_user(1, 'admin', 'admin', 'allpass')
    print(ai_assistant_db.select_user('admin'))
    # update_chat(1, {role1: 'hello', role2: 'Hi, how may I help?'}, 1)
    # update_chat(1, {role1: 'how are you', role2: 'I am good, what about you?'}, 1)
    # print(select_chats(1, conn))
        