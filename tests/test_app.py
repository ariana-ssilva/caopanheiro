import pytest
import os
from io import BytesIO

from app import create_app
from app.db import execute_db, query_db
from app.security import hash_password


@pytest.fixture()
def client(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.sqlite3"),
        "DATABASE_URL": os.environ.get("TEST_DATABASE_URL", ""),
        "SECRET_KEY": "test",
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })
    with app.test_client() as client:
        with app.app_context():
            if os.environ.get("TEST_DATABASE_URL"):
                # Only run this suite against a disposable local test database.
                from urllib.parse import urlparse
                assert urlparse(os.environ["TEST_DATABASE_URL"]).hostname in ("127.0.0.1", "localhost")
                from app.db import get_db
                cursor = get_db().cursor()
                cursor.execute("TRUNCATE donation_events,feedback,favorites,donations,adoptions,animals,users RESTART IDENTITY CASCADE")
                get_db().commit()
                cursor.close()
            execute_db("INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,'ong')",
                       ("Equipe", "ong@test.com", hash_password("password")))
            execute_db("INSERT INTO animals (name,species,age,size,description,health) VALUES (?,?,?,?,?,?)",
                       ("Luna", "Cão", "2 anos", "Médio", "Dócil", "Vacinada"))
        yield client


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def test_animals_are_public(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Luna" in response.data


def test_adopter_can_register_and_request_adoption(client):
    response = client.post("/register", data={"name": "Ariana", "email": "a@a.com", "password": "password"}, follow_redirects=True)
    assert b"Cadastro realizado" in response.data
    login(client, "a@a.com", "password")
    response = client.post("/adoptions/new/1", data={"message": "Tenho espaço e tempo.", "full_name": "Ariana", "phone": "49999999999", "housing": "Casa com quintal seguro", "household": "Todos concordam", "experience": "Já cuido de pets", "consent": "on"}, follow_redirects=True)
    assert "Recebemos seu pedido" in response.get_data(as_text=True)
    with client.application.app_context():
        adoption = query_db("SELECT * FROM adoptions", one=True)
        assert adoption["status"] == "pending"
        assert "Casa com quintal seguro" in adoption["answers"]


def test_ong_can_approve_adoption(client):
    with client.application.app_context():
        execute_db("INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,'adopter')",
                   ("Ariana", "a@a.com", hash_password("password")))
        execute_db("INSERT INTO adoptions (animal_id,adopter_id,message) VALUES (1,2,'Olá')")
    login(client, "ong@test.com", "password")
    response = client.post("/admin/adoptions/1/status", data={"status": "approved"}, follow_redirects=True)
    assert b"atualizado" in response.data


def test_adopter_cannot_access_admin(client):
    client.post("/register", data={"name": "Ariana", "email": "a@a.com", "password": "password"})
    login(client, "a@a.com", "password")
    assert client.get("/admin").status_code == 403


def test_ong_can_upload_animal_photo(client):
    login(client, "ong@test.com", "password")
    response = client.post(
        "/admin/animals/new",
        data={
            "name": "Bidu",
            "species": "Cão",
            "photo": (BytesIO(b"fake image"), "bidu.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    with client.application.app_context():
        animal = query_db("SELECT photo_filename FROM animals WHERE name = ?", ("Bidu",), one=True)
    assert animal["photo_filename"].endswith(".png")
    assert b"Bidu" in response.data


def test_ong_can_edit_animal(client):
    login(client, "ong@test.com", "password")
    response = client.post(
        "/admin/animals/1/edit",
        data={
            "name": "Luna atualizada",
            "species": "Cão",
            "age": "3 anos",
            "size": "Grande",
            "description": "Muito carinhosa",
            "health": "Vacinada",
            "status": "available",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with client.application.app_context():
        animal = query_db("SELECT * FROM animals WHERE id = 1", one=True)
    assert animal["name"] == "Luna atualizada"
    assert animal["size"] == "Grande"
    assert b"Luna atualizada" in response.data


def test_incomplete_application_is_not_saved(client):
    login(client, "ong@test.com", "password")
    response = client.post("/adoptions/new/1", data={"message": "Olá"}, follow_redirects=True)
    assert "Preencha todas as etapas" in response.get_data(as_text=True)
    with client.application.app_context():
        assert query_db("SELECT id FROM adoptions") == []


def test_new_statuses_and_candidate_answers_are_staff_only(client):
    login(client, "ong@test.com", "password")
    with client.application.app_context():
        execute_db("INSERT INTO adoptions (animal_id, adopter_id, message, answers) VALUES (1,1,?,?)", ("Olá", '{"phone":"49999999999"}'))
    for status in ("reviewing", "interview", "approved", "completed"):
        response = client.post("/admin/adoptions/1/status", data={"status": status}, follow_redirects=True)
        assert response.status_code == 200
        with client.application.app_context():
            assert query_db("SELECT status FROM adoptions WHERE id=1", one=True)["status"] == status
    assert "49999999999" in response.get_data(as_text=True)
    with client.application.app_context():
        assert query_db("SELECT status FROM animals WHERE id=1", one=True)["status"] == "adopted"
    client.post("/logout")
    assert "49999999999" not in client.get("/animal/1").get_data(as_text=True)


def test_animal_fields_and_filters(client):
    login(client, "ong@test.com", "password")
    client.post("/admin/animals/1/edit", data={"name": "Luna", "species": "Cão", "sex": "Fêmea", "vaccinated": "Sim", "neutered": "Não", "breed": "SRD", "status": "available"})
    client.post("/logout")
    assert "Luna" in client.get("/explore?sex=Fêmea&vaccinated=Sim").get_data(as_text=True)
    assert "Luna" not in client.get("/explore?sex=Macho").get_data(as_text=True)
    detail = client.get("/animal/1").get_data(as_text=True)
    assert "SRD" in detail
    assert "Cuidados em dia" not in detail


def test_core_pages_render(client):
    for path in ("/", "/welcome", "/explore", "/login", "/register", "/animal/1"):
        assert client.get(path).status_code == 200
    login(client, "ong@test.com", "password")
    for path in ("/admin", "/admin/animals/new", "/admin/animals/1/edit", "/profile", "/my-adoptions", "/favorites", "/donations", "/adoptions/new/1"):
        assert client.get(path).status_code == 200


def test_animal_detail_tags_preserve_text_and_escape_markup(client):
    with client.application.app_context():
        execute_db("UPDATE animals SET description=?, health=? WHERE id=1", (
            'Carinhosa; Adora passear\n<script>alert(1)</script>',
            'Alimentação especial; Retorno veterinário',
        ))
    html = client.get('/animal/1').get_data(as_text=True)
    assert '<li>Carinhosa</li>' in html
    assert '<li>Adora passear</li>' in html
    assert '<li>Alimentação especial</li>' in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
    assert '<script>alert(1)</script>' not in html


def test_animal_form_suggestions_and_values_survive_validation(client):
    login(client, 'ong@test.com', 'password')
    html = client.get('/admin/animals/new').get_data(as_text=True)
    assert 'Sem raça definida (SRD)' in html
    assert '<select name="size"' in html
    assert '<select name="species"' in html
    response = client.post('/admin/animals/new', data={
        'name': '', 'species': 'Gato', 'breed': 'Raça personalizada',
        'size': 'Pequeno', 'health': 'Cuidados específicos',
    })
    html = response.get_data(as_text=True)
    assert '<option selected>Gato</option>' in html
    assert 'value="Raça personalizada"' in html
    assert '>Cuidados específicos</textarea>' in html


def test_registration_with_optional_profile_photo(client):
    response = client.post('/register', data={
        'name': 'Ana', 'email': 'ana@test.com', 'password': 'password',
        'photo': (BytesIO(b'profile image'), 'perfil.png'),
    }, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    with client.application.app_context():
        user = query_db('SELECT * FROM users WHERE email=?', ('ana@test.com',), one=True)
        assert user['role'] == 'adopter'
        assert user['photo_filename'].endswith('.png')
        from pathlib import Path
        assert (Path(client.application.config['UPLOAD_FOLDER']) / user['photo_filename']).is_file()
    login(client, 'ana@test.com', 'password')
    assert user['photo_filename'] in client.get('/profile').get_data(as_text=True)
    assert user['photo_filename'] in client.get('/').get_data(as_text=True)


@pytest.mark.parametrize('role', ['adopter', 'ong', 'admin'])
def test_profile_photo_can_be_replaced_and_removed_for_all_roles(client, role):
    from pathlib import Path
    with client.application.app_context():
        execute_db('UPDATE users SET role=? WHERE id=1', (role,))
    login(client, 'ong@test.com', 'password')
    filenames = []
    for filename in ('primeira.png', 'segunda.webp'):
        response = client.post('/profile', data={
            'name': 'Nome atualizado', 'photo': (BytesIO(b'profile image'), filename),
        }, content_type='multipart/form-data', follow_redirects=True)
        assert response.status_code == 200
        with client.application.app_context():
            user = query_db('SELECT * FROM users WHERE id=1', one=True)
            assert user['role'] == role
            filenames.append(user['photo_filename'])
        assert (Path(client.application.config['UPLOAD_FOLDER']) / filenames[-1]).is_file()
    assert filenames[0] != filenames[1]
    assert not (Path(client.application.config['UPLOAD_FOLDER']) / filenames[0]).exists()
    # A normal name update must keep the photo.
    client.post('/profile', data={'name': 'Outro nome'})
    with client.application.app_context():
        assert query_db('SELECT photo_filename FROM users WHERE id=1', one=True)['photo_filename'] == filenames[-1]
    client.post('/profile', data={'name': 'Outro nome', 'remove_photo': 'on'})
    with client.application.app_context():
        assert query_db('SELECT photo_filename FROM users WHERE id=1', one=True)['photo_filename'] is None
    assert not (Path(client.application.config['UPLOAD_FOLDER']) / filenames[-1]).exists()


def test_invalid_profile_photo_does_not_change_user(client):
    login(client, 'ong@test.com', 'password')
    response = client.post('/profile', data={
        'name': 'Alterado', 'photo': (BytesIO(b'invalid'), 'arquivo.txt'),
    }, content_type='multipart/form-data')
    assert 'A foto deve estar no formato' in response.get_data(as_text=True)
    with client.application.app_context():
        user = query_db('SELECT * FROM users WHERE id=1', one=True)
        assert user['name'] == 'Equipe'
        assert user['photo_filename'] is None


def offer_donation(client, kind='alimentos', amount=''):
    return client.post('/donations', data={
        'kind': kind, 'description': 'Uma contribuição para os animais',
        'contact': 'WhatsApp 49999999999', 'amount': amount,
    }, follow_redirects=True)


def register_donor(client):
    client.post('/register', data={'name': 'Doadora', 'email': 'doadora@test.com', 'password': 'password'})
    login(client, 'doadora@test.com', 'password')


def test_full_donation_flow_and_history(client):
    register_donor(client)
    assert offer_donation(client, 'financeira', '50.25').status_code == 200
    with client.application.app_context():
        donation = query_db('SELECT * FROM donations', one=True)
        assert donation['status'] == 'pending'
        assert float(donation['amount']) == 50.25
    login(client, 'ong@test.com', 'password')
    assert client.get('/admin/donations').status_code == 200
    assert client.post('/admin/donations/1/status', data={'status': 'received', 'note': 'Recebido'}).status_code == 400
    for status in ('accepted', 'scheduled', 'received'):
        response = client.post('/admin/donations/1/status', data={'status': status, 'note': 'Orientação da equipe: ' + status}, follow_redirects=True)
        assert response.status_code == 200
    with client.application.app_context():
        assert query_db('SELECT status FROM donations WHERE id=1', one=True)['status'] == 'received'
        assert len(query_db('SELECT id FROM donation_events WHERE donation_id=1')) == 4
    assert client.post('/admin/donations/1/status', data={'status': 'accepted', 'note': 'Voltar'}).status_code == 400
    login(client, 'doadora@test.com', 'password')
    html = client.get('/donations/1').get_data(as_text=True)
    assert 'Orientação da equipe: received' in html
    assert 'R$ 50,25' in html
    assert client.post('/donations/1/cancel').status_code == 400


def test_donation_permissions_and_cancellation(client):
    register_donor(client)
    offer_donation(client)
    assert client.get('/admin/donations').status_code == 403
    assert client.post('/admin/donations/1/status', data={'status': 'accepted', 'note': 'ok'}).status_code == 403
    client.post('/register', data={'name': 'Outra', 'email': 'outra@test.com', 'password': 'password'})
    login(client, 'outra@test.com', 'password')
    assert client.get('/donations/1').status_code == 403
    assert client.post('/donations/1/cancel').status_code == 403
    assert 'WhatsApp 49999999999' not in client.get('/donations').get_data(as_text=True)
    login(client, 'doadora@test.com', 'password')
    assert client.post('/donations/1/cancel', follow_redirects=True).status_code == 200
    with client.application.app_context():
        assert query_db('SELECT status FROM donations WHERE id=1', one=True)['status'] == 'cancelled'
    client.post('/logout')
    assert client.get('/donations/1').status_code == 302


@pytest.mark.parametrize('amount', ['', '0', '-1', 'NaN', 'Infinity', '1.234', '100000000', 'abc'])
def test_invalid_financial_offer_is_not_recorded(client, amount):
    login(client, 'ong@test.com', 'password')
    response = offer_donation(client, 'financeira', amount)
    assert 'Informe um valor positivo' in response.get_data(as_text=True)
    with client.application.app_context():
        assert query_db('SELECT id FROM donations') == []
        assert query_db('SELECT id FROM donation_events') == []


def test_donation_requires_contact_and_staff_note(client):
    login(client, 'ong@test.com', 'password')
    client.post('/donations', data={'kind': 'alimentos', 'description': 'Ração'})
    with client.application.app_context():
        assert query_db('SELECT id FROM donations') == []
    offer_donation(client)
    response = client.post('/admin/donations/1/status', data={'status': 'accepted', 'note': ''}, follow_redirects=True)
    assert 'Informe as orientações' in response.get_data(as_text=True)
    with client.application.app_context():
        assert query_db('SELECT status FROM donations WHERE id=1', one=True)['status'] == 'pending'


def test_legacy_donation_migration_does_not_claim_receipt(tmp_path):
    import sqlite3
    from app.db import SCHEMA
    path = str(tmp_path / 'legacy.sqlite3')
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.execute("INSERT INTO users (name,email,password_hash) VALUES ('Antigo','antigo@test.com','hash')")
    db.execute("INSERT INTO donations (donor_id,kind,description,status) VALUES (1,'alimentos','Oferta antiga','received')")
    db.commit()
    db.close()
    config = {'TESTING': True, 'DATABASE': path, 'UPLOAD_FOLDER': str(tmp_path / 'uploads')}
    app = create_app(config)
    with app.app_context():
        assert query_db('SELECT status FROM donations', one=True)['status'] == 'pending'
        execute_db("UPDATE donations SET status='received'")
    # Subsequent restarts preserve receipts confirmed after migration.
    app = create_app(config)
    with app.app_context():
        assert query_db('SELECT status FROM donations', one=True)['status'] == 'received'


def test_dashboard_donations_summary_counts_only_appropriate_statuses(client):
    from flask import template_rendered
    from decimal import Decimal
    with client.application.app_context():
        for kind, amount, status in [('financeira', '10.10', 'received'), ('financeira', '20.20', 'received'), ('financeira', '5.15', 'pending'), ('financeira', '8.25', 'accepted'), ('financeira', '1000', 'cancelled'), ('financeira', '2000', 'declined'), ('alimentos', None, 'received'), ('alimentos', None, 'scheduled'), ('alimentos', None, 'cancelled')]:
            execute_db('INSERT INTO donations (donor_id,kind,amount,description,status) VALUES (1,?,?,?,?)', (kind, amount, 'Oferta', status))
    captured = []
    def capture(sender, template, context, **extra):
        captured.append(context)
    login(client, 'ong@test.com', 'password')
    with template_rendered.connected_to(capture, client.application):
        response = client.get('/admin')
    assert response.status_code == 200
    summary = captured[-1]['donation_summary']
    assert summary['financeira']['received_amount'] == Decimal('30.30')
    assert summary['financeira']['ongoing_amount'] == Decimal('13.40')
    assert summary['financeira']['received'] == 2
    assert summary['financeira']['ongoing'] == 2
    assert summary['alimentos']['received'] == 1
    assert summary['alimentos']['ongoing'] == 1
    assert summary['medicamentos']['received'] == 0
    assert summary['materiais']['ongoing'] == 0
    assert 'R$ 30,30' in response.get_data(as_text=True)


def test_dashboard_card_destinations_filter_lists_without_changing_totals(client):
    from flask import template_rendered
    with client.application.app_context():
        execute_db("INSERT INTO animals (name,species,status) VALUES ('Adotado','Gato','adopted')")
        execute_db("INSERT INTO donations (donor_id,kind,description) VALUES (1,'alimentos','Ração')")
        execute_db("INSERT INTO donations (donor_id,kind,description) VALUES (1,'materiais','Sabão')")
    login(client, 'ong@test.com', 'password')
    captured = []
    def capture(sender, template, context, **extra):
        captured.append(context)
    with template_rendered.connected_to(capture, client.application):
        response = client.get('/admin?animal_status=adopted')
        assert [item['name'] for item in captured[-1]['animals']] == ['Adotado']
        assert captured[-1]['stats']['available'] == 1
        assert captured[-1]['stats']['adopted'] == 1
        response = client.get('/admin/donations?kind=alimentos')
        assert [item['description'] for item in captured[-1]['donations']] == ['Ração']
    html = client.get('/admin').get_data(as_text=True)
    assert 'Acompanhar doações' in html
    assert '/admin?animal_status=available#animals' in html
    assert '/admin?application_status=ongoing#applications' in html
    assert '/admin/donations?kind=financeira' in html
