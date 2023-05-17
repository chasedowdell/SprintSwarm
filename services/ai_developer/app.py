from shared_utils.models import WorkItemUpdate, BacklogItem
from shared_utils.context import Context
from typing import List
from shared_utils.nlp import generate_completion
from shared_utils.configurations import Configurations
import logging
from shared_utils.logging_config import setup_logging
import requests
import json
import uvicorn
from fastapi import FastAPI

app = FastAPI()
context = Context()
configurations = Configurations()
logger = logging.getLogger(__name__)

# code base address
host = configurations.get('microservices', 'code_base', 'hostname')
port = configurations.get('microservices', 'code_base', 'port')
code_base_address = f"http://{host}:{port}"


async def get_detailed_tasks(item: BacklogItem, vision: dict, structure: dict, files_data: List[dict]) -> List[str]:
    files_structure = 'id,file path,file name,purpose\n'
    for i, file_data in enumerate(files_data):
        files_structure += '{},{},{},{}\n'.format(i,
                                                  file_data['path'],
                                                  file_data['name'],
                                                  file_data['purpose'])

    planning_prompt = f"""You are an exceptionally talented software developer working on an agile development team.
    The customer described the project as {vision['description']}.
    Your teams software architect setup the project structure using a {structure['architecture_paradigm']} 
    architecture paradigm.  The project structure is:
    {files_structure}
    Your current task is: {item.item['description']}
    Please generate a list of detailed code implementation actions this task without any numbering or additional explanation.
    One of your team members will use this list to identify the parts of the code that need to be updated or added."""

    logger.debug(planning_prompt)
    detailed_tasks = generate_completion(planning_prompt, max_tokens=2000)[0].split('\n')
    logger.debug(detailed_tasks)

    return detailed_tasks


async def get_candidate_code(detailed_task: str, item: BacklogItem, files_data: List[dict]) -> str:
    relevant_code_response = requests.get(code_base_address + '/search_code',
                                          params={"query": detailed_task, "top_k": 5})
    relevant_code_matches = relevant_code_response.json()['results']['matches']
    if relevant_code_matches:
        relevant_code = relevant_code_matches
        results = ['id,file_path,description']
        for match in relevant_code:
            fid = match['id']
            file_path = match['file_path']
            desc = match['metadata']['description']
            results.append(f'{fid},{file_path},{desc}')

        code_list = '\n'.join(results)

        code_context = f"""
        You are an working on an agile development team.  
        One of your team members is working on {item.item['description']}.  
        They have asked your advice for where to implement {detailed_task}.  
        You searched the code base and found the following relevant code:
        {code_list}\n
        Please respond to your colleague with either the id of the relevant code 
        or say 'add a new function' if the list is empty or none of the functions seem like the right fit.
        Please don't include any additional explanation."""
        candidate_code = generate_completion(code_context, max_tokens=2000)[0]
    else:
        candidate_code = 'add a new function'

    return candidate_code


async def handle_new_function(detailed_task: str, item: BacklogItem,
                              vision: dict, structure: dict) -> requests.Response:
    files_data = structure['files']
    files_structure = 'id,file path,file name,purpose\n'
    for i, file_data in enumerate(files_data):
        files_structure += '{},{},{},{}\n'.format(i,
                                                  file_data['path'],
                                                  file_data['name'],
                                                  file_data['purpose'])
    new_function_prompt = f"""
        You are an working on an agile development team.  
        One of your team members is working on {item.item['description']}.  
        They have asked your advice for where to implement {detailed_task}.
        The project structure is:
        {files_structure}\n
        Please respond to your colleague with either the id of the relevant file 
        or define a new file if none of the files seem like the right fit. 
        Please use the following format for your response if it is new:\n
        new:<file path>\n
        Please use the following format for your response an existing file:\n
        update:<file path>\n
        Please don't include any additional explanation."""

    candidate_file = generate_completion(new_function_prompt, max_tokens=2000)[0]

    if 'new:' in candidate_file.lower():
        target_path = candidate_file.split(':')[1].strip(' ')
        work_prompt = f"""
            You are an exceptionally talented software developer working on an agile development team.
            The customer described the project as {vision['description']}.\n
            Your are working on the '{item.item['description']}' backlog item.  
            In order to accomplish the '{detailed_task}' detailed task you are adding 
            the new file, {target_path}, to the repo.  Your teams software architect setup the 
            project structure using a {structure['architecture_paradigm']} architecture paradigm.
            Please respond with the content of the new file and nothing else."""
        completed_work = generate_completion(work_prompt, max_tokens=2049)[0]
        data = {
            "file_path": target_path,
            "content": completed_work
        }

        response = requests.post(code_base_address + '/create_file', json=data)

    else:
        target_path = candidate_file.split(':')[1].strip(' ')
        target_code = requests.get(code_base_address + '/get_code',
                                   params={"file_path": target_path}).json()['content']
        work_prompt = f"""You are an exceptionally talented software developer working on an agile development team.
            Your are working on the '{item.item['description']}' backlog item.  
            In order to accomplish the '{detailed_task}' detailed task you are adding 
            the new function, {target_path}, to the repo.  Your teams software architect setup the 
            project structure using a {structure['architecture_paradigm']} architecture paradigm.
            Please respond with the following code updated to accomplish the detailed task.
            Include all the original code in your response and don't provide any additional explanation.
            Code to update:\n{target_code}"""
        completed_work = generate_completion(work_prompt, max_tokens=2049)[0]
        data = {
            "file_path":target_path,
            "content": completed_work
        }

        response = requests.post(code_base_address + '/update_code', json=data)
    return response


