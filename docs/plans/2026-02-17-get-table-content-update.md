# get_table_content Tool Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modify the `get_table_content` tool in `coda_mcp_server.py` to return a structured summary of columns instead of the full table data, while still saving the data to a CSV.

**Architecture:** Use pandas to process the table data, extract column metadata, and construct a conditional return dictionary based on the number of columns (threshold 30).

**Tech Stack:** Python, pandas, asyncio, codaio, FastMCP.

---

### Task 1: Create a Regression Test Script

**Files:**
- Create: `tests/test_get_table_content_updated.py`

**Step 1: Write the failing test**

```python
import asyncio
import os
import sys
import pandas as pd
from coda_mcp_server import get_table_content

async def test_get_table_content_new_format():
    # Use existing test doc/table IDs from coda_mcp_tools_test.py
    doc_id = 'b_EMt7giMc'
    table_id = 'table-L0BTgR58Pp'
    output_file = 'test_output.csv'
    
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

if __name__ == "__main__":
    asyncio.run(test_get_table_content_new_format())
```

**Step 2: Run test to verify it fails**

Run: `python3 tests/test_get_table_content_updated.py`
Expected: FAIL (AttributeError or AssertionError because it currently returns a list of rows)

**Step 3: Commit**

```bash
git add tests/test_get_table_content_updated.py
git commit -m "test: add regression test for updated get_table_content format"
```

### Task 2: Update get_table_content Implementation

**Files:**
- Modify: `coda_mcp_server.py:106-128`

**Step 1: Write minimal implementation**

```python
@mcp.tool()
async def get_table_content(doc_id: str, table_id: str, output_filepath: str):
    """
    Retrieves all rows from a Coda table, saves to CSV, and returns column metadata.
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
            result["summary"] = f"number of columns = {num_cols}, first 15 columns = {first_15} last 15 columns = {last_15}"
            
        return result
    except Exception as e:
        raise RuntimeError(f"An error occurred while getting content for table '{table_id}': {e}")
```

**Step 2: Run test to verify it passes**

Run: `python3 tests/test_get_table_content_updated.py`
Expected: PASS

**Step 3: Commit**

```bash
git add coda_mcp_server.py
git commit -m "feat: update get_table_content to return column metadata and summary"
```

### Task 3: Push and PR

**Step 1: Push branch**

Run: `git push -u origin feature/get-table-content-update`

**Step 2: Verify state**

Run: `git status`
Expected: Branch pushed, no uncommitted changes.
