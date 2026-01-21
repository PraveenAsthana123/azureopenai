"""
Git Repository Connector
Extracts documentation from Git repositories (Azure DevOps, GitHub, GitLab).
"""

import asyncio
import base64
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class GitDocument:
    """Represents a document from a Git repository."""
    id: str
    path: str
    filename: str
    repository: str
    branch: str
    web_url: str
    content: str
    content_type: str
    size: int
    sha: str
    last_commit_date: datetime
    last_commit_author: str
    last_commit_message: str


class GitHubConnector:
    """Connector for GitHub repositories."""

    API_BASE = "https://api.github.com"
    DOC_EXTENSIONS = {".md", ".mdx", ".txt", ".rst", ".adoc", ".html", ".htm"}
    CODE_DOC_FILES = {"README.md", "CONTRIBUTING.md", "CHANGELOG.md", "LICENSE"}

    def __init__(
        self,
        token: str,
        include_code_files: bool = False,
        max_file_size_kb: int = 500,
    ):
        self.token = token
        self.include_code_files = include_code_files
        self.max_file_size = max_file_size_kb * 1024
        self.session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def _make_request(self, url: str) -> dict | list:
        """Make authenticated request to GitHub API."""
        async with self.session.get(url) as response:
            if response.status == 403:
                # Rate limited
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                wait_time = max(reset_time - int(datetime.now().timestamp()), 60)
                logger.warning(f"Rate limited, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                return await self._make_request(url)

            response.raise_for_status()
            return await response.json()

    async def list_repos(self, org: str) -> list[dict]:
        """List repositories in an organization."""
        repos = []
        page = 1

        while True:
            url = f"{self.API_BASE}/orgs/{org}/repos?per_page=100&page={page}"
            data = await self._make_request(url)

            if not data:
                break

            repos.extend(data)
            page += 1

        return repos

    async def list_files(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        path: str = "",
    ) -> AsyncIterator[GitDocument]:
        """List and retrieve documentation files from a repository."""
        url = f"{self.API_BASE}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"

        try:
            data = await self._make_request(url)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                # Try 'master' branch if 'main' not found
                if branch == "main":
                    async for doc in self.list_files(owner, repo, "master", path):
                        yield doc
                    return
            raise

        for item in data.get("tree", []):
            if item["type"] != "blob":
                continue

            file_path = item["path"]
            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower()

            # Filter by documentation files
            is_doc = ext in self.DOC_EXTENSIONS or filename in self.CODE_DOC_FILES
            if not is_doc and not self.include_code_files:
                continue

            # Check file size
            if item.get("size", 0) > self.max_file_size:
                continue

            # Get file content
            content = await self._get_file_content(owner, repo, file_path, branch)
            if content is None:
                continue

            # Get last commit info
            commit_info = await self._get_last_commit(owner, repo, file_path, branch)

            yield GitDocument(
                id=f"{owner}/{repo}/{file_path}@{branch}",
                path=file_path,
                filename=filename,
                repository=f"{owner}/{repo}",
                branch=branch,
                web_url=f"https://github.com/{owner}/{repo}/blob/{branch}/{file_path}",
                content=content,
                content_type=self._get_content_type(ext),
                size=item.get("size", 0),
                sha=item["sha"],
                last_commit_date=commit_info.get("date", datetime.now()),
                last_commit_author=commit_info.get("author", ""),
                last_commit_message=commit_info.get("message", ""),
            )

    async def _get_file_content(self, owner: str, repo: str, path: str, branch: str) -> str | None:
        """Get file content."""
        url = f"{self.API_BASE}/repos/{owner}/{repo}/contents/{path}?ref={branch}"

        try:
            data = await self._make_request(url)
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
            return data.get("content", "")
        except Exception as e:
            logger.warning(f"Failed to get content for {path}: {e}")
            return None

    async def _get_last_commit(self, owner: str, repo: str, path: str, branch: str) -> dict:
        """Get last commit info for a file."""
        url = f"{self.API_BASE}/repos/{owner}/{repo}/commits?path={path}&sha={branch}&per_page=1"

        try:
            data = await self._make_request(url)
            if data:
                commit = data[0]
                return {
                    "date": datetime.fromisoformat(commit["commit"]["committer"]["date"].replace("Z", "+00:00")),
                    "author": commit["commit"]["author"]["email"],
                    "message": commit["commit"]["message"][:200],
                }
        except Exception as e:
            logger.warning(f"Failed to get commit info for {path}: {e}")

        return {}

    def _get_content_type(self, ext: str) -> str:
        """Map file extension to content type."""
        mapping = {
            ".md": "text/markdown",
            ".mdx": "text/markdown",
            ".txt": "text/plain",
            ".rst": "text/x-rst",
            ".adoc": "text/asciidoc",
            ".html": "text/html",
            ".htm": "text/html",
        }
        return mapping.get(ext, "text/plain")


class AzureDevOpsConnector:
    """Connector for Azure DevOps Git repositories."""

    def __init__(
        self,
        organization: str,
        project: str,
        personal_access_token: str,
        max_file_size_kb: int = 500,
    ):
        self.organization = organization
        self.project = project
        self.pat = personal_access_token
        self.max_file_size = max_file_size_kb * 1024
        self.api_base = f"https://dev.azure.com/{organization}/{project}/_apis"
        self.session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Initialize HTTP session."""
        auth = base64.b64encode(f":{self.pat}".encode()).decode()
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
            }
        )

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def _make_request(self, url: str) -> dict:
        """Make authenticated request to Azure DevOps API."""
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    async def list_repos(self) -> list[dict]:
        """List repositories in the project."""
        url = f"{self.api_base}/git/repositories?api-version=7.0"
        data = await self._make_request(url)
        return data.get("value", [])

    async def list_files(
        self,
        repo_id: str,
        branch: str = "main",
    ) -> AsyncIterator[GitDocument]:
        """List and retrieve documentation files from a repository."""
        url = f"{self.api_base}/git/repositories/{repo_id}/items?recursionLevel=Full&api-version=7.0&versionDescriptor.version={branch}"

        data = await self._make_request(url)

        for item in data.get("value", []):
            if item.get("isFolder", False):
                continue

            path = item["path"]
            filename = os.path.basename(path)
            ext = os.path.splitext(filename)[1].lower()

            # Filter documentation files
            doc_extensions = {".md", ".mdx", ".txt", ".rst", ".html"}
            if ext not in doc_extensions:
                continue

            # Get content
            content_url = f"{self.api_base}/git/repositories/{repo_id}/items?path={path}&api-version=7.0&versionDescriptor.version={branch}"
            async with self.session.get(content_url, headers={"Accept": "text/plain"}) as resp:
                content = await resp.text()

            yield GitDocument(
                id=f"{repo_id}/{path}@{branch}",
                path=path,
                filename=filename,
                repository=repo_id,
                branch=branch,
                web_url=item.get("url", ""),
                content=content,
                content_type="text/markdown" if ext == ".md" else "text/plain",
                size=len(content),
                sha=item.get("objectId", ""),
                last_commit_date=datetime.now(),
                last_commit_author="",
                last_commit_message="",
            )
