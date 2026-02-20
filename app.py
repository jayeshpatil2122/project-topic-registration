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
    print("Using PostgreSQL database")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///groups.db'
    print("Using SQLite database")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ADMIN_PASSWORD = "1353"

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
    return re.sub(r'\s+', '', text.lower())

def clean_words(text):
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    return set(text.split())

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
    existing_groups = Group.query.all()

    if request.method == 'POST':

        if Group.query.count() >= 26:
            return "🚫 Maximum 26 Groups Allowed."

        topic = request.form['topic'].strip()

        # ===============================
        # CHECK DUPLICATE TOPIC
        # ===============================
        for g in existing_groups:
            if topics_similar(topic, g.topic):
                popup = "duplicate_topic"
                message = f"Topic already selected by Group #{g.id}"
                return render_template(
                    'index.html',
                    groups=existing_groups,
                    popup=popup,
                    message=message
                )

        # ===============================
        # COLLECT MEMBERS (1–4)
        # ===============================
        members = []

        for i in range(1, 5):
            name = request.form.get(f'm{i}_name', '').strip()
            prn = request.form.get(f'm{i}_prn', '').strip()

            if name and prn:
                members.append((name, prn))

        if len(members) == 0:
            popup = "invalid_group"
            message = "At least 1 member required."
            return render_template(
                'index.html',
                groups=existing_groups,
                popup=popup,
                message=message
            )

        # ===============================
        # PRN VALIDATION (12 digits)
        # ===============================
        for name, prn in members:
            if not prn.isdigit() or len(prn) != 12:
                popup = "invalid_prn"
                message = f"PRN {prn} must be exactly 12 digits."
                return render_template(
                    'index.html',
                    groups=existing_groups,
                    popup=popup,
                    message=message
                )

        # ===============================
        # CHECK DUPLICATE MEMBERS
        # ===============================
        for g in existing_groups:

            existing_names = [g.m1_name, g.m2_name, g.m3_name, g.m4_name]
            existing_prns = [g.m1_prn, g.m2_prn, g.m3_prn, g.m4_prn]

            for name, prn in members:

                if clean_text(prn) in [clean_text(p) for p in existing_prns if p]:
                    popup = "duplicate_user"
                    message = f"PRN {prn} already in Group #{g.id}"
                    return render_template(
                        'index.html',
                        groups=existing_groups,
                        popup=popup,
                        message=message
                    )

                if clean_text(name) in [clean_text(n) for n in existing_names if n]:
                    popup = "duplicate_user"
                    message = f"{name} already in Group #{g.id}"
                    return render_template(
                        'index.html',
                        groups=existing_groups,
                        popup=popup,
                        message=message
                    )

        # ===============================
        # SAVE GROUP
        # ===============================
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

    # ===============================
    # PREDEFINED TOPICS
    # ===============================
    all_topics = [
        "Smart Irrigation System",
        "Automatic Street Light",
        "Temperature Monitoring System",
        "Smart Parking System",
        "Home Automation using Arduino",
        "RFID Attendance System",
        "Fire Detection System",
        "Clap Switch",
        "Digital Voltmeter",
        "Smart Dustbin",
        "Obstacle Avoiding Robot",
        "Water Level Indicator",
        "Gas Leakage Detection",
        "Smart Traffic Control",
        "Heart Rate Monitor",
        "Weather Monitoring System",
        "Smart Energy Meter",
        "Voice Controlled Robot",
        "Automatic Plant Watering",
        "Solar Tracking System"
    ]

    submitted_topics = [g.topic.lower() for g in existing_groups]

    return render_template(
        'index.html',
        groups=existing_groups,
        popup=popup,
        message=message,
        all_topics=all_topics,
        submitted_topics=submitted_topics
    )


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
# EDIT GROUP
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
# DELETE GROUP
# ===============================
@app.route('/delete/<int:group_id>', methods=['POST'])
def delete_group(group_id):

    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()

    return redirect('/admin')


# ===============================
# DOWNLOAD EXCEL (FIXED VERSION)
# ===============================
@app.route('/download_excel')
def download_excel():

    groups = Group.query.all()

    data = []

    for g in groups:
        data.append([
            g.topic or "",
            f"{g.m1_name or ''}\n{g.m1_prn or ''}",
            f"{g.m2_name or ''}\n{g.m2_prn or ''}",
            f"{g.m3_name or ''}\n{g.m3_prn or ''}",
            f"{g.m4_name or ''}\n{g.m4_prn or ''}"
        ])

    df = pd.DataFrame(
        data,
        columns=["Topic","Member 1","Member 2","Member 3","Member 4"]
    )

    file_path = "groups.xlsx"

    # IMPORTANT: force openpyxl engine
    df.to_excel(file_path, index=False, engine="openpyxl")

    return send_file(
        file_path,
        as_attachment=True,
        download_name="groups.xlsx"
    )



# ===============================
# DOWNLOAD PDF (FIXED FORMAT)
# ===============================
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

@app.route('/download_pdf')
def download_pdf():

    file_path = "groups.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)

    groups = Group.query.all()

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]

    data = []

    # HEADER ROW
    data.append([
        Paragraph("<b>Topic</b>", normal_style),
        Paragraph("<b>Member 1</b>", normal_style),
        Paragraph("<b>Member 2</b>", normal_style),
        Paragraph("<b>Member 3</b>", normal_style),
        Paragraph("<b>Member 4</b>", normal_style),
    ])

    # FORMAT MEMBER (Name on top, PRN below)
    def format_member(name, prn):
        if not name:
            return ""
        return Paragraph(f"{name}<br/>{prn}", normal_style)

    # ADD DATA ROWS
    for g in groups:
        data.append([
            Paragraph(g.topic or "", normal_style),
            format_member(g.m1_name, g.m1_prn),
            format_member(g.m2_name, g.m2_prn),
            format_member(g.m3_name, g.m3_prn),
            format_member(g.m4_name, g.m4_prn),
        ])

    # FIX COLUMN WIDTHS (IMPORTANT)
    table = Table(
        data,
        colWidths=[1.2*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch]
    )

    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),5),
        ('RIGHTPADDING',(0,0),(-1,-1),5),
    ]))

    doc.build([table])

    return send_file(file_path, as_attachment=True)



if __name__ == "__main__":
    app.run(debug=True)
