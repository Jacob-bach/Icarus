"""Simplified secrets management for ICARUS v2.0.

This module provides streamlined secrets management:
- Environment variable validation
- Secret masking for logs
- Runtime validation

Security Principles:
    1. Never log actual secret values
    2. Validate required secrets at startup
    3. Provide clear error messages for missing secrets
"""

import os
import re
from typing import Optional, Dict
from dataclasses import dataclass
from icarus.common.logging_config import get_orchestrator_logger

logger = get_orchestrator_logger()


@dataclass
class SecretConfig:
    """Configuration for a secret.
    
    Attributes:
        name: Environment variable name
        required: Whether the secret is required for operation
        default: Default value if not required
        description: Human-readable description
        sensitive: Whether to mask in logs (default: True)
    """
    name: str
    required: bool = True
    default: Optional[str] = None
    description: str = ""
    sensitive: bool = True


# Define all secrets used by ICARUS
SECRETS_CONFIG: Dict[str, SecretConfig] = {
    # Database
    "DATABASE_URL": SecretConfig(
        name="DATABASE_URL",
        required=True,
        default="sqlite+aiosqlite:///./icarus.db",
        description="Database connection URL",
        sensitive=True
    ),
    
    # v2.0 Feature Flags (read from config.yaml, but can be overridden)
    "ENABLE_REFLECTION": SecretConfig(
        name="ENABLE_REFLECTION",
        required=False,
        default="false",
        description="Enable reflection engine",
        sensitive=False
    ),
    "ENABLE_TDD_INTEGRATION": SecretConfig(
        name="ENABLE_TDD_INTEGRATION",
        required=False,
        default="false",
        description="Enable TDD workflow",
        sensitive=False
    ),
    
    # MCP Tools
    "TAVILY_API_KEY": SecretConfig(
        name="TAVILY_API_KEY",
        required=False,
        description="API key for Tavily web search",
        sensitive=True
    ),
    "GITHUB_TOKEN": SecretConfig(
        name="GITHUB_TOKEN",
        required=False,
        description="GitHub personal access token",
        sensitive=True
    ),
    "DISCORD_WEBHOOK_URL": SecretConfig(
        name="DISCORD_WEBHOOK_URL",
        required=False,
        description="Discord webhook URL for notifications",
        sensitive=True
    ),
}


class SecretsManager:
    """Manages secure access to environment secrets.
    
    Example:
        >>> secrets = SecretsManager()
        >>> secrets.validate_required()
        >>> db_url = secrets.get("DATABASE_URL")
        >>> logger.info(f"Using database: {secrets.mask('DATABASE_URL', db_url)}")
    """
    
    def __init__(self):
        """Initialize the secrets manager."""
        self._config = SECRETS_CONFIG
        logger.debug("SecretsManager initialized", secret_count=len(self._config))
    
    # Retrieve secret from environment with validation
    # WHY: Centralize secret access with required/optional enforcement
    # key (str): Environment variable name (e.g., "DATABASE_URL")
    # default (str): Fallback value if not found
    # Returns: Secret value (str) or None
    # Raises: ValueError if required secret missing
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        config = self._config.get(key)
        
        if config is None:
            logger.warning(f"Accessing undeclared secret", key=key)
            return os.getenv(key, default)
        
        value = os.getenv(config.name)
        
        if value is None:
            if config.required and default is None:
                raise ValueError(
                    f"Required secret '{config.name}' not found. "
                    f"Description: {config.description}"
                )
            value = default or config.default
        
        return value
    
    # Convert environment variable to boolean for feature flags
    # WHY: Enable/disable features via env vars (ENABLE_REFLECTION=true)
    # key (str): Environment variable name
    # default (bool): Fallback if not set
    # Returns: Boolean interpretation of env var
    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key, str(default))
        if value is None:
            return default
        
        value_lower = value.lower().strip()
        return value_lower in ('true', 'yes', '1')
    
    # Mask secret values for safe logging (prevents credential leaks)
    # WHY: Allow logging database connections without exposing passwords
    # key (str): Secret name for sensitivity check
    # value (str): Actual secret value
    # Returns: Masked string (str) safe for logs
    def mask(self, key: str, value: str) -> str:
        if not value:
            return "[EMPTY]"
        
        config = self._config.get(key)
        if config and not config.sensitive:
            return value  # Not sensitive, return as-is
        
        # Mask URLs specially
        if value.startswith(('http://', 'https://', 'postgresql://', 'sqlite://')):
            return self._mask_url(value)
        
        # Mask tokens/keys
        if len(value) > 16:
            return f"{value[:4]}...{value[-4:]}"
        else:
            return "*" * min(len(value), 8)
    
    def _mask_url(self, url: str) -> str:
        """Mask sensitive parts of a URL.
        
        Args:
            url: URL to mask
            
        Returns:
            Masked URL showing protocol and host only
        """
        # Simple masking: show protocol and host, hide credentials and path
        if '@' in url:
            protocol_part = url.split('://')[0] if '://' in url else ''
            host_part = url.split('@')[-1].split('/')[0]
            return f"{protocol_part}://***:***@{host_part}/***"
        else:
            # No credentials, just mask path
            parts = url.split('/')
            if len(parts) > 3:
                return f"{parts[0]}//{parts[2]}/***"
            return url
    
    def validate_required(self) -> None:
        """Validate that all required secrets are present.
        
        Should be called at application startup.
        
        Raises:
            ValueError: If any required secrets are missing
        """
        missing = []
        
        for key, config in self._config.items():
            if config.required:
                value = os.getenv(config.name)
                if value is None and config.default is None:
                    missing.append({
                        "name": config.name,
                        "description": config.description
                    })
        
        if missing:
            error_msg = "Missing required secrets:\n"
            for secret in missing:
                error_msg += f"  - {secret['name']}: {secret['description']}\n"
            error_msg += "\nPlease set these environment variables or update .env file"
            
            logger.critical("Required secrets missing", missing_count=len(missing))
            raise ValueError(error_msg)
        
        logger.info(
            "✓ All required secrets validated",
            total_secrets=len(self._config),
            required_count=sum(1 for c in self._config.values() if c.required)
        )


# Global secrets manager instance
secrets = SecretsManager()


def validate_secrets_at_startup() -> None:
    """Validate secrets when application starts.
    
    This should be called in main.py before initializing other components.
    
    Raises:
        ValueError: If required secrets are missing
    """
    logger.info("🔐 Validating secrets configuration...")
    secrets.validate_required()
