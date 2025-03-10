import base64
import json
import os
from pathlib import Path

import click
import cloudpickle
from tabulate import tabulate

from flows import collect_public_flows
from flows.deploy import deploy_flow, PoolType

# Default storage path for Prefect
DEFAULT_PREFECT_STORAGE_PATH = Path.home() / ".prefect" / "storage"


@click.group()
def cli():
    """Flows CLI"""


@cli.command("ls")
def list_flows():
    """List all publicly available flows"""
    repo_root = Path.cwd()
    rows = []
    headers = ["Flow Name", "From", "Flow Parameters"]
    for flow_name, flow in collect_public_flows().items():
        code_file_path = Path(flow.fn.__code__.co_filename)
        flow_path = code_file_path.relative_to(repo_root)
        flow_params = {
            p: p_info.get("description", "N/D")
            for p, p_info in flow.parameters.properties.items()
        }
        params_str = "- " + "\n- ".join(f"{p}: {d}" for p, d in flow_params.items())
        rows.append((flow_name, flow_path, params_str))
    print(
        tabulate(
            rows,
            headers,
            tablefmt="fancy_grid",
            showindex=True,
        )
    )


@cli.command("deploy")
@click.argument("flow_name", type=click.Choice(list(collect_public_flows().keys())))
@click.argument("deployment_name")
@click.argument("pool-type", type=click.Choice([p.value for p in PoolType]))
@click.argument("work-pool-name")
@click.option("-b", "--build", is_flag=True)
@click.option("-t", "--flow_tags", multiple=True, default=["LINT"])
def deploy_flow_cli(
    flow_name: str,
    deployment_name: str,
    pool_type: str,
    work_pool_name: str,
    build: bool = False,
    flow_tags: list[str] | None = None,
):
    """Deploy a public flow to a Docker or Process pool.

    e.g.: Deploy the playbook-qa flow to a deployment called DEV on a 'Process' pool named 'test'
    python -m flows deploy playbook-qa DEV process test -t qa -t playbook

    Args:
        flow_name (str): Name fo the flow to deploy
        deployment_name (str): Name under which the flow will be deployed
        pool_type (str): Prefect type of pool to deploy to
        work_pool_name (str): Name of the Prefect work pool
        build (bool, optional): Wether to build docker image. Defaults to False.
        flow_tags (list[str] | None, optional): List of Prefect tags. Defaults to ['LINT'].
    """
    deploy_flow(flow_name, deployment_name, pool_type, work_pool_name, build, flow_tags)


@cli.command("read-result")
@click.argument("result_id")
@click.option(
    "-s",
    "--storage-path",
    default=os.getenv("PREFECT_LOCAL_STORAGE_PATH", DEFAULT_PREFECT_STORAGE_PATH),
)
def read_from_storage(result_id: str, storage_path: str):
    rfile = Path(storage_path).resolve() / result_id
    if rfile.exists():
        res = json.load(rfile.open())
        result = cloudpickle.loads(base64.b64decode(res["data"]))
        print(json.dumps(result, indent=2))
    else:
        print(f"💥 {rfile} could not be found!")


@click.group("chroma")
def chroma_cli():
    """ChromaDB CLI"""
    pass


@chroma_cli.command("ls")
@click.option("--host", default=os.getenv("CHROMA_HOST", "localhost"))
@click.option("--port", default=os.getenv("CHROMA_PORT", 8000))
def list_collections(host: str, port: int):
    """List all collections in the ChromaDB"""
    from flows.common.clients.chroma import ChromaClient

    client = ChromaClient(host, port)
    print("================ Collections ================")
    for collection in client.db.list_collections():
        print(f"- {collection}")

    print("✨ Done!")


@chroma_cli.command("lsc")
@click.argument("collection_name")
@click.option("-m", "--metadata-fields", default=["doc_id"], multiple=True)
@click.option("--host", default=os.getenv("CHROMA_HOST", "localhost"))
@click.option("--port", default=os.getenv("CHROMA_PORT", 8000))
def list_collection(
    collection_name: str, metadata_fields: list[str], host: str, port: int
):
    """List a ChromaDB's collection contents"""
    from flows.common.clients.chroma import ChromaClient

    client = ChromaClient(host, port)
    print(f"================ Collection {collection_name} ================")
    client.print_collection_contents(
        collection_name=collection_name, metadata_fields=metadata_fields
    )
    print("✨ Done!")


if __name__ == "__main__":
    cli.add_command(chroma_cli)
    cli()
