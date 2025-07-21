"""
pytest configuration file for RTSP capture service tests.

This file ensures proper Python path configuration for testing.
"""
import os
import sys

# Add the services/rtsp-capture directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
