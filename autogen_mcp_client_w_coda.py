import asyncio
import os
import autogen
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench, mcp_server_tools, SseServerParams
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core.models import ModelInfo





async def main():
    """
    This function sets up and runs an AutoGen agent that acts as a client
    to our MCP server.
    """
    # 1. Define the parameters to launch the MCP server.
    # The AssistantAgent will use this to start the server as a subprocess.
    base_url = os.getenv("OPENAI_API_BASEURL")
    api_key = os.getenv("CBORG_API_KEY")
    print(api_key)

    model_client = OpenAIChatCompletionClient(
        model='anthropic/claude-sonnet', # You can use any model name your endpoint supports
        base_url="https://api.cborg.lbl.gov",
        api_key=api_key,
        model_info=ModelInfo(vision=False,
                             function_calling= True,
                             json_output=False,
                             family='unknown',
                             structured_output= True)
    )
    
    
    
    server_env = {
        "OPENAI_API_KEY": api_key,
        "LITELLM_BASE_URL": base_url, # Pass the same base_url to the server
        "LITELLM_MODEL_NAME": 'anthropic/claude-sonnet', # Tell server to use openai format
        "HOST_PROJECT_PATH": os.getenv("HOST_PROJECT_PATH"),
        "ART_SRC_PATH": os.getenv("ART_SRC_PATH"),
    }
    
    
    art_server_params = StdioServerParams(
        command="python",
        args=["-u", "mcp_art_server.py"],
        read_timeout_seconds=3600,
        env=server_env
    )

    coda_server_params = StdioServerParams(
        command="npx",
        args=["-y", "coda_mcp/"],
        read_timeout_seconds=3600,
        env=server_env
    )

    print(f'the art_server contains the following tools {mcp_server_tools(art_server_params)}')

    # art_workbench = McpWorkbench(server_params=art_server_params)
    # scholar_workbench = McpWorkbench(server_params=scholar_server_params)
    # 2. Use 'async with' to create and manage the McpWorkbench.
    # This workbench connects to the MCP server and makes its tools available to the agent.
    async with McpWorkbench(server_params=art_server_params) as art_workbench:


        orchestrator_agent = AssistantAgent(
            name="ART_Orchestrator",
            model_client=model_client,
            workbench=art_workbench,
            system_message=("You are machine learning manager. You are able to split complex tasks in smaller pieces when needed based on the tools you have access to. Your primary goal is to orchestrate ART analysis using the 'run_art_analysis' tool.  You can also ask questions and prepare templates are required in order to enable the ART analysis.\n"),
            description="An agent that can run complex ART analysis workflows by calling the ART MCP server.",
            max_tool_iterations= 40
        )
        task = f"""
        preprocessing: Read the `Isoprenol_media_optimization` directory structure and the contents of `results_DBTL1.csv`, `results_DBTL2.csv`, `media_bounds.csv` and `stock_concentrations.csv`,  before doing anything else.

        Before running `run_art_analysis` use the `ask_question` tool to get instructions on how to perfectly perform the task.

        Here are your tasks:

        Target directory will be `data/DBTL3`
        [Task 1]
        [Primary]
        use `run_art_analysis` to train an ART model based on the data from DBTL1 and DBTL1. The previously generated resulst are in the `DBTL1/results_DBTL1.csv` and `DBTL2/results_DBTL2.csv` files. These contain samples where the Line Name contains <condition>-R1, <condition>-R2, <condition>-R3, where R1, R2, R3 denote replicates. Before training the model clean up the data to contain only conditions for which the coefficient of variation is below 20%. Ignore controls (WD4_D6) from the CV abalysis. Remove the third replicate of each control (WD4_D6-R3) before training the model.
        
        Sum the concentrations of the phosphate species (Na2HPO4 and KH2PO4) to one column and name that phosphates[mM]

        The model you'll build must use the following parameters:
        num_tpot_models = 2, max_mcmc_cores = 10, cross_val = True, cross_val_partitions = 5.
        
        Use this model generate 
        - 7 exploration recommendations with rel_rec_distance = 10  
        
        - 7 exploitation recommendations with rel_rec_distance = 1.

        - after that, loosen the bounds by 20% in each direction for all variables and generate 7 exploration recommendations


        [Secondary]
        USE THE RECOMMENDATIONS GENERATED FROM THE PREVIOUS TASK.
        a) randomly mix the recommendations
        b) split them in 3 sets of 7 and put them in one 24-well plate per set (ABCD, 123456) in triplicates
        c) each row must contain the same condition in 3 consecutive wells ([A1, A2, A3], [C4, C5, C6])
        d) each plate should contain a control in wells D4, D5 and D6, which should be the same as the controls we used in the same wells in DBTL1 and DBTL2

        [TASK 2]
        [Primary]
        Generate a 14 of recommendation using the `run_art_analysis` tool using the latin hypercube sampling function, by setting `init_cycle = True`. make sure you use a fresh seed when generating these recommendations. 

        [Secondary]
        USE THE RECOMMENDATIONS GENERATED FROM THE PREVIOUS TASK.
        a) split them in 3 sets of 7 and put them in one 24-well plate per set (ABCD, 123456) in triplicates. These should be plates 4, 5, and 6
        b) each row must contain the same condition in 3 consecutive wells ([A1, A2, A3], [C4, C5, C6])
        c) each plate should contain a control in wells D4, D5 and D6, which should be the same as the controls we used in the same wells in DBTL1 and DBTL2




        [TASK 3]
        Load the files plate1.csv, plate2.csv, ..., plate6.csv and generate robotic instructions for assembling the plates, using the data/stock_concentrations.csv concentrations. 
        
        """
        
        await Console(orchestrator_agent.run_stream(task=task))

if __name__ == "__main__":
    # Ensure environment variables are set before running
    required_vars = ["OPENAI_API_KEY", "HOST_PROJECT_PATH", "ART_SRC_PATH"]
    if any(var not in os.environ for var in required_vars):
        print("Error: Please set the required environment variables: " + ", ".join(required_vars))
    else:
        asyncio.run(main())