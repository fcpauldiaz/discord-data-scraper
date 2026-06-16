import os

DEFAULT_PLATFORM_URL = os.environ.get("TRADE_PLATFORM_URL", "http://localhost:3000")
DEFAULT_INGEST_URL = os.environ.get("TRADE_INGEST_URL", "http://localhost:8000/v1/ingest")
