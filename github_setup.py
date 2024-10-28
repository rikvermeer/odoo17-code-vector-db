import os
import yaml
from github import Github, InputGitAuthor
from github.GithubException import GithubException
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv()

# Read globals from env
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
REPO_NAME = os.getenv('REPO_NAME')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

REPO_DESCRIPTION = 'A project to store the Odoo 17 codebase in a vector database with comprehensive metadata.'
REPO_PRIVATE = False  # Set to True if you want a private repository

# Project details
PROJECT_NAME = 'Odoo17 Vector Database Project'
PROJECT_BODY = 'Project board to track tasks and milestones.'

# GitHub API endpoints
GITHUB_GRAPHQL_API_URL = 'https://api.github.com/graphql'
GITHUB_REST_API_URL = 'https://api.github.com'

# Headers for requests
HEADERS = {
    'Authorization': f'Bearer {GITHUB_TOKEN}',
    'Content-Type': 'application/json',
}

def graphql_query(query, variables=None):
    """Send a GraphQL query to the GitHub API."""
    response = requests.post(
        GITHUB_GRAPHQL_API_URL,
        json={'query': query, 'variables': variables},
        headers=HEADERS
    )
    if response.status_code != 200:
        raise Exception(f"Query failed to run by returning code of {response.status_code}. {response.text}")
    return response.json()

def get_user_id():
    """Get the authenticated user's ID."""
    query = '''
    query {
      viewer {
        id
      }
    }
    '''
    result = graphql_query(query)
    return result['data']['viewer']['id']

def get_repository_id(owner, name):
    """Get the repository ID by owner and name."""
    query = '''
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
      }
    }
    '''
    variables = {'owner': owner, 'name': name}
    result = graphql_query(query, variables)
    return result['data']['repository']['id'] if result['data']['repository'] else None

def create_repository(name, description, is_private):
    """Create a new repository."""
    query = '''
    mutation($name: String!, $description: String!, $visibility: RepositoryVisibility!) {
      createRepository(input: {
        name: $name,
        description: $description,
        visibility: $visibility,
        hasIssuesEnabled: true,
      }) {
        repository {
          id
          name
        }
      }
    }
    '''
    visibility = 'PRIVATE' if is_private else 'PUBLIC'
    variables = {'name': name, 'description': description, 'visibility': visibility}
    result = graphql_query(query, variables)
    print('Result:', result)
    return result['data']['createRepository']['repository']['id']

def update_readme(owner, repo, content):
    """Update the README.md file."""
    # Get the SHA of the existing README.md if it exists
    url = f"{GITHUB_REST_API_URL}/repos/{owner}/{repo}/contents/README.md"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        sha = response.json()['sha']
        message = 'Update README.md with project description and timeline'
    else:
        sha = None
        message = 'Create README.md with project description and timeline'

    # Base64 encode the content
    import base64
    content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    data = {
        'message': message,
        'content': content_encoded,
    }
    if sha:
        data['sha'] = sha

    response = requests.put(url, json=data, headers=HEADERS)
    if response.status_code not in [200, 201]:
        raise Exception(f"Failed to update README.md: {response.text}")

def get_label_id(owner, repo, name):
    """Get the ID of a label."""
    query = '''
    query($owner: String!, $repo: String!, $name: String!) {
      repository(owner: $owner, name: $repo) {
        label(name: $name) {
          id
        }
      }
    }
    '''
    variables = {'owner': owner, 'repo': repo, 'name': name}
    result = graphql_query(query, variables)
    label = result['data']['repository']['label']
    return label['id'] if label else None

def create_label(owner, repo, name, color):
    """Create a label."""
    url = f"{GITHUB_REST_API_URL}/repos/{owner}/{repo}/labels"
    data = {'name': name, 'color': color}
    response = requests.post(url, json=data, headers=HEADERS)
    if response.status_code not in [200, 201]:
        if response.status_code == 422 and 'already_exists' in response.text:
            print(f'Label "{name}" already exists. Skipping.')
        else:
            raise Exception(f"Failed to create label {name}: {response.text}")

def get_milestone_number(owner, repo, title):
    """Get the number of a milestone."""
    url = f"{GITHUB_REST_API_URL}/repos/{owner}/{repo}/milestones"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        raise Exception(f"Failed to get milestones: {response.text}")
    milestones = response.json()
    for milestone in milestones:
        if milestone['title'] == title:
            return milestone['number']
    return None

