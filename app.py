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
input{width:100%;padding:12px;margin:7px 0 16px;border:1px solid #cbd5e1;border-radius:8px}label{font-weight:bold}
.notice{padding:12px;background:#dcfce7;border-radius:8px;margin:12px 0}footer{text-align:center;color:#64748b;padding:35px}
</style></head><body><nav><a class="brand" href="/">SmartLearn</a><a href="/courses">Courses</a>
{% if current_user.is_authenticated %}<a href="/dashboard">My learning</a><a href="/logout">Sign out</a>{% else %}<a href="/login">Sign in</a><a href="/register">Create account</a>{% endif %}</nav>
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
 if Course.query.count()==0:
  seeds=[("Computer Fundamentals","ICT","Understand computer hardware, software, data representation and basic computer operations.","Beginner"),("Google Docs","Productivity","Create, format, collaborate on and share professional documents.","Beginner"),("HTML and CSS","Web Design","Build structured web pages and style them using CSS.","Beginner"),("Database and SQL","Programming","Learn relational databases, tables, queries and SQL operations.","Intermediate"),("Python Programming","Programming","Develop programming skills using Python fundamentals.","Beginner"),("Computer Networking","Networking","Explore network devices, addressing, protocols and security basics.","Intermediate")]
  for title,cat,desc,level in seeds: db.session.add(Course(title=title,category=cat,description=desc,level=level))
  db.session.commit()

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)))
