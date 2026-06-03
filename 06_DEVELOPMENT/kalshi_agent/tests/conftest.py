import sys
from pathlib import Path

# Make kalshi_agent importable from tests
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
