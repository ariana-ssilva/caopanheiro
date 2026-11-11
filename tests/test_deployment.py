import io
import json
from urllib.error import URLError

import pytest
from werkzeug.datastructures import FileStorage

from app import create_app
from app.db import query_db
from app.production import production_config, bootstrap_admin
from app.security import check_password
from app.storage import save_photo, remove_photo, photo_url


def test_render_requires_persistent_services_and_secret(tmp_path):
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        production_config({}, tmp_path)
    environment = {'SECRET_KEY': 's' * 48, 'RENDER': 'true'}
    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        production_config(environment, tmp_path)
    environment['DATABASE_URL'] = 'postgresql://example/database'
    with pytest.raises(RuntimeError, match='STORAGE_BACKEND'):
        production_config(environment, tmp_path)
    environment['STORAGE_BACKEND'] = 'supabase'
    config = production_config(environment, tmp_path)
    assert config['SESSION_COOKIE_SECURE'] is True
    assert config['DEBUG'] is False


def test_admin_bootstrap_is_idempotent_and_never_promotes_existing_user(tmp_path):
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'test.db')})
    environment = {'ADMIN_EMAIL': 'admin@test.com', 'ADMIN_PASSWORD': 'strong-password-123'}
    bootstrap_admin(app, environment)
    bootstrap_admin(app, dict(environment, ADMIN_PASSWORD='different-password-123'))
    with app.app_context():
        users = query_db('SELECT * FROM users')
        assert len(users) == 1
        assert users[0]['role'] == 'admin'
        assert check_password(users[0]['password_hash'], 'strong-password-123')
    app.test_client().post('/register', data={'name': 'Adotante', 'email': 'adopter@test.com', 'password': 'password'})
    with pytest.raises(RuntimeError, match='sem permissão'):
        bootstrap_admin(app, dict(environment, ADMIN_EMAIL='adopter@test.com'))


def storage_app(tmp_path):
    return create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'test.db'), 'STORAGE_BACKEND': 'supabase',
                       'SUPABASE_URL': 'https://project.supabase.co', 'SUPABASE_SERVICE_ROLE_KEY': 'server-only-key',
                       'SUPABASE_STORAGE_BUCKET': 'caopanheiro-fotos'})


def test_supabase_upload_url_and_delete_without_local_file(tmp_path, monkeypatch):
    app = storage_app(tmp_path)
    requests = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{}'
    def send(request, timeout):
        requests.append(request)
        assert timeout == 20
        return Response()
    monkeypatch.setattr('app.storage.urlopen', send)
    with app.test_request_context():
        filename = save_photo(FileStorage(stream=io.BytesIO(b'picture'), filename='foto.png'))
        assert filename.startswith('supabase:')
        assert photo_url(filename).startswith('https://project.supabase.co/storage/v1/object/public/caopanheiro-fotos/')
        assert 'server-only-key' not in photo_url(filename)
        assert photo_url('old.jpg') == '/static/uploads/old.jpg'
        assert not (tmp_path / filename).exists()
        remove_photo(filename)
    assert requests[0].method == 'POST'
    assert requests[0].data == b'picture'
    assert requests[0].get_header('Content-type') == 'image/png'
    assert requests[1].method == 'DELETE'
    assert json.loads(requests[1].data)['prefixes'] == [filename.split(':')[1]]


def test_supabase_failure_does_not_fall_back_to_ephemeral_storage(tmp_path, monkeypatch):
    app = storage_app(tmp_path)
    def fail(*args, **kwargs):
        raise URLError('sensitive upstream details')
    monkeypatch.setattr('app.storage.urlopen', fail)
    with app.test_request_context():
        with pytest.raises(ValueError) as error:
            save_photo(FileStorage(stream=io.BytesIO(b'picture'), filename='foto.png'))
        assert 'sensitive' not in str(error.value)
        assert 'server-only-key' not in str(error.value)