async def handle_existing_function(detailed_task: str, candidate_code: str,
                                   item: BacklogItem, structure: dict) -> requests.Response:
    target_path = candidate_code.split(':')[0].strip(' ')
    target_function = candidate_code.split(':')[1].strip(' ')
    target_code = requests.get(code_base_address + '/get_code',
                               params={"file_path": target_path}).json()['content']

    work_prompt = f"""You are an exceptionally talented software developer working on an agile development team.
        Your are working on the '{item.item['description']}' backlog item.  
        In order to accomplish the '{detailed_task}' detailed task you are updating 
        the '{target_function}' function.  Your teams software architect setup the 
        project structure using a {structure['architecture_paradigm']} architecture paradigm.
        Please respond with the following code with {target_function} updated to accomplish the detailed task.
        Include all the original code in your response and don't provide any additional explanation.
        Code to update:\n{target_code}"""
    completed_work = generate_completion(work_prompt, max_tokens=2049)[0]
    data = {
        "file_path": target_path,
        "content": completed_work
    }

    response = requests.post(code_base_address + '/update_code', json=data)
    return response


@app.post("/work_on_item")
async def work_on_item(item: BacklogItem):
    vision = context.get_project_vision()
    structure = context.get_project_structure()
    files_data = structure['files']
    detailed_tasks = await get_detailed_tasks(item, vision, structure, files_data)

    for detailed_task in detailed_tasks:
        candidate_code = await get_candidate_code(detailed_task, item, files_data)

        if 'add a new function' in candidate_code.lower():
            response = await handle_new_function(detailed_task, item, vision, structure)
        else:
            response = await handle_existing_function(detailed_task, candidate_code, item, structure)


if __name__ == '__main__':
    port = configurations.get('microservices', 'developer', 'port')
    uvicorn.run(app, port=port)

