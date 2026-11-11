"""Entrada de produção para Render/Gunicorn ou PythonAnywhere/WSGI."""
import os
from pathlib import Path
from app import create_app
from app.production import production_config, bootstrap_admin

application = create_app(production_config(os.environ, Path(__file__).resolve().parent))
bootstrap_admin(application, os.environ)
