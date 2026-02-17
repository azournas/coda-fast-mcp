import asyncio
import os
import sys
import pandas as pd
from coda_mcp_server import get_table_content

async def test_get_table_content_new_format():
    # Note: These IDs are specific to the test environment/Coda account
    doc_id = 'b_EMt7giMc'
    table_id = 'table-L0BTgR58Pp'
    output_file = 'test_output_temp.csv'

    try:
        if os.path.exists(output_file):
            os.remove(output_file)

        result = await get_table_content(doc_id, table_id, output_file)

        # Verify CSV was saved
        assert os.path.exists(output_file)
        df = pd.read_csv(output_file)

        # Verify return structure
        assert isinstance(result, dict)
        assert 'num_columns' in result
        assert result['num_columns'] == len(df.columns)

        if len(df.columns) < 30:
            assert 'columns' in result
            assert result['columns'] == list(df.columns)
        else:
            assert 'summary' in result
            assert "number of columns =" in result['summary']

        print("Test passed!")
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)

if __name__ == "__main__":
    asyncio.run(test_get_table_content_new_format())
