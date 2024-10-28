import os
import yaml
from github import Github, InputGitAuthor
from github.GithubException import GithubException
from datetime import datetime, timezone
import json
import openai
from typing_extensions import override
from openai import AssistantEventHandler
from dotenv import load_dotenv

load_dotenv()

# Read globals from env
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
REPO_NAME = os.getenv('REPO_NAME')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

g = Github(GITHUB_TOKEN)

openai.api_key = OPENAI_API_KEY

client = openai.OpenAI()

assistant = client.beta.assistants.create(
    name="Github assistant",
    instructions="You control github api calls to manage a project and codebase.",
    tools=[
        {"type": "code_interpreter"},
        {
            "type": "function",
            "function": {
                "name": "git_add_files",
                "description": "Add files to the Git staging area.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "repository_path": {
                        "type": "string",
                        "description": "Local path to the Git repository."
                    },
                    "file_paths": {
                        "type": "array",
                        "items": { "type": "string" },
                        "description": "List of file paths to add."
                    }
                    },
                    "required": ["repository_path", "file_paths"]
                }
                }

        },
        {
            "type": "function",
            "function": {
                "name": "git_commit",
                "description": "Commit changes to the repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "repository_path": { "type": "string", "description": "Local path to the Git repository." },
                    "message": { "type": "string", "description": "Commit message." }
                    },
                    "required": ["repository_path", "message"]
                }
            }

        },
        {
            "type": "function",
            "function": {
                "name": "git_create_branch",
                "description": "Create a new branch in the repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "repository_path": { "type": "string", "description": "Local path to the Git repository." },
                    "branch_name": { "type": "string", "description": "Name of the new branch." }
                    },
                    "required": ["repository_path", "branch_name"]
                }
            }

        },
        {
            "type": "function",
            "function": {
                "name": "git_checkout_branch",
                "description": "Switch to a specified branch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "repository_path": { "type": "string", "description": "Local path to the Git repository." },
                    "branch_name": { "type": "string", "description": "Name of the branch to checkout." }
                    },
                    "required": ["repository_path", "branch_name"]
                }
            }

        },
        {
            "type": "function",
            "function": {
                "name": "git_pull",
                "description": "Pull changes from the remote repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "repository_path": { "type": "string", "description": "Local path to the Git repository." },
                    "remote_name": { "type": "string", "description": "Name of the remote (default 'origin')." },
                    "branch_name": { "type": "string", "description": "Name of the branch to pull." }
                    },
                    "required": ["repository_path", "branch_name"]
                }
            }

        },
        {
            "type": "function",
            "function": {
                "name": "git_push",
                "description": "Push local commits to the remote repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "repository_path": { "type": "string", "description": "Local path to the Git repository." },
                    "remote_name": { "type": "string", "description": "Name of the remote (default 'origin')." },
                    "branch_name": { "type": "string", "description": "Name of the branch to push." }
                    },
                    "required": ["repository_path", "branch_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "git_clone_repository",
                "description": "Clone a remote repository to a local directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "repository_url": {
                        "type": "string",
                        "description": "URL of the remote repository to clone."
                    },
                    "local_path": {
                        "type": "string",
                        "description": "Local directory path where the repository will be cloned."
                    }
                    },
                    "required": ["repository_url", "local_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "git_create_local_repository",
                "description": "Initialize a new Git repository in a specified directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Path to the directory where the repository will be initialized."
                    }
                    },
                    "required": ["directory_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "github_create_repository",
                "description": "Create a new repository on GitHub.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "repository_name": {
                        "type": "string",
                        "description": "Name of the new GitHub repository."
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the repository."
                    },
                    "private": {
                        "type": "boolean",
                        "description": "Whether the repository should be private."
                    },
                    "auto_init": {
                        "type": "boolean",
                        "description": "Whether to initialize the repository with a README."
                    }
                    },
                    "required": ["repository_name"]
                }
            }
        }
    ],
    model="gpt-4o",
)

def git_add_files(params):
    from git import Repo
    repo = Repo(params['repository_path'])
    repo.index.add(params['file_paths'])
    repo.index.write()
    return {"status": "Files added to staging area."}

def git_commit(params):
    from git import Repo
    repo = Repo(params['repository_path'])
    repo.index.commit(params['message'])
    return {"status": f"Committed changes with message: '{params['message']}'"}


def git_create_branch(params):
    from git import Repo
    repo = Repo(params['repository_path'])
    new_branch = repo.create_head(params['branch_name'])
    return {"status": f"Branch '{params['branch_name']}' created."}

