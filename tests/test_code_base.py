import requests
from shared_utils.configurations import configurations
from shared_utils.models import ProjectFile
import json
import os
# from fastapi.testclient import TestClient
# from services.backlog.app import app

# client = TestClient(app)

host = configurations.get('microservices', 'code_base', 'hostname')
port = configurations.get('microservices', 'code_base', 'port')
code_base_address = f"http://{host}:{port}"
repo_path = configurations.get("git", "repo_path")


def test_create_file():
    new_file = ProjectFile(file_path=os.path.join(repo_path, './src'),  content="# this is the file")
    data = json.dumps(new_file.__dict__)
    response = requests.post(code_base_address + '/create_file', json=data)


test_create_file()
