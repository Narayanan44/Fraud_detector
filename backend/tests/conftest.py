# pytest runs this file first. It lets every test file do "from app..." and "from engine_cases ..."
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))   # backend/
sys.path.insert(0, str(Path(__file__).parent))          # backend/tests/
