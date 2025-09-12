"""
Main blueprint for the application.
"""
from flask import Blueprint

bp = Blueprint('main', __name__)

# Import unified routes to register them
from app.main import unified_routes
from app.main import dashboard_routes  # noqa: F401

from app.main import routes  # noqa: E402, F401
