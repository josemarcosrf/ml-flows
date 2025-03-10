import json
import os
from functools import wraps
from pathlib import Path

import click

from flows.shrag import playbook_qa
from flows.shrag.constants import (
    CHROMA_HOST_DEFAULT,
    CHROMA_PORT_DEFAULT,
    EMBEDDING_MODEL_DEFAULT,
    EMBEDDING_MODEL_ENV_VAR,
    LLM_BACKEND_DEFAULT,
    LLM_BACKEND_ENV_VAR,
    LLM_MODEL_DEFAULT,
    LLM_MODEL_ENV_VAR,
    SIMILARITY_CUTOFF_DEFAULT,
    SIMILARITY_TOP_K_DEFAULT,
)


def common_rag_options(func):
    @click.argument("chroma_collection_name")
    @click.option("--chroma-host", default=CHROMA_HOST_DEFAULT)
    @click.option("--chroma-port", type=int, default=CHROMA_PORT_DEFAULT)
    @click.option(
        "--llm-backend", default=os.getenv(LLM_BACKEND_ENV_VAR, LLM_BACKEND_DEFAULT)
    )
    @click.option(
        "--llm-model", default=os.getenv(LLM_MODEL_ENV_VAR, LLM_MODEL_DEFAULT)
    )
    @click.option(
        "--embedding-model",
        default=os.getenv(EMBEDDING_MODEL_ENV_VAR, EMBEDDING_MODEL_DEFAULT),
    )
    @click.option("--reranker-model", default=None)
    @click.option("--similarity-top-k", type=int, default=SIMILARITY_TOP_K_DEFAULT)
    @click.option("--similarity-cutoff", type=float, default=SIMILARITY_CUTOFF_DEFAULT)
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


@click.group()
def cli():
    """Welcome to the SHRAG's Command Line Interface"""


@cli.command()
@click.argument("input-directory")
@click.argument("output-directory")
@click.argument("playbook_json")
@common_rag_options
@click.option("-fg", "--file-glob", default="*.canonical.pdf", help="File glob pattern")
def run_playbook_qa_from_directory(
    input_directory: str,
    output_directory: str,
    playbook_json: str,
    chroma_collection_name: str,
    chroma_host: str,
    chroma_port: int,
    llm_backend: str,
    llm_model: str,
    embedding_model: str,
    reranker_model: str | None,
    similarity_top_k: int,
    similarity_cutoff: float,
    file_glob: str,
):
    """Runs the RAG dataflow on all document files in the specified directory
    using the document names as metafilters.

    Args:
        directory (str): Path to the directory containing playbook JSON files.
        chroma_collection_name (str): Name of the collection to use.
        chroma_host (str, optional): ChromaDB host. Defaults to "localhost".
        chroma_port (int, optional): ChromaDB port. Defaults to 8000.
        llm_backend (str, optional): LLM backend to use. Defaults to "openai".
        llm_model (str, optional): LLM model to use. Defaults to "gpt-4o".
        embedding_model (str, optional): Embedding model to use. Defaults to "text-embedding-3-small".
        reranker_model (str | None, optional): Reranker model to use. Defaults to None.
        similarity_top_k (int, optional): Number of top results to retrieve. Defaults to 5.
        similarity_cutoff (float, optional): Similarity cutoff for retrieval. Defaults to 0.3.
        file_glob (str, optional): File glob pattern. Defaults to "*.canonical.pdf".
    """
    # Iterate over all Document files in the directory
    for filename in Path(input_directory).rglob(file_glob):
        if filename.is_file():
            ext = file_glob.replace("*", "")
            fname = filename.name.replace(ext, "")
            print(f"⚙️ Processing {fname}")

            # Run the RAG dataflow
            meta_filters = {"name": fname}
            res = playbook_qa(
                playbook_json=playbook_json,
                meta_filters=meta_filters,
                chroma_collection_name=chroma_collection_name,
                chroma_host=chroma_host,
                chroma_port=chroma_port,
                llm_backend=llm_backend,
                llm_model=llm_model,
                embedding_model=embedding_model,
                reranker_model=reranker_model,
                similarity_top_k=similarity_top_k,
                similarity_cutoff=similarity_cutoff,
            )
            # Write the results to a file; concatenate the filters to the file name
            filters = "_".join(f"{k}={v}" for k, v in meta_filters.items())
            result_filename = f"{filters}_qa_results.json"

            output_directory = Path(output_directory)
            if not output_directory.exists():
                output_directory.mkdir(parents=True)

            with (output_directory / result_filename).open("w") as f:
                f.write(json.dumps(res, indent=2))


@cli.command()
@click.argument("playbook_json")
@common_rag_options
@click.option(
    "-m",
    "--meta_filters",
    multiple=True,
    type=str,
    help="Additional key:value pairs to be parsed as metadata filters",
)
def run_playbook_qa(
    playbook_json: str,
    meta_filters: str,
    chroma_collection_name: str,
    chroma_host: str,
    chroma_port: int,
    llm_backend: str,
    llm_model: str,
    embedding_model: str,
    reranker_model: str | None,
    similarity_top_k: int,
    similarity_cutoff: float,
):
    """Runs the RAG dataflow on the specified question library and proto questions
    and writes the results to a JSON file.

    Args:
        playbook_json (str): Path to the playbook JSON file.
        chroma_collection_name (str): Name of the collection to use.
        chroma_host (str, optional): ChromaDB host. Defaults to "localhost".
        chroma_port (int, optional): ChromaDB port. Defaults to 8000.
        llm_backend (str, optional): LLM backend to use. Defaults to "openai".
        llm_model (str, optional): LLM model to use. Defaults to "gpt-4o".
        embedding_model (str, optional): Embedding model to use. Defaults to "text-embedding-3-small".
        reranker_model (str | None, optional): Reranker model to use. Defaults to None.
        similarity_top_k (int, optional): Number of top results to retrieve. Defaults to 5.
        similarity_cutoff (float, optional): Similarity cutoff for retrieval. Defaults to 0.3.
        meta_filters (str): Metadata filters to apply to the questions.
    """
    # Parse additional_params into a dictionary
    meta_filters = (
        dict(param.split(":") for param in meta_filters) if meta_filters else {}
    )
    # Run the RAG dataflow
    res = playbook_qa(
        playbook_json=playbook_json,
        meta_filters=meta_filters,
        chroma_collection_name=chroma_collection_name,
        chroma_host=chroma_host,
        chroma_port=chroma_port,
        llm_backend=llm_backend,
        llm_model=llm_model,
        embedding_model=embedding_model,
        reranker_model=reranker_model,
        similarity_top_k=similarity_top_k,
        similarity_cutoff=similarity_cutoff,
    )
    # Write the results to a file; concatenate the filters to the file name
    filters = "_".join(f"{k}={v}" for k, v in meta_filters.items())
    with open(f"{filters}_qa_results.json", "w") as f:
        f.write(json.dumps(res, indent=2))


if __name__ == "__main__":
    cli()
