"""WebAccess MCP - API-based web search and content retrieval for Phase I."""

import httpx
from typing import List, Dict, Optional, Any
from icarus.common.logging_config import get_mcp_logger
from icarus.common.secrets import secrets


class WebAccessMCP:
    """Phase I: Lightweight API-based web access."""
    
    def __init__(self, tavily_api_key: Optional[str] = None):
        self.logger = get_mcp_logger(tool_name="WebAccess")
        self.tavily_api_key = tavily_api_key or secrets.get("TAVILY_API_KEY")
        
        if not self.tavily_api_key:
            self.logger.warning("Tavily API key not set - web search will be disabled")
        else:
            self.logger.info(
                "WebAccess MCP initialized",
                api_key_set=True,
                masked_key=secrets.mask("TAVILY_API_KEY", self.tavily_api_key)
            )
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web using Tavily API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
        
        Returns:
            List of search results with title, url, and snippet
        """
        if not self.tavily_api_key:
            self.logger.error("Tavily API key not configured - cannot perform search")
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.tavily_api_key,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "basic"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score", 0.0)
                    })
                
                self.logger.info(f"Web search completed", query=query, results_count=len(results))
                return results
        
        except httpx.HTTPStatusError as e:
            self.logger.error_with_context(
                "Web search HTTP error",
                e,
                query=query,
                status_code=e.response.status_code
            )
        except httpx.RequestError as e:
            self.logger.error_with_context(
                "Web search network error",
                e,
                query=query
            )
        except Exception as e:
            self.logger.error_with_context(
                "Web search unexpected error",
                e,
                query=query
            )
        
        return []
    
    async def read(self, url: str) -> str:
        """Read content from a URL (text-only extraction).
        
        Args:
            url: URL to fetch content from
        
        Returns:
            Markdown-formatted text content
        """
        try:
            # Use Jina AI Reader for clean markdown extraction
            reader_url = f"https://r.jina.ai/{url}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(reader_url, timeout=30.0)
                response.raise_for_status()
                
                content = response.text
                self.logger.info(f"Successfully read content from URL", url=url, content_length=len(content))
                return content
        
        except httpx.HTTPStatusError as e:
            self.logger.warning(
                "URL read failed - trying fallback",
                url=url,
                status_code=e.response.status_code
            )
            
            # Fallback: Simple HTTP GET
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=30.0)
                    response.raise_for_status()
                    self.logger.info("Fallback read successful", url=url)
                    return response.text
            except Exception as fallback_error:
                self.logger.error_with_context(
                    "Fallback read also failed",
                    fallback_error,
                    url=url
                )
                return f"Error: Could not retrieve content from {url}"
        
        except Exception as e:
            self.logger.error_with_context(
                "URL read unexpected error",
                e,
                url=url
            )
            return f"Error: Could not retrieve content from {url}"
