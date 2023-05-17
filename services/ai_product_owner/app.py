from fastapi import FastAPI
from typing import List
import logging
import requests
import json
from shared_utils.logging_config import setup_logging
from shared_utils.configurations import configurations
from shared_utils.nlp import generate_completion, generate_embedding, sanitize_ai_response
from shared_utils.models import ProductVision, BacklogItem
import uvicorn

app = FastAPI()
logger = logging.getLogger(__name__)

# backlog routes
host = configurations.get('microservices', 'backlog', 'hostname')
port = configurations.get('microservices', 'backlog', 'port')
backlog_address = f"http://{host}:{port}"

host = configurations.get('microservices', 'program_management', 'hostname')
port = configurations.get('microservices', 'program_management', 'port')
program_management_address = f"http://{host}:{port}"


@app.post("/receive_product_vision")
async def receive_product_vision(vision: ProductVision):
    # Process the product vision input
    goals = ', '.join(vision.goals)
    key_features = ', '.join(vision.key_features)
    constraints = ', '.join(vision.constraints)

    # Format a prompt for the NLP module
    prompt = f"""
    You are an exceptionally talented agile product owner tasked with creating the initial product backlog for a team of'
    AI developers. The customer has given a project with the title '{vision.title}' 
    and the description '{vision.description}', 
    the main goals are {goals}, 
    the key features are {key_features}, 
    and the constraints are {constraints}. 
    Please generate a list of backlog items to achieve these goals while considering the constraints.
    The backlog should only include items that an LLM could perform without supervision.
    Please provide the backlog as a newline delimited list in priority order without numbering or bullets.  
    Do not include any additional explanation."""

    # Send the prompt to the get_completions function and get the response
    completions = generate_completion(prompt, max_tokens=1000)[0].split('\n')
    logger.debug('Initial backlog items')
    logger.debug('\n'.join(completions))

    # Invoke the backlog add item API to add each of the new items
    for i, item in enumerate(completions):
        new_item = BacklogItem(priority=i, item={'description': item})
        data = json.dumps(new_item.__dict__)
        response = requests.post(backlog_address + '/add_item',
                                 data=data,
                                 headers={'Content-Type': 'application/json'})
    logger.debug('Starting sprint')
    response = requests.post(program_management_address + '/start_sprint',
                             data=json.dumps(vision.__dict__),
                             headers={'Content-Type': 'application/json'})
    # TODO update response with sprint review summary and return to the customer communication endpoint
    return {"success": True, "message": "Backlog items created"}


@app.post("/prioritize_backlog")
async def prioritize_backlog():
    return {"success": True, "message": "Backlog items prioritized"}

if __name__ == '__main__':
    port = configurations.get('microservices', 'product_owner', 'port')
    uvicorn.run(app, port=port)
