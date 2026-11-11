"""Configuração WSGI por ambiente e criação inicial do administrador."""
import json
from pathlib import Path

from .db import execute_db, query_db
from .security import hash_password


def production_config(environ, project_root):
    path = Path(project_root) / 'instance' / 'production.json'
    config = json.loads(path.read_text()) if path.is_file() else {}
    if environ.get('SECRET_KEY'):
        config['SECRET_KEY'] = environ['SECRET_KEY']
    if not isinstance(config.get('SECRET_KEY'), str) or len(config['SECRET_KEY']) < 32:
        raise RuntimeError('Configure SECRET_KEY com pelo menos 32 caracteres ou execute scripts/setup_production.py.')
    if environ.get('RENDER') == 'true':
        if not environ.get('DATABASE_URL', '').startswith(('postgres://', 'postgresql://')):
            raise RuntimeError('Configure DATABASE_URL do PostgreSQL no Render para preservar os dados.')
        if environ.get('STORAGE_BACKEND') != 'supabase':
            raise RuntimeError('Configure STORAGE_BACKEND=supabase no Render para preservar as fotos.')
    config.update(DEBUG=False, TESTING=False, SESSION_COOKIE_SECURE=True,
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
    return config


def bootstrap_admin(app, environ):
    email, password = environ.get('ADMIN_EMAIL', '').strip().lower(), environ.get('ADMIN_PASSWORD', '')
    if not email and not password:
        return
    if not email or len(password) < 12:
        raise RuntimeError('Para criar o administrador inicial, configure ADMIN_EMAIL e ADMIN_PASSWORD com pelo menos 12 caracteres.')
    with app.app_context():
        existing = query_db('SELECT role FROM users WHERE email=?', (email,), one=True)
        if existing:
            if existing['role'] != 'admin':
                raise RuntimeError('ADMIN_EMAIL já pertence a uma conta sem permissão de administrador. Use outro e-mail.')
            return
        execute_db("INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,'admin')",
                   (environ.get('ADMIN_NAME', 'Administrador'), email, hash_password(password)))
        app.logger.info('Administrador inicial criado.')
