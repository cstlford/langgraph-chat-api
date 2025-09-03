from dotenv import load_dotenv


from app.agent.tools import schema_retriever


load_dotenv()


print(schema_retriever.invoke({"query": "business on the books"}))
