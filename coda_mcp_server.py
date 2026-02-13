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

# Ensure the API key is set, otherwise raise an error.
if not CODA_API_KEY:
    raise ValueError("The CODA_API_KEY environment variable is not set.")


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
def list_docs():
    """
    Lists all available Coda documents that the API key has access to.

    Returns:
        dict: a dictionary with the doc name and doc ID
    """
    try:
        docs = coda.list_docs()
        # The response from coda.list_docs() is a list of full document objects.
        # We simplify it to return only the name and ID for clarity.
        os.system('curl -H "Authorization: Bearer $CODA_API_KEY" https://coda.io/apis/v1/docs > curl_output.json')
        docs = json.loads(open('curl_output.json').read())
        # Print document names and IDs
        print("Document Name, Document ID")
        for doc in docs['items']:
            print(f"{doc['name']}, {doc['id']}")
        return docs
    except Exception as e:
        return f"An error occurred while listing documents: {e}"


@mcp.tool()
def list_tables(doc_id: str):
    """
    Lists all tables within a specific Coda document. 

    Args:
        doc_id (str): The ID of the Coda document to inspect.

    Returns:
        list: A list of dictionaries, where each dictionary represents a table
              and contains the table's 'name' and 'id'.
              Returns an error message string on failure.
    """
    try:
        # Initialize the Document object
        document = Document(doc_id, coda=coda)
        doc_dict = {}
        for i in document.list_tables():
            if "data" in i.name.lower():
                print(f"{i.name}: [{i.id}]")
                doc_dict[i.name] = i.id
        
        return doc_dict
    except Exception as e:
        return f"An error occurred while listing tables for doc '{doc_id}': {e}"
    
@mcp.tool()
def get_table_content(doc_id: str, table_id: str, output_filepath: str):
    """
    Retrieves all rows and their content from a specific table in a Coda document. Saves the table to a .csv file

    Args:
        doc_id (str): The ID of the Coda document.
        table_id (str): The ID of the table to retrieve content from.
        output_filepath (str): The filepath where the table contents will be saved
    Returns:
        DataFrame: A pandas dataframe that contains the table contents
              Returns an error message string on failure.
    """
    try:
        doc = Document(doc_id, coda=coda)
        table = doc.get_table(table_id)
        table_df = pd.DataFrame(table.to_dict())
        table_df.to_csv(output_filepath)
        return table_df
    except Exception as e:
        return f"An error occurred while getting content for table '{table_id}': {e}"

@mcp.tool()
def get_table_attachments(doc_id: str, table_id: str, attachment_column_name: str):
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

        response = requests.get(url, headers=headers, params=params)
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
        return f"An error occurred while getting attachments: {e}"

@mcp.tool()
def download_coda_attachments(doc_id: str, table_id: str, attachment_column_name: str, output_dir: str):
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
        attachments = get_table_attachments(doc_id, table_id, attachment_column_name)
        if isinstance(attachments, str):  # Error message
            return attachments

        os.makedirs(output_dir, exist_ok=True)
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
            file_path = os.path.join(output_dir, unique_name)

            response = requests.get(file_url, stream=True)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            downloaded_paths.append(file_path)

        return downloaded_paths
    except Exception as e:
        return f"An error occurred while downloading attachments: {e}"



# --- Server Execution ---
# This block ensures the server only runs when the script is executed directly.
if __name__ == "__main__":
    # Start the FastMCP server. It will handle incoming requests based on the
    # defined tools. By default, it runs on http://localhost:8787.
    mcp.run()
