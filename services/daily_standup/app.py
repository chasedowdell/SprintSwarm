from shared_utils.configurations import configurations
from shared_utils.models import WorkItemUpdate
from fastapi import FastAPI
import logging
from shared_utils.logging_config import setup_logging
import httpx
import requests
import uvicorn
import json


app = FastAPI()
logger = logging.getLogger(__name__)

host = configurations.get("microservices", "sprint_planning", "hostname")
port = configurations.get("microservices", "sprint_planning", "port")
sprint_planning_address = f'http://{host}:{port}'

host = configurations.get("microservices", "developer", "hostname")
port = configurations.get("microservices", "developer", "port")
developer_address = f'http://{host}:{port}'

host = configurations.get("microservices", "tester", "hostname")
port = configurations.get("microservices", "tester", "port")
tester_address = f'http://{host}:{port}'

host = configurations.get("microservices", "code_base", "hostname")
port = configurations.get("microservices", "code_base", "port")
code_base_address = f'http://{host}:{port}'

async def get_sprint_backlog():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{sprint_planning_address}/get_sprint_backlog")
    return response.json()


@app.post("/daily_standup")
async def daily_standup():
    sprint_backlog = await get_sprint_backlog()

    while sprint_backlog:
        backlog_item = sprint_backlog.pop(0)
        logger.debug(backlog_item)
        response = requests.post(developer_address + '/work_on_item', json=backlog_item)
        response = requests.post(code_base_address + '/update_codebase')

        # async with httpx.AsyncClient(timeout=120.0) as client:
        #     response = await client.post(f"{developer_address}/work_on_item", json=backlog_item)
            # work_item_update: WorkItemUpdate = WorkItemUpdate(**response.json())

        # TODO Add the tester
        #if work_item_update.is_updated:
        #    async with httpx.AsyncClient() as client:
        #        await client.post(f"{tester_address}/test_and_report", json=work_item_update.dict())

    return {"success": True, "message": "Daily standups completed"}


if __name__ == '__main__':
    port = configurations.get('microservices', 'daily_standup', 'port')
    uvicorn.run(app, port=port)
