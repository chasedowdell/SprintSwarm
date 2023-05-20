from fastapi import FastAPI
from typing import List
import logging
from shared_utils.logging_config import setup_logging
from shared_utils.models import BacklogItem
from shared_utils.nlp import generate_chat_completion, generate_embedding
from shared_utils.configurations import configurations
from shared_utils.backlog import BacklogWithEmbedding
import json
import uvicorn
import requests

app = FastAPI()
logger = logging.getLogger(__name__)

number_of_items = configurations.get('program_management', 'items_per_sprint')
sprint_backlog_namespace = configurations.get('pinecone', 'sprint_backlog_namespace')

host = configurations.get('microservices', 'backlog', 'hostname')
port = configurations.get('microservices', 'backlog', 'port')
product_backlog_address = f"http://{host}:{port}"


sprint_backlog = BacklogWithEmbedding()


@app.post("/sprint_planning")
async def sprint_planning():
    # Retrieve the top N backlog items from the product backlog service
    response = requests.get(product_backlog_address + f"/get_top_items?number_of_items={number_of_items}")
    logging.debug(response)
    backlog_items = json.loads(response.text)["backlog_items"]
    logger.debug('Backlog items')
    logger.debug(backlog_items)

    # Decompose backlog items using the NLP completion function
    for item in backlog_items:
        prompt = f"""You are the team member responsible for sprint planning. 
        You are an expert at considering the perspectives of your AI development team. 
        Your current task is to decompose a backlog item for a sprint. The backlog item is:
        '{item['item']['description']}'
        Please provide a list of smaller tasks to complete this backlog item in priority order.
        The tasks should be as fine-grained as possible and only include code implementation tasks.
        The AI developers these will be assigned to can only create, update, and remove python code.
        Respond with a new line delimited list of tasks and do not include any additional explanation."""

        messages = [
            {"role": "system", "content": "You are an AI member of an agile software development team."},
            {"role": "user", "content": prompt}
        ]

        completions = generate_chat_completion(messages, max_tokens=2000)
        tasks = completions.split('\n')

        # Store the decomposed tasks in the sprint backlog
        for i, task in enumerate(tasks):
            sprint_task = BacklogItem(priority=i, item={'description': task})
            embedding = generate_embedding(task)
            sprint_backlog.add_item(sprint_task, embedding, sprint_backlog_namespace)

    return {"success": True, "message": f"{number_of_items} backlog items decomposed and added to the sprint backlog"}


@app.get("/get_sprint_backlog")
async def get_sprint_backlog():
    return [item.__dict__ for item in sprint_backlog.get_backlog()]

if __name__ == '__main__':
    port = configurations.get('microservices', 'sprint_planning', 'port')
    uvicorn.run(app, port=port)
