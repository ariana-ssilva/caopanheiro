import struct

from app import create_app


def test_manifest_icons_and_root_worker_are_available(tmp_path):
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'pwa.sqlite3')})
    client = app.test_client()
    page = client.get('/').get_data(as_text=True)
    assert 'rel="manifest"' in page
    assert 'rel="apple-touch-icon"' in page
    assert 'id="install-app"' in page
    response = client.get('/static/manifest.webmanifest')
    assert response.status_code == 200
    import json
    manifest = json.loads(response.data)
    assert manifest['start_url'] == '/'
    assert manifest['scope'] == '/'
    assert manifest['display'] == 'standalone'
    for icon in manifest['icons']:
        image = client.get(icon['src'])
        assert image.status_code == 200
        assert image.data[:8] == b'\x89PNG\r\n\x1a\n'
        width, height = struct.unpack('>II', image.data[16:24])
        assert icon['sizes'] == f'{width}x{height}'
    worker = client.get('/service-worker.js')
    assert worker.status_code == 200
    assert worker.headers['Service-Worker-Allowed'] == '/'
    assert worker.headers['Cache-Control'] == 'no-cache'
    assert 'javascript' in worker.mimetype
    offline = client.get('/static/pwa/offline.html')
    assert offline.status_code == 200
    assert 'Não conseguimos conectar' in offline.get_data(as_text=True)


def test_pwa_assets_do_not_query_database_for_logged_in_session(tmp_path, monkeypatch):
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'pwa.sqlite3')})
    client = app.test_client()
    with client.session_transaction() as session:
        session['user_id'] = 1
    def unavailable(*args, **kwargs):
        raise AssertionError('Static PWA assets must not require a database connection')
    monkeypatch.setattr('app.query_db', unavailable)
    for path in ('/service-worker.js', '/static/manifest.webmanifest', '/static/pwa/offline.html'):
        assert client.get(path).status_code == 200
