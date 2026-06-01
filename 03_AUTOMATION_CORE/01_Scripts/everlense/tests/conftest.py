import sys, os
from pathlib import Path
# make the package importable when pytest runs from the code home
sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))
