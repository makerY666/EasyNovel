"""Compatibility entrypoint; desktop uses python -m easynovel."""
from easynovel.app import create_app
app=create_app()