def create_milestone(owner, repo, title, description, due_on):
    """Create a milestone."""
    url = f"{GITHUB_REST_API_URL}/repos/{owner}/{repo}/milestones"
    data = {'title': title, 'description': description}
    if due_on:
        data['due_on'] = due_on.isoformat()
    response = requests.post(url, json=data, headers=HEADERS)
    if response.status_code not in [200, 201]:
        raise Exception(f"Failed to create milestone {title}: {response.text}")
    return response.json()['number']

def create_issue(owner, repo, title, body, labels, milestone_number):
    """Create an issue."""
    url = f"{GITHUB_REST_API_URL}/repos/{owner}/{repo}/issues"
    data = {
        'title': title,
        'body': body,
        'labels': labels,
        'milestone': milestone_number
    }
    response = requests.post(url, json=data, headers=HEADERS)
    if response.status_code not in [200, 201]:
        if response.status_code == 422 and 'already_exists' in response.text:
            print(f'Issue "{title}" already exists. Skipping.')
        else:
            raise Exception(f"Failed to create issue {title}: {response.text}")
    else:
        return response.json()['number']

def get_project_id(owner_id, project_name):
    """Get the ID of a project."""
    query = '''
    query($login: String!, $projectName: String!) {
      user(login: $login) {
        projectsV2(first: 100, query: $projectName) {
          nodes {
            id
            title
          }
        }
      }
    }
    '''
    variables = {'login': GITHUB_USERNAME, 'projectName': project_name}
    result = graphql_query(query, variables)
    print(f'Result: {result}')
    projects = result['data']['user']['projectsV2']['nodes']
    for project in projects:
        if project['title'] == project_name:
            return project['id']
    return None

def create_project(owner_id, project_name):
    """Create a new GitHub Project (beta)."""
    query = '''
    mutation($ownerId: ID!, $title: String!) {
      createProjectV2(input: {ownerId: $ownerId, title: $title}) {
        projectV2 {
          id
        }
      }
    }
    '''
    variables = {'ownerId': owner_id, 'title': project_name}
    result = graphql_query(query, variables)
    return result['data']['createProjectV2']['projectV2']['id']

def add_issue_to_project(project_id, issue_id):
    """Add an issue to a project."""
    query = '''
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
        item {
          id
        }
      }
    }
    '''
    variables = {'projectId': project_id, 'contentId': issue_id}
    result = graphql_query(query, variables)
    return result['data']['addProjectV2ItemById']['item']['id']

