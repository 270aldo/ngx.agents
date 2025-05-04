import os
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

# Configuración del servidor
API_HOST = os.getenv("HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", 8000))
A2A_PORT = int(os.getenv("A2A_PORT", 8001))
DEBUG = os.getenv("DEBUG", "True") == "True"

# Configuración de A2A (Agent-to-Agent)
A2A_HOST = os.getenv("A2A_HOST", "localhost")
A2A_SERVER_URL = os.getenv("A2A_SERVER_URL", f"http://{A2A_HOST}:{A2A_PORT}")
A2A_WEBSOCKET_URL = os.getenv("A2A_WEBSOCKET_URL", f"ws://{A2A_HOST}:{A2A_PORT}")

# Configuración de seguridad
API_KEY_DEFAULT = os.getenv("API_KEY_DEFAULT", "ngx_development_api_key_2025")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Gemini / Vertex
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
VERTEX_API_KEY = os.getenv("VERTEX_API_KEY")

# Perplexity
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Configuración de reintentos y timeouts
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", 1.5))
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", 30))

# ----------------------------------------
# MCP (Model Context Protocol)
# ----------------------------------------
MCP_BASE_URL = os.getenv("MCP_BASE_URL")
MCP_API_KEY = os.getenv("MCP_API_KEY")

# Nota: Las credenciales sensibles como API keys no deben almacenarse directamente en el código
# Se recomienda usar variables de entorno o servicios de gestión de secretos
