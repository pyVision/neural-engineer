"""
DeepWiki Clone - A repository exploration tool built with FastAPI
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
import json
import httpx

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import sys
import logging



from wiki_ai.data_controller import get_data_controller

# Load environment variables
load_dotenv()


# Add parent directory to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Initialize FastAPI application
app = FastAPI(
    title="DeepWiki Clone",
    description="A repository exploration tool built with FastAPI",
    version="1.0.0"
)

# Configure templating with Jinja2
templates = Jinja2Templates(directory="templates")

# Configure static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# GitHub API token for higher rate limits (optional)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Popular repositories to display by default
DEFAULT_REPOS = [
    {"owner": "microsoft", "name": "vscode", "description": "Visual Studio Code"},
    {"owner": "mark3labs", "name": "mcp-go", 
     "description": "A Go implementation of the Model Context Protocol (MCP), enabling seamless integration between LLMs"},
    {"owner": "antiwork", "name": "gumroad", "description": ""},
    {"owner": "langchain-ai", "name": "local-deep-researcher", "description": "Fully local web research and report writing assistant"},
    {"owner": "meta-llama", "name": "llama-models", "description": "Utilities intended for use with Llama models"},
    {"owner": "huggingface", "name": "transformers", 
     "description": "🤗 Transformers: State-of-the-art Machine Learning for PyTorch, TensorFlow, and JAX"},
    {"owner": "langchain-ai", "name": "langchain", "description": "🦜️ Build context-aware reasoning applications"},
    {"owner": "expressjs", "name": "express", "description": ""},
    {"owner": "lodash", "name": "lodash", 
     "description": "A modern JavaScript utility library delivering modularity, performance, & extras"},
    {"owner": "sqlite", "name": "sqlite", "description": "Official Git mirror of the SQLite source tree"},
    {"owner": "microsoft", "name": "monaco-editor", "description": "A browser based code editor"},
]


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def fetch_repo_data(owner: str, name: str) -> Dict:
    """
    Fetch repository data from GitHub API
    """
    logger.info(f"Fetching repository data for {owner}/{name}")
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    else:
        logger.warning("No GitHub token found. API rate limits may be restricted.")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{name}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"Failed to fetch repository data: {owner}/{name}, status code: {response.status_code}, response: {response.text}")
                return {
                    "owner": owner,
                    "name": name,
                    "full_name": f"{owner}/{name}",
                    "description": "Repository not found or API rate limit exceeded",
                    "stars": 0,
                    "error": True
                }
            
            data = response.json()
            logger.info(f"Successfully fetched data for {owner}/{name}")
            return {
                "owner": owner,
                "name": name,
                "full_name": data.get("full_name", f"{owner}/{name}"),
                "description": data.get("description", ""),
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "language": data.get("language", ""),
                "error": False
            }
        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching repository data for {owner}/{name}")
            return {
                "owner": owner,
                "name": name,
                "full_name": f"{owner}/{name}",
                "description": "Request timed out",
                "stars": 0,
                "error": True
            }
        except Exception as e:
            logger.error(f"Error fetching repository data for {owner}/{name}: {str(e)}")
            return {
                "owner": owner,
                "name": name,
                "full_name": f"{owner}/{name}",
                "description": f"An error occurred: {str(e)}",
                "stars": 0,
                "error": True
            }


async def search_repositories(query: str) -> List[Dict]:
    """
    Search GitHub repositories based on a query
    """
    if not query:
        return []

    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc",
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        return [
            {
                "owner": repo["owner"]["login"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo["description"] or "",
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "language": repo["language"] or ""
            }
            for repo in data.get("items", [])[:10]  # Limit to top 10 results
        ]


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Home page route handler
    """
    # Get all repositories (both remote and default) using data controller
    data_controller = get_data_controller()
    all_repos = await data_controller.get_all_repositories(DEFAULT_REPOS)
    
    # Fetch additional data for each repository
    repos = []
    for repo in all_repos:
        repo_data = await fetch_repo_data(repo["owner"], repo["name"])
        repos.append(repo_data)
    
    return templates.TemplateResponse("index.html", {"request": request, "repos": repos})

from pydantic import BaseModel

# Define request body schema
class RepoRequest(BaseModel):
    owner: str
    name: str

@app.post("/repo/add")
async def add_repository(payload: RepoRequest):
    """
    Add a repository API endpoint
    """
    try:
        data_controller = get_data_controller()

        print(f"Adding repository: {payload.owner}/{payload.name}")
        # Verify repository exists on GitHub before adding
        repo_data = await fetch_repo_data(payload.owner, payload.name)
        if repo_data.get("error", False):
            raise HTTPException(status_code=404, detail="Repository not found")
        
        success = await data_controller.add_repository(payload.owner, payload.name)
        if not success:
            raise HTTPException(status_code=400, detail="Repository already exists")
        
        return {"status": "success"}
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"GitHub API request failed: {str(e)}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.delete("/repo/remove")
async def remove_repository(request: Request):
    """
    Remove a repository API endpoint
    """
    form_data = await request.form()
    owner = form_data.get("owner")
    name = form_data.get("name")
    
    if not owner or not name:
        raise HTTPException(status_code=400, detail="Missing owner or name parameter")
    
    data_controller = get_data_controller()
    success = await data_controller.remove_repository(owner, name)
    if not success:
        raise HTTPException(status_code=404, detail="Repository not found or is a default repository")
    
    return {"status": "success"}


@app.get("/search")
async def search(q: Optional[str] = Query(None)):
    """
    Search repositories API endpoint
    """
    if not q:
        return []
    
    # Search GitHub API
    results = await search_repositories(q)
    
    # Get existing repositories to mark which ones are already added
    data_controller = get_data_controller()
    existing_repos = await data_controller.get_all_repositories(DEFAULT_REPOS)
    
    # Add a flag to indicate if repository is already in our system
    for result in results:
        result["is_added"] = any(
            r["owner"] == result["owner"] and r["name"] == result["name"]
            for r in existing_repos
        )
    
    return results


@app.get("/repo/{owner}/{name}", response_class=HTMLResponse)
async def repo_details(request: Request, owner: str, name: str):
    """
    Repository details page
    """
    repo_data = await fetch_repo_data(owner, name)
    
    if repo_data.get("error", False):
        raise HTTPException(status_code=404, detail="Repository not found or API rate limit exceeded")
    
    return templates.TemplateResponse("repo.html", {"request": request, "repo": repo_data})


@app.get("/repo/index")
async def repository_index():
    """
    Get index of all repositories in the system
    """
    data_controller = get_data_controller()
    repos = await data_controller.get_all_repositories()
    return {
        "repositories": repos,
        "total": len(repos)
    }


@app.get("/repo/{owner}/{name}/data")
async def get_repository_data(owner: str, name: str):
    """
    Get repository data API endpoint
    """
    repo_data = await fetch_repo_data(owner, name)
    if repo_data.get("error", False):
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo_data


def run():
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