def main():
    try:
        # Load milestones and tasks from YAML file
        with open('milestones.yaml', 'r') as file:
            data = yaml.safe_load(file)
        MILESTONES = data['MILESTONES']

        # Extract all labels used in tasks
        labels_in_tasks = set()
        for milestone_data in MILESTONES.values():
            for task in milestone_data['tasks']:
                labels_in_tasks.update(task.get('labels', []))

        # Get the authenticated user ID
        user_id = get_user_id()
        print(f'Authenticated user ID: {user_id}')

        # Check if repository exists
        repo_id = get_repository_id(GITHUB_USERNAME, REPO_NAME)
        if repo_id:
            print(f'Repository {REPO_NAME} already exists.')
        else:
            print(f'Creating repository {REPO_NAME}...')
            repo_id = create_repository(REPO_NAME, REPO_DESCRIPTION, REPO_PRIVATE)
            print('Repository created successfully.')

        # Update README.md
        print('Updating README.md...')
        readme_content = '''# Odoo17 Code Vector Database

## Project Description

The **Odoo17 Code Vector Database** project aims to store the Odoo 17 codebase in a vector database enriched with comprehensive structural information and metadata. This initiative will enhance searchability, contextual understanding, and analytical capabilities, enabling efficient retrieval and analysis of code segments.

**Objectives:**

- **Semantic Search:** Enable code searches based on meaning and context rather than just keywords.
- **Impact Analysis:** Understand the implications of code changes across the entire codebase.
- **Refactoring Support:** Identify duplicate code or patterns that require optimization.
- **Knowledge Sharing:** Facilitate onboarding and knowledge transfer within development teams.
- **Automated Documentation:** Generate documentation from enriched code metadata.

**Key Features:**

- **Comprehensive Metadata Storage:** Store detailed structural information such as classes, functions, variables, and dependencies.
- **Vector Embeddings:** Use state-of-the-art models to create vector representations of code for similarity searches.
- **Efficient Retrieval Mechanisms:** Implement indexing and optimization strategies for fast and relevant search results.
- **API Development:** Provide APIs for seamless integration with other tools and platforms.
- **User Interface:** Optional development of a user-friendly interface for interacting with the vector database.

## Project Timeline and Tasks

[Refer to the project milestones and tasks in the GitHub Project Board.]

## Team Roles and Responsibilities

- **Project Lead:** Oversee project progression and coordinate between teams.
- **Developers:** Implement code parsing, embeddings, and API development.
- **Data Engineers:** Handle data extraction, storage, and database management.
- **Testers/QA:** Perform testing and ensure quality standards.
- **Technical Writers:** Prepare and maintain project documentation.

## Tools and Technologies

- **Programming Language:** Python
- **Parsing Libraries:** `ast`, `PyParsing`, or similar libraries
- **Vectorization Models:** CodeBERT, OpenAI Embeddings
- **Vector Database:** Elasticsearch, Pinecone, or Weaviate
- **API Framework:** FastAPI or Flask
- **Version Control:** Git and GitHub
- **Project Management:** GitHub Projects and Issues

'''
        update_readme(GITHUB_USERNAME, REPO_NAME, readme_content)
        print('README.md updated.')

        # Create labels
        print('Creating labels...')
        for label_name in labels_in_tasks:
            create_label(GITHUB_USERNAME, REPO_NAME, label_name, 'c5def5')
        print('Labels processing completed.')

        # Create milestones and issues
        print('Creating milestones and issues...')
        for milestone_title, milestone_data in MILESTONES.items():
            # Check if milestone exists
            milestone_number = get_milestone_number(GITHUB_USERNAME, REPO_NAME, milestone_title)
            if milestone_number:
                print(f'Milestone "{milestone_title}" already exists. Skipping creation.')
            else:
                # Convert 'due_on' to datetime object
                due_on_str = milestone_data.get('due_on', None)
                if due_on_str:
                    due_on = datetime.strptime(due_on_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                else:
                    due_on = None
                # Create milestone
                milestone_number = create_milestone(
                    GITHUB_USERNAME, REPO_NAME,
                    milestone_title,
                    milestone_data.get('description', ''),
                    due_on
                )
                print(f'Created milestone: {milestone_title}')

            # Create issues for the milestone
            for task in milestone_data['tasks']:
                issue_title = task['title']
                # Check if issue exists
                # For simplicity, we assume issues are unique by title
                # You may need to implement additional checks
                try:
                    issue_number = create_issue(
                        GITHUB_USERNAME, REPO_NAME,
                        issue_title,
                        task.get('body', ''),
                        task.get('labels', []),
                        milestone_number
                    )
                    print(f'  Created issue: {issue_title}')
                except Exception as e:
                    print(e)
        print('Milestones and issues processing completed.')

        # Create project (GitHub Projects Beta)
        print('Creating or fetching project...')
        project_id = get_project_id(user_id, PROJECT_NAME)
        if project_id:
            print(f'Project "{PROJECT_NAME}" already exists.')
        else:
            print(f'Creating project "{PROJECT_NAME}"')
            project_id = create_project(user_id, PROJECT_NAME)
            print(f'Project "{PROJECT_NAME}" created with ID: {project_id}')

        # Add issues to the project
        print('Adding issues to project...')
        # Get all open issues
        url = f"{GITHUB_REST_API_URL}/repos/{GITHUB_USERNAME}/{REPO_NAME}/issues"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            raise Exception(f"Failed to get issues: {response.text}")
        issues = response.json()
        for issue in issues:
            issue_node_id = issue['node_id']
            add_issue_to_project(project_id, issue_node_id)
            print(f'  Added issue "{issue["title"]}" to project.')
        print('Issues added to project.')

        print('Setup completed successfully.')

    except Exception as ex:
        print(f'An error occurred: {ex}')

if __name__ == '__main__':
    main()

