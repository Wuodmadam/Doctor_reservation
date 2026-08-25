import sys
import os

# Ensure project root is on sys.path so `app` package can be imported during tests
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
