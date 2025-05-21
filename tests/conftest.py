"""
Configure pytest to use our mock modules.
"""
import os
import sys

# Add parent directory to path so mocks can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Make sure our mock modules are imported before the real ones
import rich
import silero_vad
import soundfile