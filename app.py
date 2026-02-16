from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import os
import re

app = Flask(__name__)

# ===============================
# DATABASE CONFIG
# ===============================
database_url = os.environ.get("DATABASE_URL")

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///groups.db'

db = SQLAlchemy(app)

ADMIN_PASSWORD = "2122"

# ===============================
# MODEL
# ===============================
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), unique=True)

    m1_name = db.Column(db.String(100))
    m1_prn = db.Column(db.String(100))

    m2_name = db.Column(db.String(100))
    m2_prn = db.Column(db.String(100))

    m3_name = db.Column(db.String(100))
    m3_prn = db.Column(db.String(100))

    m4_name = db.Column(db.String(100))
    m4_prn = db.Column(db.String(100))

# ===============================
# HELPER FUNCTIONS
# ===============================

def clean_text(text):
    return re.sub(r'\s+', '', text.lower())

def clean_words(text):
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    words = text.split()
    return set(words)

def topics_similar(topic1, topic2):
    words1 = clean_words(topic1)
    words2 = clean_words(topic2)

    if not words1 or not words2:
        return False

    common = words1.intersection(words2)
    similarity_ratio = len(common) / min(len(words1), len(words2))
    return similarity_ratio >= 0.7

# ===============================
# STUDENT PAGE
# ===============================
@app.route('/', methods=['GET', 'POST'])
def index():

    popup = None
    message = None

    if request.method == 'POST':

        if Group.query.count() >= 26:
            return "🚫 Maximum 26 Groups Allowed."

        topic = request.form['topic'].strip()

        # ===============================
        # CHECK TOPIC DUPLICATE
        # ===============================
        existing_groups = Group.query.all()

        for g in existing_groups:
            if topics_similar(topic, g.topic):
                popup = "duplicate_topic"
                message = f"Topic already selected by Group #{g.id}"
                return render_template('index.html',
                                       groups=existing_groups,
                                       popup=popup,
                                       message=message)

        # ===============================
        # CHECK MEMBER DUPLICATE
        # ===============================
        members = []

        for i in range(1, 5):
            name = request.form[f'm{i}_name'].strip()
            prn = request.form[f'm{i}_prn'].strip()
            members.append((name, prn))

        for g in existing_groups:
            for name, prn in members:

                existing_names = [
                    g.m1_name, g.m2_name, g.m3_name, g.m4_name
                ]
                existing_prns = [
                    g.m1_prn, g.m2_prn, g.m3_prn, g.m4_prn
                ]

                if clean_text(prn) in [clean_text(p) for p in existing_prns]:
                    popup = "duplicate_user"
                    message = f"User with PRN {prn} is already in Group #{g.id}"
                    return render_template('index.html',
                                           groups=existing_groups,
                                           popup=popup,
                                           message=message)

                if clean_text(name) in [clean_text(n) for n in existing_names]:
                    popup = "duplicate_user"
                    message = f"{name} is already in Group #{g.id}"
                    return render_template('index.html',
                                           groups=existing_groups,
                                           popup=popup,
                                           message=message)

        # ===============================
        # SAVE GROUP
        # ===============================
        new_group = Group(
            topic=topic,
            m1_name=members[0][0], m1_prn=members[0][1],
            m2_name=members[1][0], m2_prn=members[1][1],
            m3_name=members[2][0], m3_prn=members[2][1],
            m4_name=members[3][0], m4_prn=members[3][1],
        )

        db.session.add(new_group)
        db.session.commit()

        return redirect('/')

    groups = Group.query.all()
    return render_template('index.html', groups=groups)

# ===============================
# ADMIN LOGIN
# ===============================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            groups = Group.query.all()
            return render_template('admin.html', groups=groups)
        else:
            return render_template('admin_login.html', error="Wrong Password!")

    return render_template('admin_login.html')

# ===============================
# EDIT GROUP (ADMIN)
# ===============================
@app.route('/edit/<int:group_id>', methods=['GET', 'POST'])
def edit_group(group_id):

    group = Group.query.get_or_404(group_id)

    if request.method == 'POST':

        group.topic = request.form['topic']

        group.m1_name = request.form['m1_name']
        group.m1_prn = request.form['m1_prn']

        group.m2_name = request.form['m2_name']
        group.m2_prn = request.form['m2_prn']

        group.m3_name = request.form['m3_name']
        group.m3_prn = request.form['m3_prn']

        group.m4_name = request.form['m4_name']
        group.m4_prn = request.form['m4_prn']

        db.session.commit()

        return redirect('/admin')

    return render_template('edit_group.html', group=group)


# ===============================
# FILE DOWNLOADS
# ===============================
@app.route('/download_excel')
def download_excel():
    groups = Group.query.all()
    data = []

    for g in groups:
        data.append([
            g.topic,
            f"{g.m1_name} ({g.m1_prn})",
            f"{g.m2_name} ({g.m2_prn})",
            f"{g.m3_name} ({g.m3_prn})",
            f"{g.m4_name} ({g.m4_prn})"
        ])

    df = pd.DataFrame(data, columns=["Topic","Member 1","Member 2","Member 3","Member 4"])
    file_path = "groups.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

@app.route('/download_pdf')
def download_pdf():
    file_path = "groups.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)

    groups = Group.query.all()

    data = [["Topic","Member 1","Member 2","Member 3","Member 4"]]

    for g in groups:
        data.append([
            g.topic,
            f"{g.m1_name} ({g.m1_prn})",
            f"{g.m2_name} ({g.m2_prn})",
            f"{g.m3_name} ({g.m3_prn})",
            f"{g.m4_name} ({g.m4_prn})"
        ])

    table = Table(data)
    table.setStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ])

    doc.build([table])
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
