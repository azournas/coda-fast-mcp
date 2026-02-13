"""
This script implements a FastMCP server that acts as a bridge to the Coda API.
It allows MCP clients to interact with Coda documents, tables, and rows
by calling the tools defined in this server.

The server uses the `codaio` Python library to communicate with the Coda API.
"""
import os
import asyncio
# from dotenv import load_dotenv
# from mcp.server.fastmcp import FastMCP, Context
from codaio import Coda, Document
import json
import pandas as pd

# --- Environment Setup ---
# Load environment variables from a .env file for local development.
# load_dotenv()


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
# mcp = FastMCP(
#     name="Coda MCP Server",
#     instructions="A server to interact with the Coda API."
# )


# --- MCP Tools ---

# @mcp.tool()
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

# @mcp.tool()
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
        document_id = doc_id

        # Initialize the Document object
        document = Document(document_id, coda=coda)
        doc_dict = {}
        for i in document.list_tables():
            if "data" in i.name.lower():
                print(f"{i.name}: [{i.id}]")
                doc_dict[i.name] = i.id
        
        return doc_dict
        
    except Exception as e:
        return f"An error occurred while listing tables for doc '{doc_id}': {e}"
    
# @mcp.tool()
def get_table_content(doc_id: str, table_id: str):
    """
    Retrieves all rows and their content from a specific table in a Coda document.

    Args:
        doc_id (str): The ID of the Coda document.
        table_id (str): The ID of the table to retrieve content from.

    Returns:
        DataFrame: A pandas dataframe that contains the table contents
              Returns an error message string on failure.
    """
    try:
        doc = Document(doc_id, coda=coda)
        table = doc.get_table(table_id)
        return pd.DataFrame(table.to_dict())
    except Exception as e:
        return f"An error occurred while getting content for table '{table_id}': {e}"


# --- Server Execution ---
# This block ensures the server only runs when the script is executed directly.
# if __name__ == "__main__":
#     # Start the FastMCP server. It will handle incoming requests based on the
#     # defined tools. By default, it runs on http://localhost:8787.
#     mcp.run()



print(list_docs())
# This is the Document ID for HTS15 Coda document

document_id = 'b_EMt7giMc'
document = Document(document_id, coda=coda)
for i in document.list_tables():
    if "data" in i.name.lower():
        print(f"{i.name}: [{i.id}]")

print(list_tables(document_id))

user_defined_metadata_id = 'table-L0BTgR58Pp'
rapidfire_id = 'grid-ZeNjsNXzzc'

table1 = pd.DataFrame(document.get_table(user_defined_metadata_id).to_dict())
print(table1.head())

table1 = get_table_content(document_id, user_defined_metadata_id)
print(table1.head())


table2 = pd.DataFrame(document.get_table(rapidfire_id).to_dict())
print(table2.head())

table2 = get_table_content(document_id, rapidfire_id)
print(table2.head())

