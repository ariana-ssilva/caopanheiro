import os
import json
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path

import click
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from .db import close_db, get_db, init_db, query_db, execute_db
from .donations import KINDS, STATUSES, TRANSITIONS, record_donation, transition_donation
from .storage import save_photo, remove_photo, photo_url
from .security import check_password, hash_password


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE_URL=os.environ.get("DATABASE_URL", ""),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        STORAGE_BACKEND=os.environ.get("STORAGE_BACKEND", "local"),
        SUPABASE_URL=os.environ.get("SUPABASE_URL", ""),
        SUPABASE_SERVICE_ROLE_KEY=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        SUPABASE_STORAGE_BUCKET=os.environ.get("SUPABASE_STORAGE_BUCKET", "caopanheiro-fotos"),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    upload_dir = Path(app.config.get("UPLOAD_FOLDER", Path(app.static_folder) / "uploads"))
    app.config["UPLOAD_FOLDER"] = str(upload_dir)
    if app.config["STORAGE_BACKEND"] not in ("local", "supabase"):
        raise ValueError("STORAGE_BACKEND deve ser local ou supabase.")
    if app.config["STORAGE_BACKEND"] == "supabase":
        if not app.config["SUPABASE_URL"].startswith("https://") or not app.config["SUPABASE_SERVICE_ROLE_KEY"]:
            raise ValueError("Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY para salvar as fotos.")
    else:
        upload_dir.mkdir(parents=True, exist_ok=True)
    app.jinja_env.globals["photo_url"] = photo_url
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db)

    @app.cli.command("create-admin")
    @click.option("--name", default="Administrador", show_default=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(name, email, password):
        """Cria um usuário administrador para a implantação inicial."""
        if len(password) < 8:
            raise click.ClickException("A senha deve ter pelo menos 8 caracteres.")
        if query_db("SELECT id FROM users WHERE email = ?", (email.lower(),), one=True):
            raise click.ClickException("Este e-mail já está cadastrado.")
        execute_db(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            (name, email.lower(), hash_password(password)),
        )
        click.echo("Administrador criado.")

    animal_options = json.loads((Path(app.root_path) / "data" / "animal_options.json").read_text(encoding="utf-8"))

    @app.template_filter("info_tags")
    def info_tags(value):
        # Only explicit separators create tags; punctuation within prose is preserved.
        return [part.strip() for line in (value or "").splitlines() for part in line.split(";") if part.strip()]

    status_labels = {"pending": "Enviado", "reviewing": "Em análise", "interview": "Contato / entrevista", "approved": "Aprovado", "rejected": "Não aprovado", "completed": "Finalizado", "available": "Disponível", "adopted": "Adotado", "inactive": "Inativo"}

    @app.template_filter("status_label")
    def status_label(value):
        return status_labels.get(value, value)

    @app.before_request
    def load_logged_user():
        user_id = session.get("user_id")
        g.user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True) if user_id else None

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_upload(error):
        flash("A foto ultrapassa o limite de 5 MB.", "error")
        target = request.endpoint if request.endpoint in ("register", "profile") else "create_animal"
        return redirect(url_for(target)), 413

    def login_required(view):
        @wraps(view)
        def wrapped(**kwargs):
            if g.user is None:
                flash("Faça login para continuar.", "error")
                return redirect(url_for("login", next=request.path))
            return view(**kwargs)
        return wrapped

    def staff_required(view):
        @wraps(view)
        @login_required
        def wrapped(**kwargs):
            if g.user["role"] not in ("ong", "admin"):
                abort(403)
            return view(**kwargs)
        return wrapped

    @app.get("/health")
    def health():
        query_db("SELECT 1")
        return {"status": "ok"}

    @app.route("/")
    def index():
        animals = query_db(
            "SELECT * FROM animals WHERE status = 'available' ORDER BY created_at DESC"
        )
        return render_template("index.html", animals=animals)

    @app.route("/welcome")
    def welcome():
        return render_template("welcome.html")

    @app.route("/explore")
    def explore():
        search = request.args.get("q", "").strip()
        species = request.args.get("species", "").strip()
        size = request.args.get("size", "").strip()
        query = "SELECT * FROM animals WHERE status = 'available'"
        args = []
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            args.extend((f"%{search}%", f"%{search}%"))
        if species in ("Cão", "Gato"):
            query += " AND species = ?"
            args.append(species)
        if size:
            query += " AND size = ?"
            args.append(size)
        filters = {key: request.args.get(key, "").strip() for key in ("sex", "vaccinated", "neutered", "age")}
        for key, value in filters.items():
            if value:
                query += f" AND {key} = ?"
                args.append(value)
        query += " ORDER BY created_at DESC"
        animals = query_db(query, tuple(args))
        return render_template("explore.html", animals=animals, search=search, species=species, size=size, filters=filters)

    @app.route("/register", methods=("GET", "POST"))
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not name or not email or len(password) < 8:
                flash("Informe nome, e-mail e uma senha de pelo menos 8 caracteres.", "error")
            elif query_db("SELECT id FROM users WHERE email = ?", (email,), one=True):
                flash("Este e-mail já está cadastrado.", "error")
            else:
                try:
                    photo_filename = save_photo(request.files.get("photo"))
                except ValueError as error:
                    flash(str(error), "error")
                else:
                    execute_db(
                        "INSERT INTO users (name, email, password_hash, role, photo_filename) VALUES (?, ?, ?, 'adopter', ?)",
                        (name, email, hash_password(password), photo_filename),
                    )
                    flash("Cadastro realizado. Faça login para continuar.", "success")
                    return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
            if not user or not check_password(user["password_hash"], request.form.get("password", "")):
                flash("E-mail ou senha inválidos.", "error")
            else:
                session.clear()
                session["user_id"] = user["id"]
                return redirect(request.args.get("next") or url_for("index"))
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("index"))

    @app.post("/favorites/<int:animal_id>")
    @login_required
    def toggle_favorite(animal_id):
        animal = query_db("SELECT id FROM animals WHERE id = ?", (animal_id,), one=True)
        if animal is None:
            abort(404)
        favorite = query_db(
            "SELECT user_id FROM favorites WHERE user_id = ? AND animal_id = ?",
            (g.user["id"], animal_id), one=True,
        )
        if favorite:
            execute_db("DELETE FROM favorites WHERE user_id = ? AND animal_id = ?", (g.user["id"], animal_id))
            flash("Pet removido dos favoritos.", "success")
        else:
            execute_db("INSERT INTO favorites (user_id, animal_id) VALUES (?, ?)", (g.user["id"], animal_id))
            flash("Pet salvo nos favoritos.", "success")
        return redirect(request.form.get("next") or request.referrer or url_for("index"))

    @app.route("/favorites")
    @login_required
    def favorites():
        animals = query_db(
            """SELECT animals.* FROM animals
               JOIN favorites ON favorites.animal_id = animals.id
               WHERE favorites.user_id = ? ORDER BY favorites.created_at DESC""",
            (g.user["id"],),
        )
        return render_template("favorites.html", animals=animals)

    @app.route("/animal/<int:animal_id>")
    def animal_detail(animal_id):
        animal = query_db("SELECT * FROM animals WHERE id = ?", (animal_id,), one=True)
        if animal is None:
            abort(404)
        return render_template("animal_detail.html", animal=animal)

    @app.route("/adoptions/new/<int:animal_id>", methods=("GET", "POST"))
    @login_required
    def new_adoption(animal_id):
        animal = query_db("SELECT * FROM animals WHERE id = ?", (animal_id,), one=True)
        if animal is None or animal["status"] != "available":
            abort(404)
        if request.method == "POST":
            message = request.form.get("message", "").strip()
            existing = query_db(
                "SELECT id FROM adoptions WHERE animal_id = ? AND adopter_id = ? AND status IN ('pending', 'reviewing', 'interview', 'approved')",
                (animal_id, g.user["id"]), one=True,
            )
            answers = {key: request.form.get(key, "").strip() for key in ("full_name", "phone", "housing", "household", "experience")}
            if not message or not all(answers.values()) or request.form.get("consent") != "on":
                flash("Preencha todas as etapas e confirme o compromisso de adoção responsável.", "error")
            elif existing:
                flash("Você já possui uma solicitação ativa para este animal.", "error")
            else:
                execute_db(
                    "INSERT INTO adoptions (animal_id, adopter_id, message, answers, status) VALUES (?, ?, ?, ?, 'pending')",
                    (animal_id, g.user["id"], message, json.dumps(answers, ensure_ascii=False)),
                )
                flash("Solicitação enviada à ONG.", "success")
                return redirect(url_for("my_adoptions"))
        return render_template("adoption_form.html", animal=animal)

    @app.route("/my-adoptions")
    @login_required
    def my_adoptions():
        adoptions = query_db(
            """SELECT adoptions.*, animals.name AS animal_name
               FROM adoptions JOIN animals ON animals.id = adoptions.animal_id
               WHERE adopter_id = ? ORDER BY adoptions.created_at DESC""",
            (g.user["id"],),
        )
        return render_template("my_adoptions.html", adoptions=adoptions)

    @app.route("/profile", methods=("GET", "POST"))
    @login_required
    def profile():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Informe seu nome.", "error")
            else:
                try:
                    new_photo = save_photo(request.files.get("photo"))
                except ValueError as error:
                    flash(str(error), "error")
                else:
                    old_photo = g.user["photo_filename"]
                    photo_filename = new_photo or old_photo
                    if not new_photo and request.form.get("remove_photo") == "on":
                        photo_filename = None
                    execute_db("UPDATE users SET name = ?, photo_filename = ? WHERE id = ?",
                               (name, photo_filename, g.user["id"]))
                    if old_photo and old_photo != photo_filename:
                        remove_photo(old_photo)
                    flash("Perfil atualizado.", "success")
                    return redirect(url_for("profile"))
        return render_template("profile.html")

    @app.template_filter("donation_status")
    def donation_status(value):
        return STATUSES.get(value, value)

    @app.template_filter("money")
    def money(value):
        return "R$ " + f"{Decimal(str(value)) :,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    @app.route("/donations", methods=("GET", "POST"))
    @login_required
    def donations():
        if request.method == "POST":
            kind = request.form.get("kind", "").strip()
            description = request.form.get("description", "").strip()
            contact = request.form.get("contact", "").strip()
            amount = None
            error = None
            if kind not in KINDS or not description or not contact or len(contact) > 180:
                error = "Informe o tipo, os detalhes e um contato de até 180 caracteres."
            elif kind == "financeira":
                try:
                    amount = Decimal(request.form.get("amount", "").replace(",", "."))
                    if not amount.is_finite() or amount <= 0 or amount > Decimal("99999999.99") or amount != amount.quantize(Decimal("0.01")):
                        raise ValueError()
                except (InvalidOperation, ValueError):
                    error = "Informe um valor positivo, com até duas casas decimais e máximo de R$ 99.999.999,99."
            if error:
                flash(error, "error")
            else:
                donation_id = record_donation(g.user["id"], kind, str(amount) if amount is not None else None, description, contact)
                flash("Contribuição enviada! Aguarde a confirmação da ONG antes de combinar a entrega ou transferência.", "success")
                return redirect(url_for("donation_detail", donation_id=donation_id))
        history = query_db("SELECT * FROM donations WHERE donor_id=? ORDER BY created_at DESC, id DESC", (g.user["id"],))
        return render_template("donations.html", history=history, kinds=KINDS)

    def get_donation(donation_id):
        donation = query_db("""SELECT donations.*, users.name AS donor_name, users.email AS donor_email
            FROM donations JOIN users ON users.id=donations.donor_id WHERE donations.id=?""", (donation_id,), one=True)
        if donation is None:
            abort(404)
        if g.user["role"] not in ("ong", "admin") and donation["donor_id"] != g.user["id"]:
            abort(403)
        return donation

    @app.route("/donations/<int:donation_id>")
    @login_required
    def donation_detail(donation_id):
        donation = get_donation(donation_id)
        events = query_db("SELECT * FROM donation_events WHERE donation_id=? ORDER BY created_at, id", (donation_id,))
        return render_template("donation_detail.html", donation=donation, events=events, kinds=KINDS,
                               transitions=TRANSITIONS.get(donation["status"], ()))

    @app.post("/donations/<int:donation_id>/cancel")
    @login_required
    def cancel_donation(donation_id):
        donation = get_donation(donation_id)
        if donation["donor_id"] != g.user["id"]:
            abort(403)
        if donation["status"] not in ("pending", "accepted", "scheduled"):
            abort(400)
        if not transition_donation(donation, g.user["id"], "cancelled", "Contribuição cancelada pelo doador."):
            abort(409)
        flash("Contribuição cancelada.", "success")
        return redirect(url_for("donation_detail", donation_id=donation_id))

    @app.route("/admin/donations")
    @staff_required
    def admin_donations():
        status = request.args.get("status", "")
        kind = request.args.get("kind", "")
        sql = "SELECT donations.*, users.name AS donor_name FROM donations JOIN users ON users.id=donations.donor_id"
        args, conditions = [], []
        if status in STATUSES:
            conditions.append("donations.status=?")
            args.append(status)
        if kind in KINDS:
            conditions.append("donations.kind=?")
            args.append(kind)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        donations = query_db(sql + " ORDER BY donations.created_at DESC, donations.id DESC", tuple(args))
        return render_template("admin_donations.html", donations=donations, statuses=STATUSES, selected_status=status, selected_kind=kind, kinds=KINDS)

    @app.post("/admin/donations/<int:donation_id>/status")
    @staff_required
    def update_donation(donation_id):
        donation = get_donation(donation_id)
        status = request.form.get("status", "")
        note = request.form.get("note", "").strip()
        if status not in TRANSITIONS.get(donation["status"], ()):
            abort(400)
        if not note:
            flash("Informe as orientações ou o motivo da atualização para o doador.", "error")
        elif transition_donation(donation, g.user["id"], status, note):
            flash("Doação atualizada. O doador já pode acompanhar as orientações.", "success")
        else:
            abort(409)
        return redirect(url_for("donation_detail", donation_id=donation_id))

    @app.post("/adoptions/<int:adoption_id>/feedback")
    @login_required
    def feedback(adoption_id):
        adoption = query_db("SELECT * FROM adoptions WHERE id = ?", (adoption_id,), one=True)
        if adoption is None or adoption["adopter_id"] != g.user["id"] or adoption["status"] != "completed":
            abort(403)
        rating = request.form.get("rating", "5")
        comment = request.form.get("comment", "").strip()
        execute_db(
            "INSERT INTO feedback (adoption_id, rating, comment) VALUES (?, ?, ?)",
            (adoption_id, rating, comment),
        )
        flash("Obrigado pelo feedback.", "success")
        return redirect(url_for("my_adoptions"))

    @app.route("/admin", endpoint="admin_dashboard")
    @staff_required
    def dashboard():
        animals = query_db("SELECT * FROM animals ORDER BY created_at DESC")
        adoptions = query_db(
            """SELECT adoptions.*, animals.name AS animal_name, users.name AS adopter_name
               FROM adoptions JOIN animals ON animals.id = adoptions.animal_id
               JOIN users ON users.id = adoptions.adopter_id
               ORDER BY adoptions.created_at DESC"""
        )
        donations = query_db(
            """SELECT donations.*, users.name AS donor_name
               FROM donations JOIN users ON users.id = donations.donor_id
               ORDER BY donations.created_at DESC"""
        )
        stats = {
            "available": len(query_db("SELECT id FROM animals WHERE status = 'available'")),
            "pending": len(query_db("SELECT id FROM adoptions WHERE status IN ('pending', 'reviewing', 'interview')")),
            "adopted": len(query_db("SELECT id FROM animals WHERE status = 'adopted'")),
            "donations": len(donations),
        }
        donation_summary = {key: {"label": label, "received": 0, "ongoing": 0,
                                  "received_amount": Decimal("0"), "ongoing_amount": Decimal("0")}
                            for key, label in KINDS.items()}
        for donation in donations:
            category = donation_summary.get(donation["kind"])
            if category is None:
                continue
            bucket = "received" if donation["status"] == "received" else "ongoing" if donation["status"] in ("pending", "accepted", "scheduled") else None
            if bucket:
                category[bucket] += 1
                if donation["kind"] == "financeira" and donation["amount"] is not None:
                    category[bucket + "_amount"] += Decimal(str(donation["amount"]))
        animal_status = request.args.get("animal_status", "")
        application_status = request.args.get("application_status", "")
        if animal_status in ("available", "adopted", "inactive"):
            animals = [item for item in animals if item["status"] == animal_status]
        if application_status == "ongoing":
            adoptions = [item for item in adoptions if item["status"] in ("pending", "reviewing", "interview")]
        applications = [dict(item) for item in adoptions]
        for item in applications:
            item["answers_data"] = json.loads(item["answers"] or "{}")
        return render_template("dashboard.html", animals=animals, adoptions=applications, donations=donations, stats=stats, donation_summary=donation_summary, kinds=KINDS, animal_status=animal_status, application_status=application_status)

    @app.route("/admin/animals/new", methods=("GET", "POST"))
    @staff_required
    def create_animal():
        if request.method == "POST":
            fields = [request.form.get(key, "").strip() for key in ("name", "species", "age", "size", "description", "health", "breed", "sex", "vaccinated", "neutered")]
            if not fields[0] or not fields[1]:
                flash("Nome e espécie são obrigatórios.", "error")
            else:
                try:
                    photo_filename = save_photo(request.files.get("photo"))
                    execute_db(
                        """INSERT INTO animals (name, species, age, size, description, health, breed, sex, vaccinated, neutered, photo_filename, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')""",
                        tuple(fields) + (photo_filename,),
                    )
                except ValueError as error:
                    flash(str(error), "error")
                else:
                    flash("Animal cadastrado.", "success")
                    return redirect(url_for("admin_dashboard"))
        return render_template("animal_form.html", animal=None, options=animal_options)

    @app.route("/admin/animals/<int:animal_id>/edit", methods=("GET", "POST"))
    @staff_required
    def edit_animal(animal_id):
        animal = query_db("SELECT * FROM animals WHERE id = ?", (animal_id,), one=True)
        if animal is None:
            abort(404)
        if request.method == "POST":
            fields = [
                request.form.get(key, "").strip()
                for key in ("name", "species", "age", "size", "description", "health", "breed", "sex", "vaccinated", "neutered")
            ]
            status = request.form.get("status", "").strip()
            should_remove_photo = request.form.get("remove_photo") == "on"
            if not fields[0] or not fields[1]:
                flash("Nome e espécie são obrigatórios.", "error")
            elif status not in ("available", "adopted", "inactive"):
                flash("Status inválido.", "error")
            else:
                try:
                    new_photo = save_photo(request.files.get("photo"))
                except ValueError as error:
                    flash(str(error), "error")
                else:
                    photo_filename = animal["photo_filename"]
                    if new_photo:
                        photo_filename = new_photo
                    elif should_remove_photo:
                        photo_filename = None
                    execute_db(
                        """UPDATE animals
                           SET name = ?, species = ?, age = ?, size = ?, description = ?,
                               health = ?, breed = ?, sex = ?, vaccinated = ?, neutered = ?, photo_filename = ?, status = ?
                           WHERE id = ?""",
                        tuple(fields) + (photo_filename, status, animal_id),
                    )
                    if animal["photo_filename"] and animal["photo_filename"] != photo_filename:
                        remove_photo(animal["photo_filename"])
                    flash("Animal atualizado.", "success")
                    return redirect(url_for("admin_dashboard"))
        return render_template("animal_form.html", animal=animal, options=animal_options)

    @app.post("/admin/animals/<int:animal_id>/delete")
    @staff_required
    def delete_animal(animal_id):
        execute_db("UPDATE animals SET status = 'inactive' WHERE id = ?", (animal_id,))
        flash("Animal retirado da divulgação.", "success")
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/adoptions/<int:adoption_id>/status")
    @staff_required
    def update_adoption(adoption_id):
        status = request.form.get("status")
        if status not in ("reviewing", "interview", "approved", "rejected", "completed"):
            abort(400)
        adoption = query_db("SELECT * FROM adoptions WHERE id = ?", (adoption_id,), one=True)
        if adoption is None:
            abort(404)
        execute_db("UPDATE adoptions SET status = ? WHERE id = ?", (status, adoption_id))
        if status == "completed":
            execute_db("UPDATE animals SET status = 'adopted' WHERE id = ?", (adoption["animal_id"],))
        flash("Status da adoção atualizado.", "success")
        return redirect(url_for("admin_dashboard"))

    with app.app_context():
        init_db.callback()
    return app
