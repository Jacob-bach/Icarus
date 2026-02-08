"""GitHub MCP - Git operations and GitHub integration."""

from github import Github
from typing import Optional
from icarus.common.logging_config import get_mcp_logger
from icarus.common.secrets import secrets


class GitHubMCP:
    """GitHub integration via PyGithub."""
    
    def __init__(self, access_token: Optional[str] = None):
        self.logger = get_mcp_logger(tool_name="GitHub")
        self.access_token = access_token or secrets.get("GITHUB_TOKEN")
        
        if not self.access_token:
            self.logger.warning("GitHub token not set - GitHub operations will be disabled")
            self.client = None
        else:
            self.client = Github(self.access_token)
            self.logger.info(
                "GitHub MCP initialized",
                token_set=True,
                masked_token=secrets.mask("GITHUB_TOKEN", self.access_token)
            )
    
    def create_branch(self, repo_name: str, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch with naming convention enforcement.
        
        Args:
            repo_name: Repository name (format: "owner/repo")
            branch_name: Name for the new branch
            from_branch: Source branch to branch from, defaults to "main"
        
        Returns:
            True if successful
        """
        if not self.client:
            self.logger.error("GitHub client not initialized")
            return False
        
        # Enforce naming conventions
        valid_prefixes = ["feat/", "fix/", "docs/", "refactor/", "test/"]
        if not any(branch_name.startswith(prefix) for prefix in valid_prefixes):
            self.logger.error(f"Branch name must start with one of: {valid_prefixes}")
            return False
        
        try:
            repo = self.client.get_repo(repo_name)
            
            # Get the source branch
            source = repo.get_branch(from_branch)
            
            # Create new branch
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source.commit.sha
            )
            
            self.logger.info(f"Created branch {branch_name} from {from_branch}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to create branch: {e}")
            return False
    
    def commit_and_push(
        self,
        repo_name: str,
        branch_name: str,
        files: dict,
        commit_message: str
    ) -> bool:
        """Commit files and push to branch.
        
        This should only be called AFTER the human approval gate.
        
        Args:
            repo_name: Repository name (format: "owner/repo")
            branch_name: Target branch name
            files: Dict mapping file paths to content
            commit_message: Commit message
        
        Returns:
            True if successful
        """
        if not self.client:
            self.logger.error("GitHub client not initialized")
            return False
        
        try:
            repo = self.client.get_repo(repo_name)
            branch = repo.get_branch(branch_name)
            
            # Create blobs and tree
            element_list = []
            for file_path, content in files.items():
                blob = repo.create_git_blob(content, "utf-8")
                element = {
                    "path": file_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob.sha
                }
                element_list.append(element)
            
            # Create tree
            base_tree = repo.get_git_tree(branch.commit.sha)
            tree = repo.create_git_tree(element_list, base_tree)
            
            # Create commit
            parent = repo.get_git_commit(branch.commit.sha)
            commit = repo.create_git_commit(
                message=commit_message,
                tree=tree,
                parents=[parent]
            )
            
            # Update branch reference
            ref = repo.get_git_ref(f"heads/{branch_name}")
            ref.edit(commit.sha)
            
            self.logger.info(f"Committed and pushed to {branch_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to commit and push: {e}")
            return False
    
    def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main"
    ) -> Optional[str]:
        """Create a pull request.
        
        Args:
            repo_name: Repository name (format: "owner/repo")
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch, defaults to "main"
        
        Returns:
            PR URL if successful, None otherwise
        """
        if not self.client:
            self.logger.error("GitHub client not initialized")
            return None
        
        try:
            repo = self.client.get_repo(repo_name)
            
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            self.logger.info(f"Created PR: {pr.html_url}")
            return pr.html_url
        
        except Exception as e:
            self.logger.error(f"Failed to create PR: {e}")
            return None
