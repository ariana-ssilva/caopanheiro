"""Estados e gravações atômicas do fluxo de contribuições."""
from .db import get_db, adapt_sql, insert_row

KINDS = {'financeira': 'Financeira', 'alimentos': 'Alimentos', 'medicamentos': 'Medicamentos', 'materiais': 'Materiais de limpeza'}
STATUSES = {'pending': 'Aguardando análise', 'accepted': 'Aceita pela ONG', 'scheduled': 'Entrega combinada', 'received': 'Recebida', 'declined': 'Não aceita', 'cancelled': 'Cancelada'}
TRANSITIONS = {'pending': ('accepted', 'declined'), 'accepted': ('scheduled', 'received', 'declined'), 'scheduled': ('received', 'declined'), 'received': (), 'declined': (), 'cancelled': ()}


def record_donation(donor_id, kind, amount, description, contact):
    db = get_db()
    cursor = db.cursor()
    def run(sql, args):
        cursor.execute(adapt_sql(sql), args)
    try:
        donation_id = insert_row(cursor, "INSERT INTO donations (donor_id,kind,amount,description,contact,status) VALUES (?,?,?,?,?,'pending')", (donor_id, kind, amount, description, contact))
        run("INSERT INTO donation_events (donation_id,actor_id,status,note) VALUES (?,?,'pending',?)", (donation_id, donor_id, 'Contribuição enviada para avaliação da ONG.'))
        db.commit()
        return donation_id
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


def transition_donation(donation, actor_id, status, note):
    db = get_db()
    cursor = db.cursor()
    def run(sql, args):
        cursor.execute(adapt_sql(sql), args)
    try:
        run("UPDATE donations SET status=? WHERE id=? AND status=?", (status, donation['id'], donation['status']))
        if cursor.rowcount != 1:
            db.rollback()
            return False
        run("INSERT INTO donation_events (donation_id,actor_id,status,note) VALUES (?,?,?,?)", (donation['id'], actor_id, status, note))
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()
