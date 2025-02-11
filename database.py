import os
from dotenv import load_dotenv
from ast import literal_eval
from sqlalchemy import create_engine
from sqlalchemy import MetaData, Table, Column, ForeignKey, Integer, String, JSON

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URL, echo=True)

metadata = MetaData()

users_table = Table(
    'users', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String, nullable=False),
    Column('email', String, unique=True)
)

chats_table = Table(
    'chats', metadata,
    Column('session_id', Integer, primary_key=True),
    Column('conversation', JSON, nullable=False),
    Column('user_id', Integer, ForeignKey('users.id'))
)

role1='User'
role2='Assistant'


def select_user(email, conn):
    trans = conn.begin()
    query = users_table.select().where(users_table.c.email == email)
    result = conn.execute(query)
    trans.commit()
    return result.fetchone()


def insert_user(id, name, email, conn):
    trans = conn.begin()
    try:
        query = users_table.insert().values(id=id, name=name, email=email)
        conn.execute(query)
        trans.commit()
    except Exception as e:
        trans.rollback()
        print(f"Transaction failed: {e}")


def select_chats(session_id, conn):
    trans = conn.begin()
    query = chats_table.select().where(chats_table.c.session_id == session_id)
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


def update_chat(session_id, new_conversation, user_id, conn):
    chats = select_chats(session_id, conn)
    chats.append(new_conversation)
    trans = conn.begin()
    try:
        if len(chats)==1:
            query = chats_table.insert().values(session_id=session_id, conversation=chats, user_id=user_id)
        else:
            query = chats_table.update().where(chats_table.c.session_id == session_id).values(conversation=chats, user_id=user_id)
        conn.execute(query)
        trans.commit()
    except Exception as e:
        trans.rollback()
        print(f"Transaction failed: {e}")


if __name__ == '__main__':
    with engine.connect() as conn:
        if not select_user('admin', conn):
            insert_user(1, 'admin', 'admin', conn)
        update_chat(1, {role1: 'hello', role2: 'Hi, how may I help?'}, 1, conn)
        update_chat(1, {role1: 'how are you', role2: 'I am good, what about you?'}, 1, conn)
        print(select_chats(1, conn))
        