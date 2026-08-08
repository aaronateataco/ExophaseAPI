import sys
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

# Allow importing main.py / scraper.py from the project root
sys.path.append(str(Path(__file__).resolve().parent.parent))

from main import app  # noqa: E402

# Enable CORS so requests from Discord / Equicord clients are permitted
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)