def git_checkout_branch(params):
    from git import Repo
    repo = Repo(params['repository_path'])
    repo.git.checkout(params['branch_name'])
    return {"status": f"Checked out to branch '{params['branch_name']}'."}

def git_pull(params):
    from git import Repo
    repo = Repo(params['repository_path'])
    remote = params.get('remote_name', 'origin')
    repo.git.pull(remote, params['branch_name'])
    return {"status": f"Pulled latest changes from '{remote}/{params['branch_name']}'."}

def git_push(params):
    from git import Repo
    repo = Repo(params['repository_path'])
    remote = params.get('remote_name', 'origin')
    repo.git.push(remote, params['branch_name'])
    return {"status": f"Pushed local changes to '{remote}/{params['branch_name']}'."}

def git_clone_repository(params):
    from git import Repo
    repository_url = params['repository_url']
    local_path = params['local_path']
    try:
        Repo.clone_from(repository_url, local_path)
        return {"status": f"Repository cloned to {local_path}."}
    except Exception as e:
        return {"error": str(e)}
    
def git_create_local_repository(params):
    from git import Repo
    directory_path = params['directory_path']
    try:
        Repo.init(directory_path)
        return {"status": f"Initialized empty Git repository in {directory_path}."}
    except Exception as e:
        return {"error": str(e)}
    
def github_create_repository(params):
    from github import Github
    # Assume 'g' is an authenticated Github instance
    repository_name = params['repository_name']
    description = params.get('description', '')
    private = params.get('private', False)
    auto_init = params.get('auto_init', False)
    try:
        user = g.get_user()
        repo = user.create_repo(
            name=repository_name,
            description=description,
            private=private,
            auto_init=auto_init
        )
        return {"status": f"Repository '{repository_name}' created on GitHub.", "repository_url": repo.html_url}
    except Exception as e:
        return {"error": str(e)}


thread = client.beta.threads.create()
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Repo: odoo17-code-vector-db, local dir: Fetch and pull the master on "
)

class EventHandler(AssistantEventHandler):
    @override
    def on_event(self, event):
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)

    def handle_requires_action(self, data, run_id):
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            params = json.loads(tool.function.arguments)
            if tool.function.name == "git_add_files":
                output = git_add_files(params)
                tool_outputs.append({"tool_call_id": tool.id, "output": output['status'] if output.get('status') else output['error']})

            elif tool.function.name == "git_commit":
                output = git_commit(params)
                tool_outputs.append({"tool_call_id": tool.id, "output": output['status'] if output.get('status') else output['error']})

            elif tool.function.name == "git_create_branch":
                output = git_create_branch(params)
                tool_outputs.append({"tool_call_id": tool.id, "output": output['status'] if output.get('status') else output['error']})
                
            elif tool.function.name == "git_checkout_branch":
                output = git_checkout_branch(params)
                tool_outputs.append({"tool_call_id": tool.id, "output": output['status'] if output.get('status') else output['error']})
                
            elif tool.function.name == "git_pull":
                output = git_pull(params)
                tool_outputs.append({"tool_call_id": tool.id, "output": output['status'] if output.get('status') else output['error']})
                
            elif tool.function.name == "git_push":
                output = git_push(params)
                tool_outputs.append({"tool_call_id": tool.id, "output": output['status'] if output.get('status') else output['error']})
                
            elif tool.function.name == "git_clone_repository":
                output = git_clone_repository(params)
                tool_outputs.append({"tool_call_id": tool.id, "output": output['status'] if output.get('status') else output['error']})
                
            elif tool.function.name == "git_create_local_repository":
                output = git_create_local_repository(params)
                tool_outputs.append({"tool_call_id": tool.id, "output": output['status'] if output.get('status') else output['error']})
                
            elif tool.function.name == "github_create_repository":
                output = github_create_repository(params)
                tool_outputs.append({"tool_call_id": tool.id, "output": output['status'] if output.get('status') else output['error']})

        self.submit_tool_outputs(tool_outputs, run_id)

    def submit_tool_outputs(self, tool_outputs, run_id):
        with client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=EventHandler(),
        ) as stream:
            for text in stream.text_deltas:
                print(text, end="", flush=True)
            print()

with client.beta.threads.runs.stream(
    thread_id=thread.id,
    assistant_id=assistant.id,
    event_handler=EventHandler()
) as stream:
    stream.until_done()
