from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///groups.db'
db = SQLAlchemy(app)

ADMIN_PASSWORD = "2122"

# ===============================
# Database Model
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
# Student Page
# ===============================
@app.route('/', methods=['GET', 'POST'])
def index():

    popup = False
    taken_group = None

    if request.method == 'POST':

        if Group.query.count() >= 26:
            return "🚫 Maximum 26 Groups Allowed."

        topic = request.form['topic']

        existing = Group.query.filter_by(topic=topic).first()
        if existing:
            popup = True
            taken_group = existing.id
            groups = Group.query.all()
            return render_template(
                'index.html',
                groups=groups,
                popup=popup,
                taken_group=taken_group
            )

        new_group = Group(
            topic=topic,
            m1_name=request.form['m1_name'],
            m1_prn=request.form['m1_prn'],
            m2_name=request.form['m2_name'],
            m2_prn=request.form['m2_prn'],
            m3_name=request.form['m3_name'],
            m3_prn=request.form['m3_prn'],
            m4_name=request.form['m4_name'],
            m4_prn=request.form['m4_prn'],
        )

        db.session.add(new_group)
        db.session.commit()

        return redirect('/')

    groups = Group.query.all()
    return render_template('index.html', groups=groups)
# ===============================
# Admin Login Page
# ===============================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            groups = Group.query.all()
            return render_template('admin.html', groups=groups)
        else:
            return render_template('admin_login.html', error="Wrong Password!")

    return render_template('admin_login.html')


# ===============================
# Excel Download
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

    df = pd.DataFrame(data, columns=[
        "Topic", "Member 1", "Member 2", "Member 3", "Member 4"
    ])

    file_path = "groups.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)


# ===============================
# PDF Download
# ===============================
@app.route('/download_pdf')
def download_pdf():
    file_path = "groups.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)

    groups = Group.query.all()

    data = [["Topic", "Member 1", "Member 2", "Member 3", "Member 4"]]

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
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    doc.build([table])
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
