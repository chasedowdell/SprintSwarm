from fastapi import FastAPI
import logging
from shared_utils.logging_config import setup_logging
from shared_utils.models import ProductVision, ProjectStructure
from shared_utils.configurations import configurations
from shared_utils.nlp import generate_completion, extract_json_string
from shared_utils.context import Context
import requests
import uvicorn
import json
import os

app = FastAPI()
context = Context()
logger = logging.getLogger(__name__)

backlog_item_remaining = configurations.get('program_management', 'items_per_sprint')

# Define the agent microservices' addresses

host = configurations.get('microservices', 'sprint_planning', 'hostname')
port = configurations.get('microservices', 'sprint_planning', 'port')
ai_sprint_planning_address = f"http://{host}:{port}"

host = configurations.get('microservices', 'product_owner', 'hostname')
port = configurations.get('microservices', 'product_owner', 'port')
ai_product_owner_address = f"http://{host}:{port}"

host = configurations.get('microservices', 'daily_standup', 'hostname')
port = configurations.get('microservices', 'daily_standup', 'port')
daily_standup_address = f"http://{host}:{port}"

host = configurations.get('microservices', 'sprint_review', 'hostname')
port = configurations.get('microservices', 'sprint_review', 'port')
sprint_review_address = f"http://{host}:{port}"

host = configurations.get('microservices', 'code_base', 'hostname')
port = configurations.get('microservices', 'code_base', 'port')
code_base_address = f"http://{host}:{port}"

# Define a list of agent microservices to call in sequence
agents = [
    (ai_sprint_planning_address, "/sprint_planning"),
    (daily_standup_address, "/daily_standup"),
    # (sprint_review_address, "/sprint_review")
]


async def generate_project_structure(vision: ProductVision) -> ProjectStructure:
    # Call the AI agent to analyze the project description and generate an appropriate project structure
    # Replace the following example with the actual implementation
    # Format a prompt for the NLP module
    prompt = f"""
    You are the software architecture expert on an Agile development team.
    The project description is: 
    {vision.description} 
    The key features are:
    {vision.key_features}
    And the constraints are:
    {vision.constraints}
    Your task is to create an initial project structure that supports this vision.
    Please briefly summarize the architecture paradigm, project philosophy, 
    and initialize the project structure using only the following JSON structure and 
    no additional commentary or explanation:
    {{
        "architecture_paradigm": <software architecture approach being used>
        "project_philosophy": "<philosophy summary>",
        "files": [
            {{
                "path": "<relative file path (e.g. ./src)>",
                "name": "<file name (e.g. example.py)>",
                "purpose": "<description of what the file will do>"
            }}
            # More files ...
        ]
    }}"""
    project_structure_response = generate_completion(prompt, max_tokens=2049)[0]

    project_structure_string = extract_json_string(project_structure_response)

    logger.debug(project_structure_string)

    context.add_project_vision(vision)
    context.add_project_structure(project_structure_string)
    project_structure_mapping = json.loads(project_structure_string)

    return ProjectStructure(**project_structure_mapping)


@app.post("/create_project")
async def create_project(vision: ProductVision):
    project_structure = await generate_project_structure(vision)

    # Create the directories and files according to the generated project structure
    for file_info in project_structure.files:
        path = file_info["path"]
        name = file_info["name"]

        # Create the directory if it doesn't exist
        # os.makedirs(path, exist_ok=True)

        file_path = os.path.join(path, name)

        data = {
            "file_path": file_path,
            "content": "# " + file_info["purpose"] + "\n"
        }

        logger.debug('Creating file:')
        logger.debug(data)

        response = requests.post(code_base_address + '/create_file', json=data)

    return {"success": True, "message": "Project structure created", "project_structure": project_structure}


@app.post("/start_sprint")
async def start_sprint(vision: ProductVision):
    # TODO figure out where the create project belongs
    await create_project(vision)
    for address, endpoint in agents:
        response = requests.post(f"{address}{endpoint}")
        if response.status_code != 200:
            return {
                "success": False,
                "message": f"Error occurred while executing {endpoint} at {address}"
            }
    return {"success": True, "message": "Sprint completed"}


if __name__ == '__main__':
    port = configurations.get('microservices', 'program_management', 'port')
    uvicorn.run(app, port=port)
