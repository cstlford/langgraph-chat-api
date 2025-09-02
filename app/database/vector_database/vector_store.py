import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, cast

from langchain_community.document_loaders import JSONLoader
from chromadb.api.types import Where
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.config import vector_store_config as config


class VectorStoreManager:
    """Manages a Chroma vector store with incremental updates."""

    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure one instance."""
        if cls._instance is None:
            cls._instance = super(VectorStoreManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the manager."""
        self.persist_directory = Path(config.persist_dir)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.version_file = self.persist_directory / "schema_versions.json"
        self.embeddings = OpenAIEmbeddings(model=config.embedding_model)
        self.vectorstore_cache = None

    @contextmanager
    def _version_file(self) -> Iterator[dict[str, str]]:
        """Context manager for version file loading and saving."""
        versions = {}
        if self.version_file.exists():
            with open(self.version_file, "r") as f:
                versions = json.load(f)
        yield versions
        with open(self.version_file, "w") as f:
            json.dump(versions, f, indent=2)

    def _get_file_hash(self, file_path: Path) -> str:
        """Get SHA256 hash of a file."""
        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _get_changed_and_deleted_files(
        self, file_names: list[str]
    ) -> tuple[list[str], list[str]]:
        """Get lists of changed and deleted files since last run."""
        changed_files = []
        with self._version_file() as versions:
            # Check for deleted files
            deleted_files = [f for f in versions.keys() if f not in file_names]

            # Check for changed files
            for file_name in file_names:
                file_path = Path(config.schema_dir) / file_name
                if not file_path.exists():
                    print("schema_file_not_found:", file_name)
                    continue

                current_hash = self._get_file_hash(file_path)
                stored_hash = versions.get(file_name)

                if stored_hash != current_hash:
                    changed_files.append(file_name)
                    versions[file_name] = current_hash

            # Remove deleted files from versions
            for file_name in deleted_files:
                versions.pop(file_name, None)

        return changed_files, deleted_files

    def _load_documents(self, file_name: str):
        """Load documents from a schema file."""
        path = Path(config.schema_dir) / file_name
        if not path.exists():
            raise FileNotFoundError(f"Schema file {file_name} not found at {path}")
        if not path.suffix == ".json":
            raise ValueError(f"File {file_name} is not a JSON file")

        loader = JSONLoader(
            file_path=path,
            jq_schema=".[] | {table_name: .table_name, content: .}",
            text_content=False,
        )
        docs = loader.load()

        # Add metadata
        schema_name = file_name.replace(".json", "")
        for doc in docs:
            doc.metadata["schema"] = schema_name
            doc.metadata["source_file"] = file_name

        return docs

    def _remove_documents(self, vectorstore: Chroma, source_files: list[str]):
        """Remove documents from specified source files to avoid duplicates."""
        if not source_files:
            return

        where_clause: Where = cast(Where, {"source_file": {"$in": source_files}})
        results = vectorstore.get(where=where_clause)
        if results["ids"]:
            print("removing_documents", len(results["ids"]), source_files)
            vectorstore.delete(ids=results["ids"])

    def setup_vectorstore(
        self, file_names: list[str], collection_name: str, force_rebuild: bool = False
    ) -> Chroma:
        """Set up vector store with incremental updates."""
        print("setting_up_vector_store", collection_name, len(file_names))

        # Get or create vector store
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_directory),
        )

        # Check cache and rebuild flag
        if not force_rebuild and self.vectorstore_cache is not None:
            return self.vectorstore_cache

        if force_rebuild:
            print("force_rebuild_requested", collection_name)
            changed_files = file_names
            self._remove_documents(vectorstore, file_names)
        else:
            # Check for changed and deleted files
            changed_files, deleted_files = self._get_changed_and_deleted_files(
                file_names
            )
            if not changed_files and not deleted_files:
                print("no_schema_files_changed", collection_name)
                self.vectorstore_cache = vectorstore
                return vectorstore
            print("processing_files", changed_files, "deleted", deleted_files)
            self._remove_documents(vectorstore, changed_files + deleted_files)

        # Load and add documents from changed files
        for file_name in changed_files:
            try:
                docs = self._load_documents(file_name)
                vectorstore.add_documents(docs)
                print("documents_added", file_name, len(docs))
            except Exception as e:
                print("error_loading_file", file_name, str(e))

        # Cache and return
        self.vectorstore_cache = vectorstore
        return vectorstore

    def clear_cache(self):
        """Clear the vector store cache."""
        self.vectorstore_cache = None


def get_vectorstore(force_rebuild: bool = False) -> Chroma:
    """Get or create vector store with intelligent caching."""
    manager = VectorStoreManager()
    return manager.setup_vectorstore(
        config.schema_files, config.collection_name, force_rebuild=force_rebuild
    )


def clear_vectorstore_cache():
    """Clear the vector store cache."""
    VectorStoreManager().clear_cache()
