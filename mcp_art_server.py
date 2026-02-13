# mcp_art_server.py
import asyncio
import os
import subprocess
from typing import Dict, Any

import pandas as pd
from mcp.server.fastmcp import FastMCP, Context
import litellm
import sys
litellm.modify_params = True
# --- Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")



if not OPENAI_API_KEY:
    raise ValueError("The OPENAI_API_KEY environment variable is not set.")

BASE_URL = os.getenv("LITELLM_BASE_URL")


# LLM_CLIENT = OpenAI(base_url = BASE_URL,
#                     api_key=OPENAI_API_KEY)

# ART_CODE_DIR = "art_code"

# os.makedirs(ART_CODE_DIR, exist_ok=True)

# --- MCP Server Definition ---
mcp = FastMCP(
    name="ART Analysis Server",
    instructions="A server to run ART analysis by generating and executing code."
)


@mcp.resource("art://template")
def get_art_template() -> str:
    """Provides basic documentation for the recommendation engine"""
    
    with open('art_template.py', 'r') as file:
        return file.read()
    
@mcp.resource("art://liquid_handling_template")
def get_art_template() -> str:
    """Provides a template to generate liquid handling instructions"""
    
    with open('/app/art_code/liquid_handler_instructions_template.py', 'r') as file:
        return file.read()

@mcp.resource("art://stock_concentrations")
def get_art_template() -> str:
    """contains the stock concentrations"""
    
    with open('/app/Isoprenol_media_optimization/data/stock_concentrations.csv', 'r') as file:
        return file.read()

@mcp.resource("art://docs")
def get_RE_docs() -> str:
    """Provides the ART Python code template."""
    with open('recommendationEngine_docs.txt', 'r') as file:
        return file.read()
    
@mcp.resource("art://preprocess")
def get_art_optimizer() -> str:
    """Provides the sub class, optimizer"""
    with open('/app/art-core/art/preprocess.py', 'r') as file:
        return file.read()
    
@mcp.resource("art://optimizer")
def get_art_optimizer() -> str:
    """Provides the sub class, optimizer"""
    with open('/app/art-core/art/core/optimizer.py', 'r') as file:
        return file.read()
    
@mcp.resource("art://recommender")
def get_art_recommender() -> str:
    """Provides the sub class, recommender"""
    with open('/app/art-core/art/core/recommender.py', 'r') as file:
        return file.read()
    
@mcp.resource("art://recommendation_engine")
def get_art_recommendationEngine() -> str:
    """Provides the code for the main class, recommendation engine"""
    with open('/app/art-core/art/core/recommendation_engine.py', 'r') as file:
        return file.read()


# --- Helper Functions ---
def inspect_csv_file(filename: str) -> Dict[str, Any]:
    try:
        df = pd.read_csv(filename)
        columns = df.columns.tolist()
        return {
            "success": True,
            "columns": columns,
            "description": f"Successfully read '{filename}'. Columns: {columns}."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def read_file(filepath: str) -> str:
    with open(filepath, 'r') as file:
        return file.read()

def save_file(filepath: str, content: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)

async def run_art_in_docker(script_path: str) -> str:
    host_project_path = os.getenv("HOST_PROJECT_PATH")
    art_src_path = os.getenv("ART_SRC_PATH")
    if not host_project_path or not art_src_path:
        return "Error: HOST_PROJECT_PATH or ART_SRC_PATH are not set."

    command = [
        "docker", "run", "--rm", "--user", "artuser",
        "-v", f"{host_project_path}:/app",
        "-v", f"{art_src_path}:/app/art",
        "-w", "/app",
        "--pull", "never", "--entrypoint", "python",
        "jbei/art-core", script_path
    ]

    def blocking_docker_run():
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=3600)
            return f"--- ART Core Execution Successful ---\nSTDOUT:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"--- ERROR Running ART Core ---\nSTDERR:\n{e.stderr}"
        except subprocess.TimeoutExpired as e:
            return f"--- ERROR: ART Core execution timed out. ---\nSTDERR:\n{e.stderr}"

    return await asyncio.to_thread(blocking_docker_run)

