"""API key loading shared by notebooks and scripts."""
 
import os
 
from dotenv import find_dotenv, load_dotenv
 
 
def load_api_key() -> str:
    """Find .env.local in the current or a parent directory and return its API key."""
    env_file = find_dotenv(filename=".env.local", usecwd=True)
    if not env_file:
        raise FileNotFoundError(
            "Could not find .env.local in the current directory or any parent directory."
        )
 
    load_dotenv(env_file, override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(f"OPENAI_API_KEY is not set in {env_file}")
    return api_key
