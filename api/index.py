import sys
from pathlib import Path

# Allow importing main.py / scraper.py from the project root
sys.path.append(str(Path(__file__).resolve().parent.parent))

from main import app  # noqa: E402