@mcp.tool()
def read_csv_file(filename: str):
    df = pd.read_csv(filename)
    return df

# --- Core MCP Tool ---
@mcp.tool()
def get_directory_structure_string(startpath):
    """
    Returns the directory structure as a string starting from the given path.
    """
    
    # Use a list to accumulate the output lines
    output_lines = []
    
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        
        # Add the directory line
        output_lines.append(f'{indent}{os.path.basename(root)}/')
        
        subindent = ' ' * 4 * (level + 1)
        
        # Add the file lines
        for f in files:
            output_lines.append(f'{subindent}{f}')
            
    # Join all lines with a newline character and return the single string
    return '\n'.join(output_lines)

@mcp.tool()
async def generate_robotic_instructions(prompt: str, project_dir: str, output_code_dir: str, sample_file_path:str, ctx: Context
) -> str:
    """
    Reads the experimental recommendations, such as these generated by the `run_art_analysis` function and generates robotic instructions for creating these media compositions:
    Args:
        prompt: The user's request for robotic instructions generation
        project_dir: The project directory, where all files are saved
        output_code_dir: directory where the code will be saved
        sample_file_path: path to one of the files generated by run_art_analysis as a sample
        ctx: The MCP Context object, injected by the server.
    """

    try:
        print(prompt, file=sys.stderr, flush=True)
        print("--- SERVER: Step 1/5: Analyzing directory structure... ---", file=sys.stderr, flush=True)
        await ctx.info("--- SERVER: Step 1/5: Analyzing directory structure... ---")

        dir_struct = get_directory_structure_string(project_dir)

        print("--- SERVER: Step 2/5: Reading resources... ---", file=sys.stderr, flush=True)
        await ctx.info("--- SERVER: Step 2/5: Reading resources... ---")

        lh_template = await ctx.read_resource("art://liquid_handling_template")
        stock_concentrations = await ctx.read_resource("art://stock_concentrations")

        sample_file = pd.read_csv(sample_file_path)

        generation_prompt = f"""
        Generate robotic instructions for the current DBTL cycle.
        all of the data regarding this project are in `{project_dir}`, which has the following structure.\n
        [directory structure]:\n
        {dir_struct}\n

        Here is a template on how to generate liquid handling instructions:\n
        [code template]:\n
        {lh_template}\n

        Here are the stock concentrations too:\n
        [stock concentrations]:\n
        {stock_concentrations}

        The files you will be starting with look like this:\n
        [sample file]:\n
        {sample_file}
        

        Return only the raw, complete Python code.
        """

        print("--- Step 3/5: Generating ART code with an LLM... ---", file=sys.stderr, flush=True)

        await ctx.info("Step 3/5: Generating ART code with an LLM...")
        response = litellm.completion(
            model='anthropic/claude-sonnet',
            messages=[{"role": "user", "content": generation_prompt}],
            api_base=BASE_URL,
            api_key=OPENAI_API_KEY
        )
        generated_code = response.choices[0].message.content.strip().removeprefix("```python").removesuffix("```").strip()

        await ctx.info("ART code generated.")
        print("--- Step 4/5: Saving generated code... ---", file=sys.stderr, flush=True)

        await ctx.info("Step 4/5: Saving generated code...")
        script_path = os.path.join(output_code_dir, "generated_LH_code.py")
        save_file(script_path, generated_code)
        await ctx.info(f"Code saved to {script_path}")
        print(f"Code saved to {script_path}", file=sys.stderr, flush=True)

        print("--- Step 5/5: Executing ART code in container... ---", file=sys.stderr, flush=True)

        await ctx.info("Step 5/5: Executing ART code in container...")
        result = await run_art_in_docker(script_path)
        await ctx.info("ART execution finished.")
        return result

    except Exception as e:
        await ctx.error(f"An unexpected error occurred in the workflow: {e}")
        return f"Workflow failed with an error: {str(e)}"


