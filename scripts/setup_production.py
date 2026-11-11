"""Cria a configuração privada no servidor sem exibir a chave secreta."""
import json
import os
import secrets
from pathlib import Path


def setup(project_root):
    instance = project_root / 'instance'
    instance.mkdir(parents=True, exist_ok=True)
    target = instance / 'production.json'
    if target.exists():
        print('Configuração existente preservada.')
        return
    config = {'SECRET_KEY': secrets.token_hex(32), 'SESSION_COOKIE_SECURE': True,
              'SESSION_COOKIE_HTTPONLY': True, 'SESSION_COOKIE_SAMESITE': 'Lax',
              'DEBUG': False, 'TESTING': False}
    descriptor = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        json.dump(config, output, indent=2)
    print('Configuração de produção criada em instance/production.json.')


if __name__ == '__main__':
    setup(Path(__file__).resolve().parent.parent)
