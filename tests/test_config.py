"""
Shared test configuration.
Loads credentials from .secrets.env or environment variables.
"""

import os

def load_secrets():
    """Load secrets from .secrets.env file."""
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".secrets.env")

    if os.path.exists(secrets_path):
        with open(secrets_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

# Load on import
load_secrets()

# Test configuration - from environment
AUTH_TOKEN = os.environ.get("CAPACITIES_AUTH_TOKEN")
SPACE_ID = os.environ.get("CAPACITIES_SPACE_ID", "")
NOTE_STRUCTURE_ID = os.environ.get("CAPACITIES_NOTE_STRUCTURE_ID", "")

def get_auth_token(cli_token: str = None) -> str:
    """Get auth token from CLI arg or environment."""
    if cli_token:
        return cli_token
    if AUTH_TOKEN:
        return AUTH_TOKEN
    return None

def require_auth_token(cli_token: str = None) -> str:
    """Get auth token or exit with error."""
    token = get_auth_token(cli_token)
    if not token:
        print("\nERROR: No authentication token provided")
        print("\nTo provide a token, use one of these methods:")
        print("  1. Create .secrets.env with CAPACITIES_AUTH_TOKEN=your-token")
        print("  2. Environment: export CAPACITIES_AUTH_TOKEN=your-token")
        print("  3. Command line: python test_*.py --token YOUR_TOKEN")
        import sys
        sys.exit(1)
    return token
