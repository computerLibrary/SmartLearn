import os
from datetime import datetime
from flask import Flask, request, redirect, url_for, flash, render_template_string, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-secret-before-production")
db_url = os.getenv("DATABASE_URL", "sqlite:///smartlearn.db")
if db_url.startswith("mysql://"): db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

enrolments = db.Table("enrolments",
 db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
 db.Column("course_id", db.Integer, db.ForeignKey("course.id"), primary_key=True))

class User(UserMixin, db.Model):
 id=db.Column(db.Integer,primary_key=True)
 name=db.Column(db.String(100),nullable=False)
 email=db.Column(db.String(150),unique=True,nullable=False)
 password_hash=db.Column(db.String(255),nullable=False)
 courses=db.relationship("Course",secondary=enrolments,backref="students")
 def set_password(self,p): self.password_hash=generate_password_hash(p)
 def check_password(self,p): return check_password_hash(self.password_hash,p)

class Course(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 title=db.Column(db.String(160),nullable=False)
 category=db.Column(db.String(80),default="ICT")
 description=db.Column(db.Text,default="")
 level=db.Column(db.String(40),default="Beginner")
 lessons=db.relationship("Lesson",backref="course",cascade="all, delete-orphan")

class Lesson(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 course_id=db.Column(db.Integer,db.ForeignKey("course.id"),nullable=False)
 title=db.Column(db.String(160),nullable=False)
 content=db.Column(db.Text,default="")
 position=db.Column(db.Integer,default=1)

@login_manager.user_loader
def load_user(uid): return db.session.get(User,int(uid))

BASE="""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{title}} | SmartLearn</title><style>
*{box-sizing:border-box}body{margin:0;font:16px Arial,sans-serif;background:#f4f7fb;color:#172033}
nav{background:#102a43;color:white;padding:18px max(5%,calc((100% - 1100px)/2));display:flex;gap:22px;align-items:center;flex-wrap:wrap}
nav a{color:white;text-decoration:none}.brand{font-size:23px;font-weight:bold;margin-right:auto}
main{max-width:1100px;margin:38px auto;padding:0 20px}.hero{background:linear-gradient(120deg,#0f766e,#164e63);color:white;padding:42px;border-radius:18px}
h1{font-size:34px;margin-top:0}.muted{color:#64748b}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}
.card{background:white;padding:22px;border-radius:14px;box-shadow:0 4px 18px #102a4310}.btn{display:inline-block;background:#0f766e;color:white;padding:11px 17px;border:0;border-radius:8px;text-decoration:none;cursor:pointer}
input{width:100%;padding:12px;margin:7px 0 16px;border:1px solid #cbd5e1;border-radius:8px}label{font-weight:bold}textarea{font:inherit}
.notice{padding:12px;background:#dcfce7;border-radius:8px;margin:12px 0}footer{text-align:center;color:#64748b;padding:35px}
</style></head><body><nav><a class="brand" href="/">SmartLearn</a><a href="/courses">Courses</a>
{% if current_user.is_authenticated %}<a href="/dashboard">My learning</a>{% if is_smartlearn_admin %}<a href="/admin">Admin</a>{% endif %}<a href="/logout">Sign out</a>{% else %}<a href="/login">Sign in</a><a href="/register">Create account</a>{% endif %}</nav>
<main>{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="notice">{{m}}</div>{% endfor %}{% endwith %}{{body|safe}}</main><footer>SmartLearn · Learn something new every day</footer></body></html>"""
def page(title,body,**ctx): return render_template_string(BASE,title=title,body=render_template_string(body,**ctx),**ctx)

@app.route("/")
def home():
 cs=Course.query.order_by(Course.id).limit(6).all()
 return page("Home",'''<section class="hero"><h1>Learn without limits.</h1><p>Build practical skills with accessible online courses.</p><a class="btn" href="/courses">Explore courses</a></section><h2>Popular courses</h2><div class="grid">{% for c in cs %}<article class="card"><p class="muted">{{c.category}} · {{c.level}}</p><h3>{{c.title}}</h3><p>{{c.description}}</p><a href="/course/{{c.id}}">View course →</a></article>{% else %}<p>Courses are being prepared.</p>{% endfor %}</div>''',cs=cs)

@app.route("/health")
def health(): return {"status":"ok","app":"SmartLearn"}

@app.route("/courses")
def courses():
 cs=Course.query.order_by(Course.title).all()
 return page("Courses",'''<h1>Course catalogue</h1><div class="grid">{% for c in cs %}<article class="card"><p class="muted">{{c.category}} · {{c.level}}</p><h2>{{c.title}}</h2><p>{{c.description}}</p><a class="btn" href="/course/{{c.id}}">View course</a></article>{% else %}<p>No courses published yet.</p>{% endfor %}</div>''',cs=cs)

@app.route("/course/<int:cid>")
def course(cid):
 c=Course.query.get_or_404(cid)
 return page(c.title,'''<article class="card"><p class="muted">{{c.category}} · {{c.level}}</p><h1>{{c.title}}</h1><p>{{c.description}}</p>{% if current_user.is_authenticated %}<form method="post" action="/enrol/{{c.id}}"><button class="btn">Enrol in this course</button></form>{% else %}<a class="btn" href="/login">Sign in to enrol</a>{% endif %}<h2>Lessons</h2>{% for l in c.lessons|sort(attribute='position') %}<p><a href="/lesson/{{l.id}}">{{l.position}}. {{l.title}}</a></p>{% else %}<p>Lessons will be added soon.</p>{% endfor %}</article>''',c=c)

@app.route("/register",methods=["GET","POST"])
def register():
 if request.method=="POST":
  name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower(); pw=request.form.get("password","")
  if not name or not email or len(pw)<8: flash("Enter your name, email and a password of at least 8 characters.")
  elif User.query.filter_by(email=email).first(): flash("That email is already registered.")
  else:
   u=User(name=name,email=email); u.set_password(pw); db.session.add(u); db.session.commit(); login_user(u); return redirect(url_for("dashboard"))
 return page("Register",'''<div class="card" style="max-width:520px;margin:auto"><h1>Create your account</h1><form method="post"><label>Full name</label><input name="name" required><label>Email</label><input name="email" type="email" required><label>Password (minimum 8 characters)</label><input name="password" type="password" minlength="8" required><button class="btn">Create account</button></form></div>''')

@app.route("/login",methods=["GET","POST"])
def login():
 if request.method=="POST":
  u=User.query.filter_by(email=request.form.get("email","").strip().lower()).first()
  if u and u.check_password(request.form.get("password","")): login_user(u); return redirect(url_for("dashboard"))
  flash("Email or password is incorrect.")
 return page("Sign in",'''<div class="card" style="max-width:520px;margin:auto"><h1>Welcome back</h1><form method="post"><label>Email</label><input name="email" type="email" required><label>Password</label><input name="password" type="password" required><button class="btn">Sign in</button></form></div>''')


def admin_required():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    if not admin_email or current_user.email.lower() != admin_email:
        abort(403)
    return None

@app.context_processor
def inject_admin_status():
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    return {"is_smartlearn_admin": bool(current_user.is_authenticated and admin_email and current_user.email.lower() == admin_email)}

@app.route("/admin")
@login_required
def admin_dashboard():
    denied = admin_required()
    if denied: return denied
    return page("Admin dashboard", """
    <h1>SmartLearn administration</h1>
    <p class="muted">Manage courses, lessons and registered learners.</p>
    <div class="grid">
      <article class="card"><h2>{{course_count}}</h2><p>Courses</p></article>
      <article class="card"><h2>{{lesson_count}}</h2><p>Lessons</p></article>
      <article class="card"><h2>{{student_count}}</h2><p>Registered learners</p></article>
    </div>
    <p><a class="btn" href="/admin/course/new">Add a course</a></p>
    <h2>Courses</h2>
    {% for c in courses %}<article class="card" style="margin:12px 0">
      <h3>{{c.title}}</h3><p>{{c.category}} · {{c.level}} · {{c.lessons|length}} lessons · {{c.students|length}} enrolled</p>
      <a href="/course/{{c.id}}">View course</a> · <a href="/admin/course/{{c.id}}/lesson/new">Add lesson</a>
      <form method="post" action="/admin/course/{{c.id}}/delete" onsubmit="return confirm('Delete this course and its lessons?')"><button class="btn" style="background:#b91c1c;margin-top:10px">Delete course</button></form>
    </article>{% else %}<p>No courses yet.</p>{% endfor %}
    <h2>Registered learners</h2><div class="card"><ul>{% for u in users %}<li>{{u.name}} — {{u.email}} — {{u.courses|length}} enrolled</li>{% else %}<li>No learners registered.</li>{% endfor %}</ul></div>
    """, course_count=Course.query.count(), lesson_count=Lesson.query.count(),
       student_count=User.query.count(), courses=Course.query.order_by(Course.title).all(),
       users=User.query.order_by(User.name).all())

@app.route("/admin/course/new", methods=["GET", "POST"])
@login_required
def admin_new_course():
    denied = admin_required()
    if denied: return denied
    if request.method == "POST":
        title=request.form.get("title","").strip()
        category=request.form.get("category","ICT").strip() or "ICT"
        level=request.form.get("level","Beginner").strip() or "Beginner"
        description=request.form.get("description","").strip()
        if not title:
            flash("Course title is required.")
        else:
            db.session.add(Course(title=title,category=category,level=level,description=description))
            db.session.commit()
            flash("Course created successfully.")
            return redirect(url_for("admin_dashboard"))
    return page("Add course", """
    <div class="card" style="max-width:650px;margin:auto"><h1>Add a course</h1>
    <form method="post"><label>Course title</label><input name="title" required maxlength="160">
    <label>Category</label><input name="category" placeholder="ICT, Programming, Web Design">
    <label>Level</label><input name="level" placeholder="Beginner, Intermediate, Advanced">
    <label>Description</label><textarea name="description" rows="5" style="width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:8px"></textarea>
    <button class="btn">Save course</button> <a href="/admin">Cancel</a></form></div>
    """)

@app.route("/admin/course/<int:cid>/lesson/new", methods=["GET", "POST"])
@login_required
def admin_new_lesson(cid):
    denied = admin_required()
    if denied: return denied
    c=Course.query.get_or_404(cid)
    if request.method == "POST":
        title=request.form.get("title","").strip()
        content=request.form.get("content","").strip()
        if not title:
            flash("Lesson title is required.")
        else:
            next_position=(db.session.query(db.func.max(Lesson.position)).filter_by(course_id=c.id).scalar() or 0)+1
            db.session.add(Lesson(course_id=c.id,title=title,content=content,position=next_position))
            db.session.commit()
            flash("Lesson added successfully.")
            return redirect(url_for("admin_dashboard"))
    return page("Add lesson", """
    <div class="card" style="max-width:720px;margin:auto"><h1>Add lesson</h1><p>Course: {{c.title}}</p>
    <form method="post"><label>Lesson title</label><input name="title" required maxlength="160">
    <label>Lesson content</label><textarea name="content" rows="12" style="width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:8px" placeholder="Write the lesson notes here..." required></textarea>
    <button class="btn">Save lesson</button> <a href="/admin">Cancel</a></form></div>
    """, c=c)

@app.route("/admin/course/<int:cid>/delete", methods=["POST"])
@login_required
def admin_delete_course(cid):
    denied = admin_required()
    if denied: return denied
    c=Course.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash("Course and its lessons deleted.")
    return redirect(url_for("admin_dashboard"))

@app.route("/logout")
@login_required
def logout(): logout_user(); return redirect(url_for("home"))

@app.route("/enrol/<int:cid>",methods=["POST"])
@login_required
def enrol(cid):
 c=Course.query.get_or_404(cid)
 if c not in current_user.courses: current_user.courses.append(c); db.session.commit()
 flash("You are enrolled in "+c.title); return redirect(url_for("dashboard"))

@app.route("/dashboard")
@login_required
def dashboard():
 return page("My learning",'''<h1>My learning</h1><p>Welcome, {{current_user.name}}.</p><div class="grid">{% for c in current_user.courses %}<article class="card"><h2>{{c.title}}</h2><p>{{c.description}}</p><a href="/course/{{c.id}}">Continue learning →</a></article>{% else %}<p>You have not enrolled in any courses. <a href="/courses">Browse courses</a>.</p>{% endfor %}</div>''')

@app.route("/lesson/<int:lid>")
@login_required
def lesson(lid):
 l=Lesson.query.get_or_404(lid)
 if l.course not in current_user.courses: abort(403)
 return page(l.title,'''<article class="card"><p><a href="/course/{{l.course.id}}">← {{l.course.title}}</a></p><h1>{{l.title}}</h1><div style="white-space:pre-wrap;line-height:1.7">{{l.content}}</div></article>''',l=l)

with app.app_context():
 db.create_all()
 # Lightweight, non-destructive schema migration for existing installations.
 # SQLAlchemy create_all() creates missing tables but does not add new columns.
 from sqlalchemy import inspect
 schema_updates = {
  "course": {
   "category": "VARCHAR(80) DEFAULT 'ICT'",
   "description": "TEXT",
   "level": "VARCHAR(40) DEFAULT 'Beginner'"
  },
  "lesson": {
   "position": "INTEGER DEFAULT 1"
  }
 }
 inspector = inspect(db.engine)
 with db.engine.begin() as connection:
  for table_name, columns in schema_updates.items():
   if inspector.has_table(table_name):
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    for column_name, column_sql in columns.items():
     if column_name not in existing:
      connection.exec_driver_sql(
       f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"
      )
 if Course.query.count()==0:
  seeds=[("Computer Fundamentals","ICT","Understand computer hardware, software, data representation and basic computer operations.","Beginner"),("Google Docs","Productivity","Create, format, collaborate on and share professional documents.","Beginner"),("HTML and CSS","Web Design","Build structured web pages and style them using CSS.","Beginner"),("Database and SQL","Programming","Learn relational databases, tables, queries and SQL operations.","Intermediate"),("Python Programming","Programming","Develop programming skills using Python fundamentals.","Beginner"),("Computer Networking","Networking","Explore network devices, addressing, protocols and security basics.","Intermediate")]
  for title,cat,desc,level in seeds: db.session.add(Course(title=title,category=cat,description=desc,level=level))
  db.session.commit()

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)))
