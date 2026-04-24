from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import pandas as pd
import json
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import random
import os

app = Flask(__name__)

# --- CONFIGURATION DES APIS ---
# Remplacez par vos propres clés API
GEMINI_API_KEY = "AIzaSyD9e8lCQq5bJntfRvBHsSkN8AU1sJZGLEg" 
SCRAPING_API_KEY = "VOTRE_CLE_SCRAPING" # Ex: ScrapingAnt, ScrapingDog, etc.

if GEMINI_API_KEY != "VOTRE_CLE_GEMINI":
    genai.configure(api_key=GEMINI_API_KEY)

def init_db():
    '''
    Initialisation de la base de données avec les nouvelles variables.
    '''
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            sexe TEXT,
            ville TEXT,
            niveau TEXT,
            filiere TEXT NOT NULL,
            moyenne REAL NOT NULL, 
            temps REAL NOT NULL,
            age INTEGER NOT NULL,
            participation INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# ROUTE 1: Accueil
@app.route('/')
def accueil():
    """ Affiche la page d'accueil simple """
    return render_template('accueil.html')

# ROUTE 2: Ici Je collecte mes donnees
@app.route('/collecte')
def collecte():
    """ Affiche le formulaire d'ajout ou de modification """
    edit_id = request.args.get('edit_id')
    edit_student = None

    if edit_id:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE id=?", (edit_id,))
        raw_student = cursor.fetchone()
        conn.close()
        
        if raw_student:
            edit_student = {
                'id': raw_student[0], 'nom': raw_student[1], 'prenom': raw_student[2],
                'sexe': raw_student[3], 'ville': raw_student[4], 'niveau': raw_student[5],
                'filiere': raw_student[6], 'moyenne': raw_student[7], 
                'temps': raw_student[8], 'age': raw_student[9], 'participation': raw_student[10]
            }

    return render_template('collecte.html', edit_student=edit_student)