#
# @app.post("/work_on_item")
# async def work_on_item(item: BacklogItem):
#     vision = context.get_project_vision()
#     structure = context.get_project_structure()
#     files_data = structure['files']
#
#     files_structure = 'id,file path,file name,purpose\n'
#     for i, file_data in enumerate(files_data):
#         files_structure += '{},{},{},{}\n'.format(i,
#                                                   file_data['file_path'],
#                                                   file_data['file_name'],
#                                                   file_data['purpose'])
#
#     planning_prompt = f"""
#     You are an exceptionally talented software developer working on an agile development team.
#     The customer described the project as {vision['description']}.
#     Your teams software architect setup the project structure using a {structure['architecture_paradigm']}
#     architecture paradigm.  The project structure is:
#     {files_structure}
#     Your current task is: {item.item['description']}
#     Please generate a list of detailed implementation actions this task without any numbering or additional explanation.
#     One of your team members will use this list to identify the parts of the code that need to be updated or added.
#     """
#
#     detailed_tasks = generate_completion(planning_prompt, max_tokens=2000)[0].split('\n')
#
#     for detailed_task in detailed_tasks:
#         relevant_code = requests.get(code_base_address + '/search_code',
#                                      params={"query": detailed_task, "top_k": 5}).json()
#
#         json_data = json.loads(relevant_code)
#
#         results = ['id,file_path,description']
#         for match in json_data['matches']:
#             fid = match['id']
#             file_path = match['file_path']
#             desc = match['metadata']['description']
#             results.append(f'{fid},{file_path},{desc}')
#
#         code_list = '\n'.join(results)
#
#         code_context = f"""
#         You are an working on an agile development team.
#         One of your team members is working on {item.item['description']}.
#         They have asked your advice for where to implement {detailed_task}.
#         You searched the code base and found the following relevant code:
#         {code_list}\n
#         Please respond to your colleague with either the id of the relevant code
#         or say 'add a new function' if the list is empty or none of the functions seem like the right fit.
#         Please don't include any additional explanation.
#         """
#
#         candidate_code = generate_completion(code_context, max_tokens=2000)[0]
#
#         if 'add a new function' in candidate_code.lower():
#             new_function_prompt = f"""
#                 You are an working on an agile development team.
#                 One of your team members is working on {item.item['description']}.
#                 They have asked your advice for where to implement {detailed_task}.
#                 The project structure is:
#                 {files_structure}\n
#                 Please respond to your colleague with either the id of the relevant file
#                 or define a new file if none of the files seem like the right fit.
#                 Please use the following format for your response if it is new:\n
#                 new:<file path>\n
#                 Please use the following format for your response an existing file:\n
#                 update:<file path>\n
#                 Please don't include any additional explanation.
#                 """
#
#             candidate_file = generate_completion(new_function_prompt, max_tokens=2000)[0]
#
#             if 'new:' in candidate_file.lower():
#                 target_path = candidate_file.split(':')[1].strip(' ')
#                 work_prompt = f"""
#                     You are an exceptionally talented software developer working on an agile development team.
#                     The customer described the project as {vision['description']}.\n
#                     Your are working on the '{item.item['description']}' backlog item.
#                     In order to accomplish the '{detailed_task}' detailed task you are adding
#                     the new file, {target_path}, to the repo.  Your teams software architect setup the
#                     project structure using a {structure['architecture_paradigm']} architecture paradigm.
#                     Please respond with the content of the new file and nothing else.
#                     """
#                 completed_work = generate_completion(work_prompt, max_tokens=2049)[0]
#                 data = {
#                     "file_path":target_path,
#                     "content": completed_work
#                 }
#
#                 response = requests.post(code_base_address + '/create_file', json=data)
#
#             else:
#                 target_path = files_data[int(candidate_file)]['file_path']
#                 target_code = requests.get(code_base_address + '/get_code',
#                                            params={"file_path": target_path}).json()['content']
#                 work_prompt = f"""
#                     You are an exceptionally talented software developer working on an agile development team.
#                     Your are working on the '{item.item['description']}' backlog item.
#                     In order to accomplish the '{detailed_task}' detailed task you are adding
#                     the new function, {target_path}, to the repo.  Your teams software architect setup the
#                     project structure using a {structure['architecture_paradigm']} architecture paradigm.
#                     Please respond with the following code updated to accomplish the detailed task.
#                     Include all the original code in your response and don't provide any additional explanation.
#                     Code to update:\n{target_code}
#                     """
#                 completed_work = generate_completion(work_prompt, max_tokens=2049)[0]
#                 data = {
#                     "file_path":target_path,
#                     "content": completed_work
#                 }
#
#                 response = requests.post(code_base_address + '/update_code', json=data)
#
#         else:
#             target_path = candidate_code.split(':')[0].strip(' ')
#             target_function = candidate_code.split(':')[1].strip(' ')
#             target_code = requests.get(code_base_address + '/get_code',
#                                        params={"file_path": target_path}).json()['content']
#
#             work_prompt = f"""
#                 You are an exceptionally talented software developer working on an agile development team.
#                 Your are working on the '{item.item['description']}' backlog item.
#                 In order to accomplish the '{detailed_task}' detailed task you are updating
#                 the '{target_function}' function.  Your teams software architect setup the
#                 project structure using a {structure['architecture_paradigm']} architecture paradigm.
#                 Please respond with the following code with {target_function} updated to accomplish the detailed task.
#                 Include all the original code in your response and don't provide any additional explanation.
#                 Code to update:\n{target_code}
#                 """
#             completed_work = generate_completion(work_prompt, max_tokens=2049)[0]
#             data = {
#                 "file_path": target_path,
#                 "content": completed_work
#             }
#
#             response = requests.post(code_base_address + '/update_code', json=data)
