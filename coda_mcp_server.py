"""
This script implements a FastMCP server that acts as a bridge to the Coda API.
It allows MCP clients to interact with Coda documents, tables, and rows
by calling the tools defined in this server.

The server uses the `codaio` Python library to communicate with the Coda API.
"""
import os
import asyncio
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from codaio import Coda, Document
import json
import pandas as pd
# --- Environment Setup ---
# Load environment variables from a .env file for local development.
load_dotenv()


# --- Configuration ---
# Retrieve the Coda API key from environment variables.
CODA_API_KEY = os.getenv("CODA_API_KEY")
WORKING_DIR_RESTRICTION = os.getenv("WORKING_DIR_RESTRICTION")

# Ensure the API key is set, otherwise raise an error.
if not CODA_API_KEY:
    raise ValueError("The CODA_API_KEY environment variable is not set.")


def resolve_path(path: str) -> str:
    if not WORKING_DIR_RESTRICTION:
        return os.path.abspath(os.path.normpath(path))

    # Ensure restriction itself is absolute and normalized
    abs_restriction = os.path.abspath(os.path.normpath(WORKING_DIR_RESTRICTION))

    # Ensure we are working with absolute normalized paths
    if not os.path.isabs(path):
        full_path = os.path.abspath(os.path.normpath(os.path.join(abs_restriction, path)))
    else:
        full_path = os.path.abspath(os.path.normpath(path))

    # Check if the resolved path is within the restriction
    if os.path.commonpath([abs_restriction, full_path]) == abs_restriction:
        return full_path

    raise ValueError(f"Access to path {path} is restricted to {WORKING_DIR_RESTRICTION}")


# --- Coda API Client Initialization ---
# Create an instance of the Coda API client using the provided API key.
# This client will be used by all tools to make requests to the Coda API.
coda = Coda(CODA_API_KEY)


# --- MCP Server Definition ---
# Instantiate the FastMCP server, giving it a name and instructions
# that can be displayed to clients.
mcp = FastMCP(
    name="Coda MCP Server",
    instructions="A server to interact with the Coda API."
)


# --- MCP Tools ---

@mcp.tool()
async def list_docs():
    """
    Lists all available Coda documents that the API key has access to.

    Returns:
        dict: a dictionary with the doc names and doc IDs in an 'items' list.
    """
    try:
        docs = await asyncio.to_thread(coda.list_docs)
        items = [{"name": doc["name"], "id": doc["id"]} for doc in docs.get("items", [])]
        return {"items": items}
        
    except Exception as e:
        raise RuntimeError(f"An error occurred while listing documents: {e}")


@mcp.tool()
async def list_tables(doc_id: str):
    """
    Lists all tables within a specific Coda document.

    Args:
        doc_id (str): The ID of the Coda document to inspect.

    Returns:
        dict: A dictionary mapping table names to their IDs.
    """
    try:
        # Initialize the Document object
        document = await asyncio.to_thread(Document, doc_id, coda=coda)
        tables = await asyncio.to_thread(document.list_tables)
        doc_dict = {table.name: table.id for table in tables}

        return doc_dict
    except Exception as e:
        raise RuntimeError(f"An error occurred while listing tables for doc '{doc_id}': {e}")
    
@mcp.tool()
async def get_table_content(doc_id: str, table_id: str, output_filepath: str):
    """
    Retrieves all rows and their content from a specific table in a Coda document.
    Saves the table to a .csv file and returns column metadata.

    Args:
        doc_id (str): The ID of the Coda document.
        table_id (str): The ID of the table to retrieve content from.
        output_filepath (str): The filepath where the table contents will be saved.
    Returns:
        dict: A dictionary containing 'num_columns' and either 'columns' (list) or 'summary' (string).
    """
    try:
        resolved_output_filepath = resolve_path(output_filepath)
        doc = await asyncio.to_thread(Document, doc_id, coda=coda)
        table = await asyncio.to_thread(doc.get_table, table_id)

        data = await asyncio.to_thread(table.to_dict)
        table_df = pd.DataFrame(data)

        await asyncio.to_thread(table_df.to_csv, resolved_output_filepath, index=False)

        cols = list(table_df.columns)
        num_cols = len(cols)

        result = {"num_columns": num_cols}

        if num_cols < 30:
            result["columns"] = cols
        else:
            first_15 = cols[:15]
            last_15 = cols[-15:]
            result["summary"] = f"number of columns = {num_cols}, first 15 columns = {first_15}; last 15 columns = {last_15}"

        return result
    except Exception as e:
        raise RuntimeError(f"An error occurred while getting content for table '{table_id}': {e}")