@mcp.tool()
async def create_template_csv(path: str, csv_prompt: str, ctx: Context) -> str:
    """
    Creates a CSV template file for ART input.
    Args:
        path: The path where the CSV template file should be created.
        csv_prompt: The prompt for the CSV content.
        ctx: The MCP Context object, injected by the server.
    """
    try:
        await ctx.info("Creating CSV template file...")

        template = read_file('data/template.csv')
        prompt_to_llm = f"Generate a CSV template for ART based on the following description:\n{csv_prompt}, following the format of\n\n{template}\n\nProvide only the CSV content without any additional text."
        print(prompt_to_llm, file=sys.stderr, flush=True)
        response = litellm.completion(
            model='anthropic/claude-sonnet',
            messages=[{"role": "user", "content": prompt_to_llm}],
            api_base=BASE_URL,
            api_key=OPENAI_API_KEY
        )
        print(path, file=sys.stderr, flush=True)
        print(response, file=sys.stderr, flush=True)
        save_file(path, response.choices[0].message.content.strip())
        await ctx.info(f"CSV template file created at {path}")
        return f"CSV template file created at {path}"
    except Exception as e:
        await ctx.error(f"Failed to create CSV template file: {e}")
        return f"Failed to create CSV template file: {e}"

@mcp.tool()
async def answer_question(question: str, ctx: Context) -> str:
    """
    Answers a question using an LLM.
    Args:
        question: The question to answer.
        ctx: The MCP Context object, injected by the server.
    """
    try:
        await ctx.info("Generating answer using LLM...")
        await ctx.info("Step 1/5: Reading Resources...")
        template_code = await ctx.read_resource("art://template")
        recEngine_docs = await ctx.read_resource("art://docs")
        optimizer_code = await ctx.read_resource("art://optimizer")
        recommender_code = await ctx.read_resource("art://recommender")
        await ctx.info("Step 2/5: Asking LLM...")
        prompt_to_llm = f"Answer the following question concisely:\n{question}\n\nHere is some relevant information:\n[Template]:\n```python\n{template_code}\n```\n[Docs]:\n```text\n{recEngine_docs}\n```[Optimizer]:\n```python\n{optimizer_code}\n```[Recommender]:\n```python\n{recommender_code}\n```"
        response = litellm.completion(
            model='anthropic/claude-sonnet',
            messages=[{"role": "user", "content": prompt_to_llm}],
            api_base=BASE_URL,
            api_key=OPENAI_API_KEY
        )
        answer = response.choices[0].message.content.strip()
        print(f"--- LLM Answer Generated ---\n{answer}", file=sys.stderr, flush=True)
        await ctx.info("Answer generated.")
        return answer
    except Exception as e:
        await ctx.error(f"An error occurred while answering the question: {e}")
        return f"Failed to answer question: {str(e)}"

