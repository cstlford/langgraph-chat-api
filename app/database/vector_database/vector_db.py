from pathlib import Path
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import JSONLoader

from app.config import vector_store_config as vc


def load_documents(store: Chroma):
    json_files = [p for p in Path(str(vc.schema_dir)).iterdir() if p.suffix == ".json"]
    print(f"📂 Loading {len(json_files)} JSON files from {vc.schema_dir}")
    docs = []
    for json_file in json_files:
        loader = JSONLoader(
            file_path=json_file,
            jq_schema=".[] | .",
            text_content=False,
        )
        docs.extend(loader.load())
    print(f"✅ Loaded {len(docs)} schemas\n")
    store.add_documents(docs)


def get_or_create_vector_store():
    persist_directory = Path(vc.persist_dir)
    vector_store = Chroma(
        persist_directory=str(persist_directory),
        collection_name=vc.collection_name,
        embedding_function=OpenAIEmbeddings(model=vc.embedding_model),
    )

    # check if folder only has one file
    if len(list(persist_directory.iterdir())) <= 1:
        print("\n✨ Creating vector store...")
        load_documents(vector_store)

    return vector_store
