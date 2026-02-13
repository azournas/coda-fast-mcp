# Coda Fast MCP Server

This project implements a Fast MCP server to interact with the Coda API using the `codaio` Python package.

## Setup

1.  **Install dependencies:**

    Create a virtual environment and install the required packages from `requirements.txt`:

    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Set up your Coda API Key:**

    Create a `.env` file in the root of the project. You can copy the example file:

    ```bash
    cp .env.example .env
    ```

    Then, open the `.env` file and replace `"your-coda-api-key-here"` with your actual Coda API key.

## Usage

To start the server, run the following command:

```bash
python coda_mcp_server.py
```

The server will start and be available for clients to connect to.

## Available Tools

The server exposes the following tools:

*   `list_docs()`: Lists all available Coda documents.
*   `list_tables(doc_id: str)`: Lists all tables in a given Coda document.
*   `get_table_content(doc_id: str, table_id: str)`: Retrieves the content of a specific table in a Coda document.
