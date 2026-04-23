from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import pandas as pd
import json

app = Flask(__name__)

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
        "participation_dist": df['participation'].tolist() if 'participation' in df else []
    }

    return render_template(
        'resultats.html', 
        data=df.values.tolist(), 
        stats=stats, 
        chart_data=json.dumps(chart_data)
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


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