@mcp.tool()
async def get_table_attachments(doc_id: str, table_id: str, attachment_column_name: str):
    """
    Get file attachment information (URLs and metadata) from a Coda table column.

    Args:
        doc_id: Coda document ID
        table_id: Coda table ID
        attachment_column_name: Name of column containing attachments

    Returns:
        List of dicts with file metadata (name, url, mimeType, size)
    """
    try:
        url = f"https://coda.io/apis/v1/docs/{doc_id}/tables/{table_id}/rows"
        headers = {"Authorization": f"Bearer {CODA_API_KEY}"}
        params = {
            "valueFormat": "rich",
            "useColumnNames": True
        }

        response = await asyncio.to_thread(requests.get, url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        attachments = []

        for item in data.get("items", []):
            row_id = item.get("id")
            values = item.get("values", {})
            file_data = values.get(attachment_column_name)

            if isinstance(file_data, list):
                for file_info in file_data:
                    if isinstance(file_info, dict) and "url" in file_info:
                        attachments.append({
                            "row_id": row_id,
                            "name": file_info.get("name"),
                            "url": file_info.get("url"),
                            "mimeType": file_info.get("mimeType"),
                            "size": file_info.get("size")
                        })
            elif isinstance(file_data, dict) and "url" in file_data:
                attachments.append({
                    "row_id": row_id,
                    "name": file_data.get("name"),
                    "url": file_data.get("url"),
                    "mimeType": file_data.get("mimeType"),
                    "size": file_data.get("size")
                })

        return attachments
    except Exception as e:
        raise RuntimeError(f"An error occurred while getting attachments: {e}")

@mcp.tool()
async def download_coda_attachments(doc_id: str, table_id: str, attachment_column_name: str, output_dir: str):
    """
    Download all files from a Coda table attachment column to a local directory.

    Args:
        doc_id: Coda document ID
        table_id: Coda table ID
        attachment_column_name: Name of column containing attachments
        output_dir: Directory to save downloaded files

    Returns:
        List of downloaded file paths
    """
    try:
        attachments = await get_table_attachments(doc_id, table_id, attachment_column_name)

        resolved_output_dir = resolve_path(output_dir)
        os.makedirs(resolved_output_dir, exist_ok=True)
        downloaded_paths = []

        for att in attachments:
            file_url = att.get("url")
            file_name = att.get("name")

            if not file_url or not file_name:
                continue

            # Ensure unique filename if multiple rows have same filename
            # using row_id as prefix
            row_id = att.get("row_id", "unknown")
            unique_name = f"{row_id}_{file_name}"
            file_path = os.path.join(resolved_output_dir, unique_name)

            response = await asyncio.to_thread(requests.get, file_url, stream=True)
            response.raise_for_status()

            def save_attachment():
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

            await asyncio.to_thread(save_attachment)

            downloaded_paths.append(file_path)

        return downloaded_paths
    except Exception as e:
        raise RuntimeError(f"An error occurred while downloading attachments: {e}")



import shutil
import zipfile

@mcp.tool()
async def unzip_and_inspect_data(zip_filepath: str, output_dir: str):
    """
    Unzips a file and inspects any CSV files found within it, returning column metadata.

    Args:
        zip_filepath (str): The path to the zip file to unzip.
        output_dir (str): The directory where the files will be extracted.
    Returns:
        dict: A dictionary mapping filenames to their column metadata/summaries.
    """
    try:
        resolved_zip_path = resolve_path(zip_filepath)
        resolved_output_dir = resolve_path(output_dir)

        os.makedirs(resolved_output_dir, exist_ok=True)

        def extract_zip():
            with zipfile.ZipFile(resolved_zip_path, 'r') as zip_ref:
                zip_ref.extractall(resolved_output_dir)

        await asyncio.to_thread(extract_zip)

        results = {}

        for root, _, files in os.walk(resolved_output_dir):
            for file in files:
                if file.endswith('.csv'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, resolved_output_dir)

                    try:
                        df = await asyncio.to_thread(pd.read_csv, file_path)
                        cols = list(df.columns)
                        num_cols = len(cols)

                        file_info = {"num_columns": num_cols}

                        if num_cols < 30:
                            file_info["columns"] = cols
                        else:
                            first_15 = cols[:15]
                            last_15 = cols[-15:]
                            file_info["summary"] = f"number of columns = {num_cols}, first 15 columns = {first_15}; last 15 columns = {last_15}"

                        results[rel_path] = file_info
                    except Exception as csv_err:
                        results[rel_path] = {"error": str(csv_err)}

        return results
    except Exception as e:
        raise RuntimeError(f"An error occurred while unzipping and inspecting data: {e}")

# --- Server Execution ---
# This block ensures the server only runs when the script is executed directly.
if __name__ == "__main__":
    # Start the FastMCP server. It will handle incoming requests based on the
    # defined tools. By default, it runs on http://localhost:8787.
    mcp.run()
