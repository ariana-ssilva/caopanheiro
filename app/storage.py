"""Armazenamento local no desenvolvimento e Supabase Storage na publicação."""
import json
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import current_app, url_for
from werkzeug.utils import secure_filename

MIME_TYPES = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}
PREFIX = 'supabase:'


def _request(path, method, data, content_type):
    config = current_app.config
    request = Request(config['SUPABASE_URL'].rstrip('/') + '/storage/v1/' + path,
                      data=data, method=method, headers={
                          'Authorization': 'Bearer ' + config['SUPABASE_SERVICE_ROLE_KEY'],
                          'apikey': config['SUPABASE_SERVICE_ROLE_KEY'],
                          'Content-Type': content_type,
                      })
    try:
        with urlopen(request, timeout=20) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError, OSError):
        # Never expose upstream responses, credentials or URLs in user messages.
        raise ValueError('Não foi possível acessar o armazenamento de fotos. Tente novamente.') from None


def save_photo(upload):
    if upload is None or not upload.filename:
        return None
    extension = Path(secure_filename(upload.filename)).suffix.lower()
    if extension not in MIME_TYPES:
        raise ValueError('A foto deve estar no formato JPG, PNG ou WEBP.')
    filename = uuid.uuid4().hex + extension
    if current_app.config['STORAGE_BACKEND'] == 'supabase':
        bucket = quote(current_app.config['SUPABASE_STORAGE_BUCKET'], safe='')
        _request('object/' + bucket + '/' + filename, 'POST', upload.read(), MIME_TYPES[extension])
        return PREFIX + filename
    upload.save(Path(current_app.config['UPLOAD_FOLDER']) / filename)
    return filename


def remove_photo(filename):
    if not filename:
        return
    if filename.startswith(PREFIX):
        if current_app.config['STORAGE_BACKEND'] != 'supabase':
            return
        bucket = quote(current_app.config['SUPABASE_STORAGE_BUCKET'], safe='')
        try:
            _request('object/' + bucket, 'DELETE', json.dumps({'prefixes': [filename[len(PREFIX):]]}).encode(), 'application/json')
        except ValueError:
            # Saving a replacement must not fail because old-object cleanup is unavailable.
            current_app.logger.warning('Falha ao remover foto antiga do armazenamento externo.')
    else:
        (Path(current_app.config['UPLOAD_FOLDER']) / Path(filename).name).unlink(missing_ok=True)


def photo_url(filename):
    if filename and filename.startswith(PREFIX):
        base = current_app.config['SUPABASE_URL'].rstrip('/')
        bucket = quote(current_app.config['SUPABASE_STORAGE_BUCKET'], safe='')
        return base + '/storage/v1/object/public/' + bucket + '/' + quote(filename[len(PREFIX):], safe='')
    return url_for('static', filename='uploads/' + (filename or ''))
