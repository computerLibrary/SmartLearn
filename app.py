import os
from flask import Flask, request, redirect, url_for, session, render_template_string, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-before-production")
db_url = os.environ.get("DATABASE_URL", "sqlite:///smartlearn.db")
if db_url.startswith("mysql://"):
    db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    level = db.Column(db.String(40), default="Beginner")

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)

PAGE = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>SmartLearn</title><style>
*{box-sizing:border-box}body{margin:0;font:16px Arial;background:#f4f7fb;color:#18243a}header{background:#102b52;color:white;padding:22px 7%;display:flex;justify-content:space-between;align-items:center}a{color:#1769aa;text-decoration:none}.brand{font-size:26px;font-weight:bold;color:white}.nav a{color:white;margin-left:18px}.hero{padding:65px 7%;background:linear-gradient(120deg,#102b52,#1769aa);color:white}.hero h1{font-size:42px;margin:0 0 14px}.wrap{padding:32px 7%;max-width:1200px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}.card,form{background:white;border-radius:14px;padding:22px;box-shadow:0 5px 20px #13294b12}.btn,button{background:#1673bd;color:white;border:0;border-radius:8px;padding:11px 16px;cursor:pointer;display:inline-block}.muted{color:#607089}input{width:100%;padding:12px;margin:7px 0 14px;border:1px solid #ccd5e1;border-radius:7px}footer{padding:24px 7%;color:#607089;text-align:center}
</style></head><body><header><a class="brand" href="/">SmartLearn</a><nav class="nav"><a href="/">Courses</a>{% if user %}<a href="/dashboard">My learning</a><a href="/logout">Log out</a>{% else %}<a href="/login">Log in</a><a href="/register">Register</a>{% endif %}</nav></header>{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="wrap">{{m}}</div>{% endfor %}{% endwith %}{{ body|safe }}<footer>SmartLearn · Learn new skills, build your future.</footer></body></html>"""

def page(body):
    return render_template_string(PAGE, body=body, user=session.get("user"))

@app.route("/")
def home():
    courses=Course.query.order_by(Course.title).all()
    cards="".join(f'<article class="card"><h3>{c.title}</h3><p class="muted">{c.level}</p><p>{c.description}</p><a class="btn" href="/course/{c.id}">Explore course</a></article>' for c in courses)
    body=f'<section class="hero"><h1>Learn without limits.</h1><p>Build practical digital skills with SmartLearn.</p><a class="btn" href="#courses">Explore courses</a></section><main class="wrap" id="courses"><h2>Explore our courses</h2><div class="grid">{cards or "<p>Courses are being prepared. Please check back soon.</p>"}</div></main>'
    return page(body)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip(); email=request.form["email"].lower().strip(); password=request.form["password"]
        if User.query.filter_by(email=email).first(): flash("That email is already registered.")
        else:
            db.session.add(User(name=name,email=email,password=generate_password_hash(password))); db.session.commit(); flash("Account created. Please log in."); return redirect(url_for("login"))
    return page('<main class="wrap"><form method="post"><h2>Create your SmartLearn account</h2><label>Full name</label><input name="name" required><label>Email</label><input name="email" type="email" required><label>Password</label><input name="password" type="password" minlength="8" required><button>Create account</button></form></main>')

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=User.query.filter_by(email=request.form["email"].lower().strip()).first()
        if u and check_password_hash(u.password,request.form["password"]): session["user"]=u.id; return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.")
    return page('<main class="wrap"><form method="post"><h2>Welcome back</h2><label>Email</label><input name="email" type="email" required><label>Password</label><input name="password" type="password" required><button>Log in</button></form></main>')

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if not session.get("user"): return redirect(url_for("login"))
    rows=Enrollment.query.filter_by(user_id=session["user"]).all()
    courses=[Course.query.get(r.course_id) for r in rows]
    body='<main class="wrap"><h2>My learning</h2><div class="grid">'+''.join(f'<article class="card"><h3>{c.title}</h3><a href="/course/{c.id}">Continue learning</a></article>' for c in courses if c)+'</div></main>'
    return page(body)

@app.route("/course/<int:course_id>", methods=["GET","POST"])
def course(course_id):
    c=Course.query.get_or_404(course_id)
    if request.method=="POST":
        if not session.get("user"): return redirect(url_for("login"))
        if not Enrollment.query.filter_by(user_id=session["user"],course_id=c.id).first():
            db.session.add(Enrollment(user_id=session["user"],course_id=c.id)); db.session.commit()
        flash("You are enrolled in this course.")
        return redirect(url_for("dashboard"))
    body=f'<main class="wrap"><article class="card"><p class="muted">{c.level}</p><h1>{c.title}</h1><p>{c.description}</p><form method="post"><button>Enroll in this course</button></form></article></main>'
    return page(body)

with app.app_context():
    db.create_all()
    if Course.query.count()==0:
        starters=[
        ("Computer Fundamentals","Understand computer systems, hardware, software, data representation and basic digital skills.","Beginner"),
        ("Google Docs","Create, format, collaborate on and share professional documents.","Beginner"),
        ("HTML and CSS","Build and style responsive web pages using HTML5 and CSS.","Beginner"),
        ("Database and SQL","Learn relational databases, tables, queries, joins and data management.","Intermediate"),
        ("Python Programming","Develop programming skills using Python fundamentals and practical exercises.","Beginner"),
        ("Computer Networking","Explore network devices, protocols, addressing and network security.","Intermediate"),
        ("Google Sheets","Work with spreadsheets, formulas, functions, charts and data analysis.","Beginner")]
        db.session.add_all([Course(title=t,description=d,level=l) for t,d,l in starters]); db.session.commit()

@app.get("/health")
def health(): return {"status":"ok","app":"SmartLearn"}

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
