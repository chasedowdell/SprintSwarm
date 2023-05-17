import os
import git
from fastapi import FastAPI
import logging
from shared_utils.logging_config import setup_logging
from shared_utils.models import CodeBaseFunction, ProjectFile
from shared_utils.PineconeDatabase import PineconeDatabase
from shared_utils.configurations import configurations
from shared_utils.nlp import generate_embedding, generate_completion
import uvicorn


app = FastAPI()
logger = logging.getLogger(__name__)

# Initialize the Git repository

repo_path = configurations.get("git", "repo_path")
# Check if the repository already exists
if os.path.exists(os.path.join(repo_path, '.git')):
    # The repository already exists, open it
    repo = git.Repo(repo_path)
else:
    # The repository doesn't exist, initialize it
    repo = git.Repo.init(repo_path)

# Initialize the Pinecone vector database
pinecone_api_key = configurations.get("pinecone", "api_key")
vector_db = PineconeDatabase(pinecone_api_key)


def get_function_name(code):
    """
    Extract function name from a line beginning with "def "
    """
    assert code.startswith("def ")
    return code[len("def "): code.index("(")]


def get_until_no_space(all_lines, i) -> str:
    """
    Get all lines until a line outside the function definition is found.
    """
    ret = [all_lines[i]]
    for j in range(i + 1, i + 10000):
        if j < len(all_lines):
            if len(all_lines[j]) == 0 or all_lines[j][0] in [" ", "\t", ")"]:
                ret.append(all_lines[j])
            else:
                break
    return "\n".join(ret)


def index_codebase():
    # Iterate through the repository files and index their embeddings
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    code = f.read().replace("\r", "\n")
                    all_lines = code.split("\n")
                    for i, l in enumerate(all_lines):
                        if l.startswith("def "):
                            function_code = get_until_no_space(all_lines, i)
                            function_name = get_function_name(function_code)
                            logger.debug(f'indexing {function_name}')

                            summary_prompt = f"""
                            Please generate a brief 1 to 2 sentence description of the following function 
                            ({function_name}) without any additional explanation:\n
                            {function_code} 
                            """
                            code_description = generate_completion(summary_prompt)[0]

                            # Generate the code embedding
                            embedding = generate_embedding(code_description)

                            code_base_function = CodeBaseFunction(
                                id=file_path + ':' + function_name,
                                function_name=function_name,
                                file_path=file_path,
                                code=function_code,
                                embedding=embedding,
                                description=code_description
                            )

                            # Add the code embedding to the vector database
                            vector_db.add_code(code_base_function)


@app.on_event("startup")
async def on_startup():
    # Index the codebase on startup
    logger.info(f'Indexing {repo_path}')
    index_codebase()


@app.get("/search_code")
async def search_code(query: str, top_k: int = 5):
    # Generate the query embedding
    query_embedding = generate_embedding(query)

    # Search the vector database
    logging.debug(f'Querying codebase: {query}')
    try:
        results = vector_db.search(query_embedding, top_k, namespace='codebase')
    except Exception as e:
        logging.error(f'Error while querying vector database: {e}')
        raise e
    logging.debug(results)

    results_json = {
        'matches': [str(match) for match in results['matches']],
        'namespace': results['namespace'],
    }

    # Return the search results
    return {"results": results_json}


@app.post("/update_codebase")
async def update_codebase():
    # Re-index the codebase
    index_codebase()
    return {"success": True, "message": "Codebase re-indexed"}

# Add more Git-related functions as needed


@app.post("/update_code")
async def update_code(new_file: ProjectFile):
    file_path = os.path.normpath(new_file.file_path)
    new_content = os.path.normpath(new_file.content)

    with open(os.path.join(repo_path, file_path), "w") as f:
        f.write(new_content)
    repo.git.add(file_path)


@app.post("/commit_changes")
async def commit_changes(commit_message: str):
    repo.git.commit("-m", commit_message)


@app.post("/create_file")
async def create_file(new_file: ProjectFile):

    file_path = os.path.normpath(new_file.file_path)

    # Join the file path with the repo base
    file_path = os.path.join(repo_path, file_path.lstrip("./"))

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        f.write(new_file.content)
    repo.git.add(all=True)
    repo.git.add(os.path.dirname(file_path))
    repo.git.add(file_path)
    repo.git.commit("-m", f"Create new file: {file_path}")


@app.post("/create_branch")
async def create_branch(branch_name: str):
    repo.git.checkout("-b", branch_name)


@app.post("/fetch_and_pull")
async def fetch_and_pull(remote_name: str = "origin", branch_name: str = "main"):
    repo.git.fetch(remote_name)
    repo.git.pull(remote_name, branch_name)


@app.get("/get_commit_history")
async def get_commit_history():
    commit_history = []
    for commit in repo.iter_commits():
        commit_history.append({
            "commit_id": commit.hexsha,
            "author": commit.author.name,
            "date": commit.authored_datetime,
            "message": commit.message
        })
    return {"commit_history": commit_history}


@app.get("/get_code")
async def get_code(file_path: str):
    try:
        with open(os.path.join(repo_path, file_path), "r") as f:
            content = f.read()
        return {"success": True, "content": content}
    except FileNotFoundError:
        return {"success": False, "message": f"File not found: {file_path}", "content": ""}
    except Exception as e:
        return {"success": False, "message": f"Error retrieving file content: {str(e)}", "content": ""}


if __name__ == '__main__':
    port = configurations.get('microservices', 'code_base', 'port')
    uvicorn.run(app, port=port)
