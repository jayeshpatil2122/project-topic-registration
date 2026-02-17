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
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///groups.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ADMIN_PASSWORD = "2122"

# ===============================
# MODEL
# ===============================
class Group(db.Model):
    __tablename__ = "groups"

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


with app.app_context():
    db.create_all()

# ===============================
# HELPER FUNCTIONS
# ===============================
def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', '', text.lower())

def clean_words(text):
    if not text:
        return set()
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    return set(text.split())

def topics_similar(t1, t2):
    w1 = clean_words(t1)
    w2 = clean_words(t2)

    if not w1 or not w2:
        return False

    common = w1.intersection(w2)
    similarity = len(common) / min(len(w1), len(w2))
    return similarity >= 0.7


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
        existing_groups = Group.query.all()

        # ---- CHECK DUPLICATE TOPIC ----
        for g in existing_groups:
            if topics_similar(topic, g.topic):
                popup = "duplicate_topic"
                message = f"Topic already selected by Group #{g.id}"
                return render_template('index.html',
                                       groups=existing_groups,
                                       popup=popup,
                                       message=message)

        # ---- COLLECT MEMBERS (ONLY FILLED ONES) ----
        members = []
        for i in range(1, 5):
            name = request.form.get(f'm{i}_name', '').strip()
            prn = request.form.get(f'm{i}_prn', '').strip()

            if name and prn:
                members.append((name, prn))

        if len(members) == 0:
            popup = "invalid_group"
            message = "At least 1 member required"
            return render_template('index.html',
                                   groups=existing_groups,
                                   popup=popup,
                                   message=message)

        # ---- PRN VALIDATION ----
        for name, prn in members:
            if not prn.isdigit() or len(prn) != 12:
                popup = "invalid_prn"
                message = f"PRN {prn} must be exactly 12 digits"
                return render_template('index.html',
                                       groups=existing_groups,
                                       popup=popup,
                                       message=message)

        # ---- CHECK DUPLICATE MEMBERS ----
        for g in existing_groups:

            existing_names = [g.m1_name, g.m2_name, g.m3_name, g.m4_name]
            existing_prns = [g.m1_prn, g.m2_prn, g.m3_prn, g.m4_prn]

            for name, prn in members:

                if clean_text(prn) in [clean_text(p) for p in existing_prns if p]:
                    popup = "duplicate_user"
                    message = f"PRN {prn} already in Group #{g.id}"
                    return render_template('index.html',
                                           groups=existing_groups,
                                           popup=popup,
                                           message=message)

                if clean_text(name) in [clean_text(n) for n in existing_names if n]:
                    popup = "duplicate_user"
                    message = f"{name} already in Group #{g.id}"
                    return render_template('index.html',
                                           groups=existing_groups,
                                           popup=popup,
                                           message=message)

        # ---- SAVE (DYNAMIC MEMBERS) ----
        new_group = Group(topic=topic)

        if len(members) >= 1:
            new_group.m1_name, new_group.m1_prn = members[0]
        if len(members) >= 2:
            new_group.m2_name, new_group.m2_prn = members[1]
        if len(members) >= 3:
            new_group.m3_name, new_group.m3_prn = members[2]
        if len(members) >= 4:
            new_group.m4_name, new_group.m4_prn = members[3]

        db.session.add(new_group)
        db.session.commit()

        return redirect('/')

    groups = Group.query.all()
    return render_template('index.html', groups=groups)


# ===============================
# ADMIN PANEL
# ===============================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            groups = Group.query.all()
            return render_template('admin.html', groups=groups)
        else:
            return "Wrong Password"

    return render_template('admin_login.html')


# ===============================
# DELETE GROUP
# ===============================
@app.route('/delete/<int:group_id>')
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    return redirect('/admin')


# ===============================
# DOWNLOAD EXCEL
# ===============================
@app.route('/download_excel')
def download_excel():
    groups = Group.query.all()
    data = []

    for g in groups:
        data.append([
            g.topic,
            f"{g.m1_name or ''} ({g.m1_prn or ''})",
            f"{g.m2_name or ''} ({g.m2_prn or ''})",
            f"{g.m3_name or ''} ({g.m3_prn or ''})",
            f"{g.m4_name or ''} ({g.m4_prn or ''})"
        ])

    df = pd.DataFrame(data, columns=["Topic","Member 1","Member 2","Member 3","Member 4"])
    file_path = "groups.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)


# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    app.run()
