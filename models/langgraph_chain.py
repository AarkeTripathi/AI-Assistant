import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

load_dotenv()

# 1️⃣ Initialize Postgres pgvectorRetriever
vector_store = PGVector(
    embeddings=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
    connection=os.getenv("DATABASE_URL"),
    collection_name="companies",
    distance_strategy="cosine",
    pre_delete_collection=False
)
retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k":5})

# 2️⃣ Prepare LLM
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)

# 3️⃣ Define helper chains for context decider and summarizer
decider_prompt = PromptTemplate.from_template(
    "Conversation:\n{chat_history}\nUser: {input}\n\n"
    "Do you need company data? Reply exactly 'Yes' or 'No'."
)
decider = decider_prompt | llm | StrOutputParser()


summarizer_prompt = PromptTemplate.from_template(
    "Extract key use cases and website link from:\n{docs}\nSummary:"
)
summarizer = summarizer_prompt | llm | StrOutputParser()


final_prompt = PromptTemplate.from_template(
    "{chat_history}\n\nContext Summaries:\n{context}\nUser: {input}\nAnswer:"
)
final_answer = final_prompt | llm | StrOutputParser()


# 4️⃣ Build LangGraph state machine + memory
class State(TypedDict):
    user_input: str
    messages: list

def process_turn(state: State):
    user_input = state["user_input"]
    state["messages"].append(HumanMessage(content=user_input))
    chat_history = "\n".join(m.content for m in state["messages"])

    decision = decider.invoke({"chat_history": chat_history, "input": user_input}).strip().lower()

    context = ""
    if decision == "yes":
        docs = retriever.invoke(user_input)
        joined = "\n---\n".join(d.page_content for d in docs)
        context = summarizer.invoke({"docs": joined})

    answer = final_answer.invoke({
        "chat_history": chat_history,
        "context": context,
        "input": user_input
    })

    state["messages"].append(AIMessage(content=answer))
    return {"messages": state["messages"]}

# Assemble graph
graph = StateGraph(state_schema=State)
graph.add_node("model", process_turn)
graph.add_edge(START, "model")

# Add memory checkpointing
memory = MemorySaver()
agent = graph.compile(checkpointer=memory)

# 5️⃣ Run the agent (with persistence across turns)
cfg = {"configurable": {"thread_id": "session_123"}}

# Turn 1
res = agent.invoke({"user_input": "Hello!", "messages": []}, config=cfg)
print(res["messages"][-1].content)

# Turn 2
# res2 = agent.invoke({"messages": [], "user_input": "Do you need company data?"}, config=cfg)
# print(res2["messages"][-1].content)