@mcp.tool()
async def run_art_analysis(
    prompt: str, data_path: str, output_dir: str, ctx: Context, secondary_prompt: str = None
) -> str:
    """
    Analyzes data, generates ART code, executes it in Docker, and returns the result.
    Args:
        prompt: The user's goal for the analysis.
        data_path: Path to the input CSV data file.
        output_dir: Path to save any code generated and any output files
        template_path: Path to the ART code template.
        ctx: The MCP Context object, injected by the server.
        secondary_prompt (optional): A secondary goal defined by the user as a follow-up to prompt
    """

    try:
        print(prompt, file=sys.stderr, flush=True)
        print(secondary_prompt, file=sys.stderr, flush=True)
        print(f"--- SERVER: Step 1/5: Analyzing data file... {data_path}---", file=sys.stderr, flush=True)
        await ctx.info("Step 1/5: Analyzing data file...")
        
        analysis = inspect_csv_file(data_path)
        if not analysis["success"]:
            await ctx.error(f"Data analysis failed: {analysis['error']}")
            # return f"Failed to analyze data file: {analysis['error']}"
            await ctx.info(f"Data analysis failed: with error {analysis['error']}. Need to create a new template for the csv file")
            print(f"Data analysis failed: with error {analysis['error']}. Need to create a new template for the csv file", file=sys.stderr, flush=True)

        else:
            await ctx.info(f"Data analysis complete: {analysis['description']}")
        print("--- Step 2/5: Reading Resources... ---", file=sys.stderr, flush=True)

        await ctx.info("Step 2/5: Reading Resources...")
        template_code = await ctx.read_resource("art://template")
        recEngine_docs = await ctx.read_resource("art://docs")
        recEngine_code = await ctx.read_resource("art://recommendation_engine")
        optimizer_code = await ctx.read_resource("art://optimizer")
        recommender_code = await ctx.read_resource("art://recommender")
        print("--- Step 3/5: Generating ART code with an LLM... ---", file=sys.stderr, flush=True)

        await ctx.info("Step 3/5: Generating ART code with an LLM...")
        
        os.makedirs(output_dir, exist_ok=True)
        generation_prompt = f"""Complete the following ART code template based on the user's request and data analysis.\n
        User Request: {prompt}\n
        Target directory: {output_dir} \n 
        Data Analysis: {analysis['description']}\n
        [Template]:\n
        ```python\n
        {template_code}\n
        ```\n
        [Docs]:
        ```text\n
        {recEngine_docs}\n
        ```\n
        [Optimizer]:\n
        ```python\n
        {optimizer_code}\n
        ```\n
        [Recommender]:\n
        ```python\n
        {recommender_code}\n
        ```\n
        Return only the raw, complete Python code."""
        
        response = litellm.completion(
            model='anthropic/claude-sonnet',
            messages=[{"role": "user", "content": generation_prompt}],
            api_base=BASE_URL,
            api_key=OPENAI_API_KEY
        )
        generated_code = response.choices[0].message.content.strip().removeprefix("```python").removesuffix("```").strip()
        await ctx.info("ART code generated.")
        print("--- Step 4/5: Saving generated code... ---", file=sys.stderr, flush=True)

        await ctx.info("Step 4/5: Saving generated code...")
        script_path = os.path.join(output_dir, "generated_art_code.py")
        save_file(script_path, generated_code)
        await ctx.info(f"Code saved to {script_path}")

        print(f"Code saved to {script_path}", file=sys.stderr, flush=True)
        print("--- Step 5/5: Executing ART code in container... ---", file=sys.stderr, flush=True)

        await ctx.info("Step 5/5: Executing ART code in container...")
        result = await run_art_in_docker(script_path)
        await ctx.info("ART execution finished.")
        
        if secondary_prompt:
            print("-------------------------------- \n --- Step 6/5: Found secondary objective. Generating prompt...  ---", file=sys.stderr, flush=True)
            secondary_generation_prompt = f"""
            given that the code generated already is:\n 
            [generated code]\n
            {generated_code}\n
            provide code that will perform the following task:
            [task]\n
            {secondary_prompt}\n
            make sure any files are saved in {output_dir}\n
            **Return only the raw, complete Python code.**
            """
            print("--- Step 7/9: Generating secondary code... ---", file=sys.stderr, flush=True)
            secondary_response = litellm.completion(
            model='anthropic/claude-sonnet',
            messages=[{"role": "user", "content": secondary_generation_prompt}],
            api_base=BASE_URL,
            api_key=OPENAI_API_KEY
        )
            secondary_generated_code = secondary_response.choices[0].message.content.strip().removeprefix("```python").removesuffix("```").strip()
            print("--- Step 8/9: Saving secondary code... ---", file=sys.stderr, flush=True)
            secondary_script_path = os.path.join(output_dir, "secondary_generated_art_code.py")
            save_file(secondary_script_path, secondary_generated_code)
            print("--- Step 9/9: Running secondary code... ---", file=sys.stderr, flush=True)
            await run_art_in_docker(secondary_script_path)

        
        return result

    except Exception as e:
        await ctx.error(f"An unexpected error occurred in the workflow: {e}")
        return f"Workflow failed with an error: {str(e)}"

# --- Server Execution ---
if __name__ == "__main__":

    
    mcp.run()