from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

DB_NAME = "database.db"


# =========================
# 📦 INIT DATABASE
# =========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reclamations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        type TEXT,
        service TEXT,
        message TEXT,
        urgence TEXT,
        reponse TEXT,
        date TEXT,
        statut TEXT DEFAULT 'En attente'
    )
    """)

    conn.commit()
    conn.close()


# =========================
# 🔥 CORRECTION DB (évite erreur)
# =========================
def update_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE reclamations ADD COLUMN reponse TEXT")
    except:
        pass  # colonne déjà existante

    conn.commit()
    conn.close()


# =========================
# 🌐 ROUTE FORMULAIRE
# =========================
@app.route("/")
def form():
    return render_template("form.html")


# =========================
# 🤖 GÉNÉRATION RÉPONSE AUTO
# =========================
def generate_auto_reply(message):
    msg = message.lower()

    if "retard" in msg:
        return "Votre demande a été prise en compte. Nous traitons le retard signalé."
    elif "erreur" in msg:
        return "Votre demande a été prise en compte. Une vérification est en cours."
    elif "note" in msg or "résultat" in msg:
        return "Votre demande a été prise en compte. Les résultats sont en cours de traitement."
    else:
        return "Votre demande a été prise en compte avec succès. Merci pour votre confiance."


# =========================
# 📩 SOUMISSION FORMULAIRE
# =========================
@app.route("/submit", methods=["POST"])
def submit():
    nom = request.form.get("nom")
    type_personne = request.form.get("type")
    service = request.form.get("service")
    message = request.form.get("message")
    urgence = request.form.get("urgence")

    # 🔥 réponse automatique immédiate
    reponse_auto = generate_auto_reply(message)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reclamations (nom, type, service, message, urgence, reponse, date, statut)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nom,
        type_personne,
        service,
        message,
        urgence,
        reponse_auto,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Traité"  # 🔥 directement traité
    ))

    conn.commit()
    conn.close()

    return redirect("/")


# =========================
# 🚀 RUN
# =========================
if __name__ == "__main__":
    init_db()
    update_db()  # 🔥 IMPORTANT (corrige ton erreur)
    app.run(host="0.0.0.0", port=5000, debug=True)