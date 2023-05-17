from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from typing import List, Optional
from shared_utils.models import BacklogItem
from shared_utils.nlp import generate_embedding
from shared_utils.backlog import BacklogWithEmbedding
from shared_utils.configurations import configurations
import uvicorn
import heapq
import logging
from shared_utils.logging_config import setup_logging

backlog_namespace = configurations.get('pinecone', 'backlog_namespace')

app = FastAPI()
logger = logging.getLogger(__name__)
backlog = BacklogWithEmbedding()


@app.post("/add_item")
async def add_item(item: BacklogItem):
    # Validate the input data
    try:
        _ = item
    except ValidationError as e:
        return {"error": str(e)}

    logger.info(f'Add backlog item\n {item}')
    embedding = generate_embedding(item.item['description'])
    backlog.add_item(item, embedding, backlog_namespace)
    return {"success": True, "message": "new item added"}


@app.get("/get_top_items")
async def get_top_items(number_of_items: Optional[int] = 5):
    if number_of_items < 1:
        raise HTTPException(status_code=400, detail="Number of items should be greater than 0")

    top_items = heapq.nsmallest(number_of_items, backlog.get_backlog())
    logger.debug(top_items)
    return {"backlog_items": [item.__dict__ for item in top_items]}


if __name__ == '__main__':
    port = configurations.get('microservices', 'backlog', 'port')
    uvicorn.run(app, port=port)