# ROUTE 3: Mes resultats analyses
@app.route('/resultats')
def resultats():
    """ Affiche les statistiques, graphiques et la base de données complète """
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT * FROM students", conn)
    conn.close()

    if df.empty:
        return render_template('resultats.html', data=[], stats={}, chart_data="{}")

    # ANALYSE DESCRIPTIVE AMÉLIORÉE
    try:
        stats = {
            "total_etudiants": len(df),
            "moyenne_generale": round(df["moyenne"].mean(), 2),
            "age_moyen": round(df["age"].mean(), 2),
            "temps_etude_moyen": round(df["temps"].mean(), 2),
            "participation_moyenne": round(df["participation"].mean(), 2) if "participation" in df else 0,
            "meilleure_moyenne": round(df["moyenne"].max(), 2),
            "pire_moyenne": round(df["moyenne"].min(), 2),
            "sexe_ratio": df['sexe'].value_counts().to_dict() if 'sexe' in df else {}
        }
    except Exception as e:
        print(f"Erreur stats: {e}")
        stats = {} 
        
    # ---- DONNÉES GRAPHIQUES POUR Chart.js ----
    chart_data = {
        "filieres": df['filiere'].value_counts().to_dict(),
        "niveaux": df['niveau'].value_counts().to_dict() if 'niveau' in df else {},
        "temps_vs_moyenne": [{"x": row['temps'], "y": row['moyenne']} for index, row in df.iterrows()],
        "participation_dist": df['participation'].tolist() if 'participation' in df else [],
        "age_moyenne": df.groupby('age')['moyenne'].mean().to_dict()
    }

    # ---- ANALYSE IA VIA API (GEMINI) ----
    ai_analysis = {
        "summary": "Chargement...",
        "risks": "Chargement...",
        "recommendations": "Chargement..."
    }

    try:
        if GEMINI_API_KEY != "Votre ":
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""
            Analyse ces statistiques d'étudiants : {stats}.
            Donne moi 3 parties : 
            1. Un résumé des performances (max 50 mots).
            2. Les risques potentiels identifiés.
            3. 3 recommandations concrètes.
            Réponds uniquement au format JSON avec les clés 'summary', 'risks', 'recommendations'.
            Utilise du HTML léger (<strong>, etc.) pour la mise en forme.
            """
            response = model.generate_content(prompt)
            # Nettoyage JSON
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            ai_analysis = json.loads(clean_text)
        else:
            # Fallback Dynamique
            ai_analysis = {
                "summary": f"La filière <strong>{top_filiere}</strong> domine avec {top_avg}/20. (Mode Démo sans API)",
                "risks": "Risque d'échec élevé pour les étudiants ayant peu de temps d'étude.",
                "recommendations": "Plan d'urgence : Mise en place d'un tutorat pour les niveaux L1."
            }
    except Exception as e:
        print(f"Erreur API Gemini: {e}")

    return render_template(
        'resultats.html', 
        data=df.values.tolist(), 
        stats=stats, 
        chart_data=json.dumps(chart_data),
        ai_analysis=json.dumps(ai_analysis)
    )

# ROUTE 4: (C)reate - Ajouter un étudiant (POST)
@app.route('/add', methods=["POST"])
def add_student():
    """ Ajoute un nouvel étudiant et redirige vers les résultats """
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    sexe = request.form["sexe"]
    ville = request.form["ville"]
    niveau = request.form["niveau"]
    filiere = request.form["filiere"]
    moyenne = float(request.form["moyenne"].replace(',', '.'))
    temps = float(request.form["temps_etude"].replace(',', '.'))
    age = int(request.form["age"])
    participation = int(request.form["participation"])

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO students (nom, prenom, sexe, ville, niveau, filiere, moyenne, temps, age, participation) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (nom, prenom, sexe, ville, niveau, filiere, moyenne, temps, age, participation))
    conn.commit()
    conn.close()

    return redirect(url_for('resultats'))

# ROUTE 5: (U)pdate - Valider la mise à jour (POST)
@app.route('/update/<int:id>', methods=["POST"])
def update_student(id):
    """ Met à jour l'étudiant N° id puis redirige vers résultats """
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    sexe = request.form["sexe"]
    ville = request.form["ville"]
    niveau = request.form["niveau"]
    filiere = request.form["filiere"]
    moyenne = float(request.form["moyenne"].replace(',', '.'))
    temps = float(request.form["temps_etude"].replace(',', '.'))
    age = int(request.form["age"])
    participation = int(request.form["participation"])

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE students
        SET nom=?, prenom=?, sexe=?, ville=?, niveau=?, filiere=?, moyenne=?, temps=?, age=?, participation=?
        WHERE id=?
    ''', (nom, prenom, sexe, ville, niveau, filiere, moyenne, temps, age, participation, id))
    conn.commit()
    conn.close()

    return redirect(url_for('resultats'))

# ROUTE 6: Ici je supprime mes donnees
@app.route('/delete/<int:id>')
def delete_student(id):
    """ Supprime l'étudiant via son ID puis redirige vers résultats """
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('resultats'))


# ROUTE 7: Web Scrapper (Via Scraping API)
@app.route('/scrapper', methods=["POST"])
def scrapper():
    url_cible = request.form.get("url")
    try:
        # APPEL À UNE API DE SCRAPPING (Exemple structurel)
        # On utilise ScrapingAnt ou équivalent si la clé est fournie
        if SCRAPING_API_KEY != "VOTRE_CLE_SCRAPING":
            api_url = f"https://api.scrapingant.com/v2/general?url={url_cible}&x-api-key={SCRAPING_API_KEY}"
            response = requests.get(api_url)
            data = response.json()
            html_content = data.get('content')
        else:
            # Simulation si pas de clé API
            response = requests.get(url_cible)
            html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Logique d'extraction (Simulation de parsing d'une table)
        new_students = [
            ("Lovelace", "Ada", "Femme", "Londres", "M2", "Algorithmique", 19.5, 20, 36, 95),
            ("Turing", "Alan", "Homme", "Bletchley", "Doc", "Cryptographie", 18.0, 18, 41, 98)
        ]

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        for s in new_students:
            cursor.execute('''
                INSERT INTO students (nom, prenom, sexe, ville, niveau, filiere, moyenne, temps, age, participation) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', s)
        conn.commit()
        conn.close()
        return redirect(url_for('resultats'))
    except Exception as e:
        return f"Erreur de scrapping API : {e}"

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
