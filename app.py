from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.platypus import SimpleDocTemplate, Table
import qrcode
import os
import io

app = Flask(__name__)
app.secret_key = "secret123"

DB_NAME = "database.db"

# 🔐 SÉCURITÉ LOGIN
login_attempts = {}

# =========================
# 📦 INIT DATABASE
# =========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reclamations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        telephone TEXT,
        type TEXT,
        service TEXT,
        message TEXT,
        reponse TEXT,
        urgence TEXT,
        date TEXT,
        statut TEXT DEFAULT 'En attente'
    )
    """)

    # ADMIN
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        password_hash = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", password_hash)
        )

    conn.commit()
    conn.close()


# =========================
# 🔥 UPDATE DB
# =========================
def update_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE reclamations ADD COLUMN reponse TEXT")
    except:
        pass

    conn.commit()
    conn.close()


# =========================
# 📲 QR CODE (PRO VERSION)
# =========================
@app.route("/qr")
def generate_qr():
    # 🔥 URL automatique (Render ou local)
    url = request.host_url.rstrip("/")

    # Génération QR en mémoire (plus pro)
    img = qrcode.make(url)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png", as_attachment=True, download_name="qr_reclamation.png")


# =========================
# 🔐 LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in login_attempts and login_attempts[username] >= 3:
            return render_template("login.html", error="Compte bloqué temporairement")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("SELECT password FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user[0], password):
            session["logged_in"] = True
            login_attempts[username] = 0
            return redirect("/admin")
        else:
            login_attempts[username] = login_attempts.get(username, 0) + 1
            return render_template("login.html", error="Identifiants incorrects")

    return render_template("login.html")


# =========================
# 🚪 LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect("/login")


# =========================
# 🌐 FORMULAIRE
# =========================
@app.route("/")
def form():
    return render_template("form.html")


# =========================
# 📩 SOUMISSION
# =========================
@app.route("/submit", methods=["POST"])
def submit():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reclamations (nom, telephone, type, service, message, urgence, date)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        request.form.get("nom"),
        request.form.get("telephone"),
        request.form.get("type"),
        request.form.get("service"),
        request.form.get("message"),
        request.form.get("urgence"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return redirect("/")


# =========================
# 🤖 RÉPONSE AUTO
# =========================
@app.route("/reply/<int:id>")
def reply(id):
    if not session.get("logged_in"):
        return redirect("/login")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT message FROM reclamations WHERE id=?", (id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return redirect("/admin")

    message = result[0] or ""
    msg = message.lower()

    if "retard" in msg:
        reponse = "Votre demande a été prise en compte. Nous traitons le retard signalé."
    elif "erreur" in msg:
        reponse = "Votre demande a été prise en compte. Une vérification est en cours."
    elif "résultat" in msg or "note" in msg:
        reponse = "Votre demande a été prise en compte. Les résultats sont en cours de traitement."
    elif "paiement" in msg:
        reponse = "Votre demande a été prise en compte. Le service financier vérifie votre situation."
    else:
        reponse = "Votre demande a été prise en compte avec succès. Merci pour votre confiance."

    cursor.execute("""
        UPDATE reclamations
        SET reponse=?, statut='Traité'
        WHERE id=?
    """, (reponse, id))

    conn.commit()
    conn.close()

    return redirect("/admin")


# =========================
# 📊 DASHBOARD
# =========================
@app.route("/admin")
def admin():
    if not session.get("logged_in"):
        return redirect("/login")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM reclamations")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reclamations WHERE statut='En attente'")
    attente = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reclamations WHERE statut='En cours'")
    encours = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reclamations WHERE statut='Traité'")
    traite = cursor.fetchone()[0]

    cursor.execute("""
    SELECT date(date), COUNT(*)
    FROM reclamations
    GROUP BY date(date)
    ORDER BY date(date)
    """)
    evolution = cursor.fetchall()
    dates = [row[0] for row in evolution]
    counts = [row[1] for row in evolution]

    cursor.execute("""
    SELECT strftime('%Y-%m', date), COUNT(*)
    FROM reclamations
    GROUP BY 1
    ORDER BY 1
    """)
    monthly = cursor.fetchall()
    months = [row[0] for row in monthly]
    monthly_counts = [row[1] for row in monthly]

    cursor.execute("SELECT * FROM reclamations ORDER BY id DESC")
    data = cursor.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        reclamations=data,
        total=total,
        attente=attente,
        encours=encours,
        traite=traite,
        dates=dates,
        counts=counts,
        months=months,
        monthly_counts=monthly_counts
    )


# =========================
# 🚀 RUN (PRODUCTION READY)
# =========================
if __name__ == "__main__":
    init_db()
    update_db()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)