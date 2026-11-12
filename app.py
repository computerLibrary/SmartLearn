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
.home-hero{background:linear-gradient(90deg,rgba(8,35,55,.92),rgba(8,35,55,.42)),url("https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1800&q=85") center/cover no-repeat;min-height:340px;display:flex;align-items:center}
.visual-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:18px;margin:22px 0 34px}
.visual-card{background:white;border-radius:14px;overflow:hidden;box-shadow:0 4px 18px #102a4310}
.visual-card img{display:block;width:100%;height:155px;object-fit:cover}
.visual-card div{padding:16px}.visual-card h3{margin:0 0 8px}.visual-card p{margin:0;color:#64748b;line-height:1.5}
@media(max-width:600px){.home-hero{min-height:300px;padding:28px}}
</style></head><body><nav><a class="brand" href="/">SmartLearn</a><a href="/courses">Courses</a>
{% if current_user.is_authenticated %}<a href="/dashboard">My learning</a>{% if is_smartlearn_admin %}<a href="/admin">Admin</a>{% endif %}<a href="/logout">Sign out</a>{% else %}<a href="/login">Sign in</a><a href="/register">Create account</a>{% endif %}</nav>
<main>{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="notice">{{m}}</div>{% endfor %}{% endwith %}{{body|safe}}</main><footer>SmartLearn · Learn something new every day<br><span style="font-size:14px">Developed by <strong>Isaac NKURUNZIZA</strong></span></footer></body></html>"""
def page(title,body,**ctx): return render_template_string(BASE,title=title,body=render_template_string(body,**ctx),**ctx)

@app.route("/")
def home():
 cs=Course.query.order_by(Course.id).limit(6).all()
 return page("Home","""
 <section class="hero home-hero"><div><p style="text-transform:uppercase;letter-spacing:2px;font-weight:bold">Welcome to SmartLearn</p><h1>Learn today. Build tomorrow.</h1><p style="max-width:600px;line-height:1.7">Develop practical digital skills in computing, programming, web design, databases and emerging technologies.</p><a class="btn" href="/courses">Explore courses</a></div></section>
 <h2>Explore learning areas</h2>
 <div class="visual-grid">
  <article class="visual-card"><img src="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=900&q=80" alt="Learner working on a laptop" loading="lazy"><div><h3>Digital skills</h3><p>Build confidence using essential digital tools and technology.</p></div></article>
  <article class="visual-card"><img src="https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=900&q=80" alt="Team collaborating at computers" loading="lazy"><div><h3>Programming</h3><p>Learn problem-solving, algorithms and software development.</p></div></article>
  <article class="visual-card"><img src="https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=900&q=80" alt="Web development workspace with code on a screen" loading="lazy"><div><h3>Web development</h3><p>Create websites and learn how frontend and backend systems work.</p></div></article>
  <article class="visual-card"><img src="https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?auto=format&fit=crop&w=900&q=80" alt="Computer programming code on a monitor" loading="lazy"><div><h3>Data and AI</h3><p>Explore databases, data analysis and artificial intelligence.</p></div></article>
 </div>
 <h2>Popular courses</h2><div class="grid">{% for c in cs %}<article class="card"><p class="muted">{{c.category}} · {{c.level}}</p><h3>{{c.title}}</h3><p>{{c.description}}</p><a href="/course/{{c.id}}">View course →</a></article>{% else %}<p>Courses are being prepared.</p>{% endfor %}</div>
 """,cs=cs)

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
  "user": {
   "password_hash": "VARCHAR(255) NULL"
  },
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
      existing.add(column_name)
  # The previous SmartLearn version stored password hashes in user.password.
  # Copy them into the new password_hash column without deleting existing accounts.
  if inspector.has_table("user"):
   existing_user_columns = {column["name"] for column in inspect(db.engine).get_columns("user")}
   if "password" in existing_user_columns and "password_hash" in existing_user_columns:
    connection.exec_driver_sql(
     "UPDATE user SET password_hash = password WHERE password_hash IS NULL OR password_hash = ''"
    )
   elif "password_hash" in existing_user_columns:
    connection.exec_driver_sql(
     "UPDATE user SET password_hash = '' WHERE password_hash IS NULL"
    )
   # The legacy password column is no longer written by this application.
   # Keep existing hashes, but allow new accounts to leave that old column empty.
   if db.engine.dialect.name == "mysql" and "password" in existing_user_columns:
    password_column = next(
     column for column in inspect(db.engine).get_columns("user")
     if column["name"] == "password"
    )
    if not password_column.get("nullable", True):
     connection.exec_driver_sql(
      "ALTER TABLE user MODIFY COLUMN password VARCHAR(255) NULL"
     )
 if Course.query.count()==0:
  seeds=[("Computer Fundamentals","ICT","Understand computer hardware, software, data representation and basic computer operations.","Beginner"),("Google Docs","Productivity","Create, format, collaborate on and share professional documents.","Beginner"),("HTML and CSS","Web Design","Build structured web pages and style them using CSS.","Beginner"),("Database and SQL","Programming","Learn relational databases, tables, queries and SQL operations.","Intermediate"),("Python Programming","Programming","Develop programming skills using Python fundamentals.","Beginner"),("Computer Networking","Networking","Explore network devices, addressing, protocols and security basics.","Intermediate")]
  for title,cat,desc,level in seeds: db.session.add(Course(title=title,category=cat,description=desc,level=level))
  db.session.commit()

# Add structured starter lessons to existing courses without duplicating content.
# Existing courses and enrolments are preserved; courses with lessons are left unchanged.
lesson_catalog = {
  "Computer Fundamentals": [
    [
      "Introduction to Computers",
      "LEARNING OBJECTIVES\n- Define a computer and explain its main purpose.\n- Identify the input, processing, output and storage stages.\n\nNOTES\nA computer is an electronic device that accepts data, processes it according to instructions, stores it and produces information. Data are raw facts; information is processed data that has meaning. A typical information-processing cycle is input → processing → output, supported by storage and communication.\n\nComputers are used in education, health, banking, business, communication, research and government. They improve speed, accuracy and storage, but depend on correct instructions and data.\n\nKEY TERMS: data, information, hardware, software, user, processing.\n\nLEARNING ACTIVITIES\n1. Write your own definition of a computer.\n2. Identify five places in your community where computers are used and explain their purpose.\n3. Give three examples of data and show how each could become useful information."
    ],
    [
      "Computer Hardware and Software",
      "LEARNING OBJECTIVES\n- Distinguish hardware from software.\n- Classify common computer components.\n\nNOTES\nHardware refers to the physical parts that can be seen and touched. Input devices send data to a computer (keyboard, mouse, scanner, microphone). The CPU processes instructions and includes the control unit and arithmetic logic unit. Output devices present results (monitor, printer, speakers). Storage devices keep data, either temporarily or for long periods (RAM, SSD, hard drive, flash drive).\n\nSoftware is a set of programs that tells hardware what to do. System software manages the computer; an operating system such as Windows or Linux manages files, memory and devices. Application software helps users perform tasks, for example word processors, browsers and spreadsheets.\n\nLEARNING ACTIVITIES\n1. Draw a computer system and label four input, processing, output and storage examples.\n2. Classify ten devices or programs as hardware or software.\n3. Explain the difference between RAM and long-term storage."
    ],
    [
      "Types of Computers and Their Uses",
      "LEARNING OBJECTIVES\n- Describe common computer categories.\n- Match computer types to suitable tasks.\n\nNOTES\nComputers differ in size, processing power, portability and purpose. Supercomputers handle extremely complex calculations such as climate modelling. Mainframes process large volumes of transactions for institutions. Servers provide services and resources to other computers. Desktop computers are designed for a fixed workspace. Laptops are portable personal computers; tablets and smartphones use touch interfaces and built-in sensors. Embedded computers control devices such as vehicles, appliances and industrial machines.\n\nThe best computer depends on the task, cost, performance, reliability and mobility required.\n\nLEARNING ACTIVITIES\n1. Create a table comparing a desktop, laptop, tablet, server and supercomputer.\n2. Recommend a suitable computer for a school office, bank and travelling student. Justify each choice.\n3. Identify three embedded computers used in everyday life."
    ],
    [
      "Data Representation and Computer Memory",
      "LEARNING OBJECTIVES\n- Explain bits, bytes and basic units.\n- Describe how computers represent text, numbers and images.\n\nNOTES\nComputers store and process information using binary digits: 0 and 1. A bit is one binary digit; a byte is normally eight bits. Larger units include kilobytes, megabytes, gigabytes and terabytes. A bit can represent two states, while groups of bits represent larger values.\n\nText is encoded using character standards such as ASCII and Unicode. Images are represented as pixels, with colour information stored using binary values. Sound is represented by sampling a sound wave and storing the sample values. RAM is fast, temporary working memory; ROM/firmware stores instructions needed to start or control a device; secondary storage keeps files when power is off.\n\nLEARNING ACTIVITIES\n1. Convert the binary number 00000101 to denary by adding its place values.\n2. Write the 8-bit binary representation of denary 10.\n3. Explain why a high-resolution image usually needs more storage than a small text file."
    ],
    [
      "Operating Systems, Files and Computer Care",
      "LEARNING OBJECTIVES\n- Explain the role of an operating system.\n- Apply safe file-management and maintenance practices.\n\nNOTES\nAn operating system (OS) provides the interface between users, applications and hardware. It manages processes, memory, files, users, devices and security. Examples include Windows, Linux, macOS, Android and iOS. Files store information; folders organise files. Useful practices include meaningful filenames, consistent folders, backups and checking file extensions before opening unknown files.\n\nKeep a computer reliable by updating software, using reputable security tools, protecting ventilation, keeping liquids away and shutting down correctly. Use strong unique passwords and avoid unknown downloads or links.\n\nLEARNING ACTIVITIES\n1. Create a folder named ICT_Practice and organise three subfolders inside it.\n2. Describe five tasks performed by an operating system.\n3. Prepare a simple weekly computer-maintenance checklist."
    ]
  ],
  "Google Docs": [
    [
      "Getting Started with Google Docs",
      "LEARNING OBJECTIVES\n- Open Google Docs and create a document.\n- Identify the main workspace features.\n\nNOTES\nGoogle Docs is an online word-processing application used to create, edit, format and share documents. A Google account is normally used to access it. Start a blank document or choose a template, then rename it by clicking the document title. The editing area is the page workspace; menus and toolbars provide commands for formatting, inserting objects and reviewing work.\n\nDocs saves changes automatically when connected. Files are stored in Google Drive and can be accessed from supported devices. A stable internet connection is useful; offline access may be configured in advance.\n\nLEARNING ACTIVITIES\n1. Create a blank document titled My ICT Learning Profile.\n2. Type your name, class, school and three learning goals.\n3. Locate the undo, print, zoom and document-title controls."
    ],
    [
      "Editing and Formatting Text",
      "LEARNING OBJECTIVES\n- Edit text accurately.\n- Apply character and paragraph formatting.\n\nNOTES\nEditing changes document content: insert, select, delete, copy, cut, paste and move text. Formatting changes appearance without changing meaning. Select text before applying font family, size, bold, italic, underline, text colour or highlight. Paragraph tools include alignment, line spacing, indentation and bullets or numbering.\n\nUse headings to create a clear structure. Keep fonts readable and formatting consistent. Use spelling and grammar suggestions as aids, but review suggestions because they may not understand the intended meaning.\n\nLEARNING ACTIVITIES\n1. Type a two-paragraph note about the importance of ICT.\n2. Format the title as 20-point bold and centre aligned.\n3. Add a numbered list of five computer uses and apply 1.5 line spacing."
    ],
    [
      "Page Layout, Tables and Images",
      "LEARNING OBJECTIVES\n- Set up page layout.\n- Insert and format tables and images.\n\nNOTES\nPage setup controls paper size, orientation and margins. Portrait is taller than it is wide; landscape is wider. Page breaks start content on a new page. Headers and footers repeat information such as document titles or page numbers.\n\nTables organise information into rows and columns. Use Insert → Table, then add or remove rows and columns as needed. Images can be inserted from a device or supported online sources. Resize images using corner handles to preserve proportions and use text-wrapping options to control placement. Add descriptive captions when they improve understanding.\n\nLEARNING ACTIVITIES\n1. Set a document to landscape orientation.\n2. Insert a 4-column, 5-row table showing subject, teacher, room and time.\n3. Insert a relevant image and resize it without distorting it; add a caption."
    ],
    [
      "Collaboration, Comments and Sharing",
      "LEARNING OBJECTIVES\n- Share a document responsibly.\n- Use comments and suggestions for collaboration.\n\nNOTES\nGoogle Docs supports collaboration by allowing several people to work on a document. The Share control lets the owner invite specific people or configure link access. Common roles are Viewer, Commenter and Editor. Give only the access needed and avoid public link sharing for private information.\n\nComments allow collaborators to ask questions or give feedback without changing the main text. Suggesting mode proposes edits that the owner can accept or reject. Version history shows earlier versions and can help restore work after unwanted changes.\n\nLEARNING ACTIVITIES\n1. Share a practice document with a classmate as Viewer, then change access to Commenter.\n2. Add a comment asking for feedback on one paragraph.\n3. Open version history and identify how an earlier version can be restored."
    ],
    [
      "Document Review, Printing and Productivity",
      "LEARNING OBJECTIVES\n- Review a document before submission.\n- Prepare a document for printing or PDF delivery.\n\nNOTES\nA professional document has a clear title, logical headings, consistent formatting and correct spelling. Use page numbers for longer documents and check that tables and images fit within margins. Use Find and Replace to locate repeated words or correct consistent errors. Download or export a copy as PDF when a fixed layout is required. Preview the document before printing to check page breaks, orientation and blank pages.\n\nRespect copyright: credit sources for text and images that are not your own. Use accessible headings and meaningful link text.\n\nLEARNING ACTIVITIES\n1. Review your ICT Learning Profile using spelling suggestions and Find and Replace.\n2. Add a header, footer and page number.\n3. Download the document as PDF and inspect the print preview."
    ]
  ],
  "HTML and CSS": [
    [
      "How the Web and HTML Work",
      "LEARNING OBJECTIVES\n- Explain the purpose of HTML.\n- Describe the basic structure of an HTML page.\n\nNOTES\nThe web is a collection of linked resources accessed through browsers. A browser requests a resource from a web server using HTTP or HTTPS and displays the returned content. HTML (HyperText Markup Language) describes the structure and meaning of web content; it is a markup language, not a programming language.\n\nA basic HTML5 document includes <!doctype html>, html, head and body elements. The head contains metadata and the page title; the body contains visible content. Elements are usually formed with an opening tag, content and a closing tag. Some elements, such as img and br, are void elements and do not wrap content.\n\nLEARNING ACTIVITIES\n1. Create index.html with a valid HTML5 structure.\n2. Add a page title, one main heading and one paragraph.\n3. Open the file in a browser and describe what appears."
    ],
    [
      "HTML Elements, Attributes, Links and Images",
      "LEARNING OBJECTIVES\n- Use common HTML elements.\n- Apply attributes to provide additional information.\n\nNOTES\nHeadings h1 to h6 express a hierarchy; paragraphs use p; emphasis uses em or strong; lists use ul/ol with li items. Links use the a element with an href attribute. Images use img with a src and meaningful alt text. Attributes appear in an element's opening tag and provide extra information. Quote attribute values and use descriptive names.\n\nUse semantic elements such as header, nav, main, section, article and footer to describe page structure. A link should explain its destination; alt text should communicate an image's purpose.\n\nLEARNING ACTIVITIES\n1. Build a page with three heading levels, a paragraph and an ordered list.\n2. Add a link to a trusted learning website.\n3. Insert an image with useful alternative text."
    ],
    [
      "HTML Forms and User Input",
      "LEARNING OBJECTIVES\n- Create a simple HTML form.\n- Choose appropriate input types and labels.\n\nNOTES\nForms collect information from users. The form element groups controls and may specify an action and method. Labels identify controls and should be connected using matching for/id values. Common input types include text, email, password, number, date, checkbox and radio. A button submits the form. Required and other validation attributes help prevent incomplete or incorrectly formatted input, but server-side validation is still essential.\n\nNever collect sensitive information without a legitimate reason and appropriate protection. A password field hides typed characters visually; it does not encrypt data by itself.\n\nLEARNING ACTIVITIES\n1. Create a student registration form with name, email, date of birth and course fields.\n2. Add labels and mark essential fields as required.\n3. Test the form with valid and invalid entries and note the browser's response."
    ],
    [
      "Introduction to CSS and Selectors",
      "LEARNING OBJECTIVES\n- Explain the role of CSS.\n- Apply CSS rules using selectors.\n\nNOTES\nCSS (Cascading Style Sheets) controls presentation such as colours, fonts, spacing, borders and layout. HTML provides structure; CSS provides visual styling. A CSS rule contains a selector and declaration block. Each declaration has a property and value, for example p { color: navy; }.\n\nCSS can be added inline, in a style element in the document head, or through an external .css file linked with link rel=\"stylesheet\". External stylesheets are usually best for multi-page sites because they support reuse and easier maintenance. Selectors include element, class, ID and attribute selectors. The cascade considers origin, importance, specificity and source order.\n\nLEARNING ACTIVITIES\n1. Create styles.css and link it to index.html.\n2. Set a page background, heading colour and paragraph font size.\n3. Create a class called highlight and apply it to two elements."
    ],
    [
      "CSS Box Model, Layout and Responsive Design",
      "LEARNING OBJECTIVES\n- Explain the CSS box model.\n- Build a simple responsive page layout.\n\nNOTES\nEvery element is laid out as a box consisting of content, padding, border and margin. Padding is space inside the border; margin is space outside it. The box-sizing property can make sizing easier; border-box includes padding and border in the declared width.\n\nCSS layout tools include Flexbox for arranging items along one dimension and Grid for rows and columns. Responsive design adapts to different screen sizes using flexible widths, relative units and media queries. Test pages on narrow and wide screens. Avoid fixed widths that cause horizontal scrolling.\n\nLEARNING ACTIVITIES\n1. Draw and label the four parts of the box model.\n2. Create a navigation bar using Flexbox.\n3. Use a media query to change a two-column layout into one column on a narrow screen."
    ]
  ],
  "Database and SQL": [
    [
      "Database Concepts and Relational Tables",
      "LEARNING OBJECTIVES\n- Define database, DBMS and relational database.\n- Identify tables, records and fields.\n\nNOTES\nA database is an organised collection of related data. A database management system (DBMS) creates, stores, retrieves and protects data. In a relational database, data are organised into tables. A row is a record; a column is a field or attribute. Each field has a data type such as integer, date, text or decimal.\n\nGood database design reduces unnecessary duplication and helps maintain consistency. Tables should represent clear entities such as Student, Course or Enrolment. Relationships connect related records across tables.\n\nLEARNING ACTIVITIES\n1. Design a Student table with student_id, full_name, email and date_registered.\n2. Identify the fields and records in a sample class register.\n3. Explain two advantages of using a database instead of separate paper lists."
    ],
    [
      "Keys, Relationships and Data Integrity",
      "LEARNING OBJECTIVES\n- Distinguish primary and foreign keys.\n- Explain one-to-one, one-to-many and many-to-many relationships.\n\nNOTES\nA primary key uniquely identifies each row and should not be null. A foreign key refers to a key in another table and creates a relationship. A student may enrol in many courses and each course may have many students; this many-to-many relationship is usually implemented using an Enrolment junction table.\n\nReferential integrity ensures that references remain valid. Constraints such as NOT NULL, UNIQUE, PRIMARY KEY, FOREIGN KEY and CHECK help enforce rules. Choose suitable actions for updates and deletes so related data are not accidentally lost.\n\nLEARNING ACTIVITIES\n1. Draw Student, Course and Enrolment tables and mark primary and foreign keys.\n2. Identify the relationship between a teacher and the classes they teach.\n3. Explain why a foreign key can prevent deleting a course that still has enrolment records."
    ],
    [
      "SQL Basics: Creating and Changing Tables",
      "LEARNING OBJECTIVES\n- Recognise common SQL statements.\n- Create a table and modify its structure.\n\nNOTES\nSQL (Structured Query Language) is used to define, query and manipulate relational databases. DDL statements define structures: CREATE TABLE, ALTER TABLE and DROP TABLE. DML statements change data: INSERT, UPDATE and DELETE. DQL commonly refers to SELECT queries. SQL syntax varies slightly between database systems.\n\nExample: CREATE TABLE Student (student_id INT PRIMARY KEY, full_name VARCHAR(100) NOT NULL, email VARCHAR(150) UNIQUE); INSERT INTO Student (student_id, full_name, email) VALUES (1, 'Amina N.', 'amina@example.com');\n\nBe careful with UPDATE and DELETE: use a WHERE clause when you intend to affect selected rows. Back up important data before structural changes.\n\nLEARNING ACTIVITIES\n1. Write a CREATE TABLE statement for a Course table.\n2. Write two INSERT statements with different course records.\n3. Explain the risk of running DELETE FROM Student without a WHERE clause."
    ],
    [
      "Querying Data with SELECT, Filtering and Sorting",
      "LEARNING OBJECTIVES\n- Retrieve selected data with SELECT.\n- Filter, sort and summarise query results.\n\nNOTES\nSELECT retrieves data. Use SELECT column_list FROM table_name; to choose columns. WHERE filters rows using comparisons and logical operators. LIKE matches text patterns; IN checks membership in a list; BETWEEN checks a range; IS NULL checks missing values. ORDER BY sorts results, while GROUP BY creates groups for aggregate calculations. Common aggregate functions include COUNT, SUM, AVG, MIN and MAX. HAVING filters groups after aggregation.\n\nExample: SELECT course_name FROM Course WHERE level = 'Beginner' ORDER BY course_name;\n\nLEARNING ACTIVITIES\n1. Write a query to display all students alphabetically by name.\n2. Write a query to count courses in each category.\n3. Explain the difference between WHERE and HAVING."
    ],
    [
      "Joins, Normalisation, Security and Backup",
      "LEARNING OBJECTIVES\n- Combine related tables using joins.\n- Explain normalisation and basic database protection.\n\nNOTES\nA JOIN combines rows from related tables. INNER JOIN returns matching rows; LEFT JOIN returns all rows from the left table and matching rows from the right; RIGHT JOIN returns all rows from the right and matches from the left. A many-to-many relationship is joined through its junction table.\n\nNormalisation organises data to reduce duplication and update anomalies. First Normal Form requires atomic values and no repeating groups; later normal forms address dependencies. Protect databases with user permissions, strong authentication, parameterised queries and regular tested backups. Give users only the privileges they need.\n\nLEARNING ACTIVITIES\n1. Join Student and Enrolment to list students and their course IDs.\n2. Describe a situation where LEFT JOIN is more useful than INNER JOIN.\n3. Identify two duplicated-data problems and propose a normalised table design."
    ]
  ],
  "Python Programming": [
    [
      "Introduction to Python and Program Structure",
      "LEARNING OBJECTIVES\n- Explain what Python is used for.\n- Write and run a simple Python program.\n\nNOTES\nPython is a high-level, general-purpose programming language known for readable syntax. It is used in automation, web development, data analysis, artificial intelligence and education. A program is a set of instructions. Python executes statements in sequence unless control structures change the flow.\n\nExample:\nprint(\"Hello, SmartLearn!\")\n\nComments begin with # and explain code to human readers. Indentation is meaningful in Python and defines blocks of code. Use clear filenames and meaningful variable names. Errors may be syntax errors, runtime errors or logic errors.\n\nLEARNING ACTIVITIES\n1. Install or open a Python environment approved by your teacher.\n2. Write and run a program that prints your name and school.\n3. Intentionally remove a quotation mark, run the program and describe the error."
    ],
    [
      "Variables, Data Types and Operators",
      "LEARNING OBJECTIVES\n- Store values in variables.\n- Use common data types and operators.\n\nNOTES\nA variable is a name that refers to a value. Assign values with =, for example age = 18. Common types include int for whole numbers, float for decimal numbers, str for text and bool for True/False values. Use type() to inspect a value's type. Convert values with int(), float() and str() when appropriate.\n\nArithmetic operators include +, -, *, /, //, %, and **. Comparison operators include ==, !=, <, >, <= and >=. Logical operators are and, or and not. The + operator can add numbers or join strings depending on their types.\n\nLEARNING ACTIVITIES\n1. Store two numbers and display their sum, difference, product and quotient.\n2. Ask the user for their age and convert the input to an integer.\n3. Predict the result of 17 // 5 and 17 % 5, then verify by running Python."
    ],
    [
      "Input, Output and Conditional Statements",
      "LEARNING OBJECTIVES\n- Accept input and display output.\n- Make decisions using if, elif and else.\n\nNOTES\ninput() reads text entered by the user. print() displays output. Convert input to a numeric type before performing arithmetic. Conditional statements run different blocks depending on whether an expression is True or False. Use if for the first condition, elif for additional conditions and else for the remaining case. Indent each block consistently.\n\nExample:\nmark = int(input(\"Enter mark: \"))\nif mark >= 70:\n    print(\"Distinction\")\nelif mark >= 50:\n    print(\"Pass\")\nelse:\n    print(\"Needs improvement\")\n\nLEARNING ACTIVITIES\n1. Write a program that asks for two numbers and displays the larger one.\n2. Create a grading program with at least four grade categories.\n3. Test boundary values such as 49, 50, 69 and 70."
    ],
    [
      "Loops, Collections and Functions",
      "LEARNING OBJECTIVES\n- Repeat instructions with loops.\n- Store multiple values and organise reusable code.\n\nNOTES\nA for loop iterates over a sequence; a while loop repeats while a condition remains True. Ensure a while loop eventually changes its condition to avoid an infinite loop. Lists store ordered, changeable collections. Indexing starts at zero. Dictionaries store key-value pairs. Functions are defined with def, can accept parameters and may return a result using return.\n\nExample:\ndef add(a, b):\n    return a + b\n\nUse functions to divide a large program into smaller, testable tasks. Give functions and variables meaningful names.\n\nLEARNING ACTIVITIES\n1. Use a for loop to display numbers from 1 to 10.\n2. Store five subject marks in a list and calculate their average.\n3. Write a function that receives two numbers and returns the larger."
    ],
    [
      "Files, Errors, Modules and a Mini Project",
      "LEARNING OBJECTIVES\n- Read and write simple text files.\n- Handle common errors and organise a small program.\n\nNOTES\nFiles allow programs to keep information after they stop running. Use with open(\"notes.txt\", \"w\", encoding=\"utf-8\") as file: to write text and mode \"r\" to read. The with statement closes the file automatically. Exceptions can be handled with try and except so a program can respond to expected problems, such as invalid numeric input or a missing file.\n\nA module is a file or library of reusable Python code. Import modules with import. Test programs with normal, boundary and invalid inputs. Keep code readable and avoid repeating the same logic.\n\nLEARNING ACTIVITIES\n1. Write a program that saves a user's name and favourite subject to a text file.\n2. Add exception handling for a value that cannot be converted to an integer.\n3. Mini project: build a simple marks calculator that accepts five marks, calculates total, average and percentage, and displays a clear report."
    ]
  ],
  "Computer Networking": [
    [
      "Networking Fundamentals and Network Types",
      "LEARNING OBJECTIVES\n- Define a computer network.\n- Compare LAN, WAN and other network types.\n\nNOTES\nA computer network is a group of connected devices that exchange data and share resources. Benefits include communication, shared printers and files, centralised services and access to the internet. A LAN covers a limited area such as a home, office or school. A WAN connects networks over large geographic areas. A PAN connects personal devices over a short range; a MAN covers a metropolitan area.\n\nNetwork performance depends on bandwidth, latency, reliability, congestion and the quality of the connection. Networks may use wired or wireless links.\n\nLEARNING ACTIVITIES\n1. Classify a school network, home Bluetooth connection and international bank network.\n2. Draw a simple network for a computer laboratory.\n3. Explain two benefits and two risks of connecting computers."
    ],
    [
      "Network Devices, Media and Topologies",
      "LEARNING OBJECTIVES\n- Identify common networking devices.\n- Describe common network topologies and transmission media.\n\nNOTES\nA network interface card connects a device to a network. A switch forwards frames within a LAN using MAC addresses. A router connects different networks and forwards packets using IP addresses. A wireless access point connects Wi-Fi devices to a network. A modem adapts signals for a service provider connection; a firewall filters traffic according to security rules.\n\nTransmission media include copper Ethernet cable, fibre-optic cable and wireless radio. Common topologies include star, bus, ring and mesh. A star topology connects devices to a central switch and is common in modern LANs.\n\nLEARNING ACTIVITIES\n1. Draw a star topology with six computers and one switch.\n2. Match router, switch, access point and firewall to their functions.\n3. Compare fibre-optic and copper cable for distance, speed and interference."
    ],
    [
      "IP Addressing, MAC Addresses and DNS",
      "LEARNING OBJECTIVES\n- Distinguish IP and MAC addresses.\n- Explain IPv4, IPv6, DHCP and DNS.\n\nNOTES\nAn IP address is a logical address used to identify an interface and route packets across networks. IPv4 uses 32 bits, commonly written as four decimal octets, such as 192.168.1.10. IPv6 uses 128 bits and provides a much larger address space. A subnet mask or prefix identifies the network portion of an address. A MAC address is a link-layer hardware address used for local network delivery; it is not a substitute for an IP address.\n\nDHCP can automatically assign network settings. DNS translates domain names such as example.com into IP addresses. Private IPv4 ranges are used inside networks and usually access the internet through address translation.\n\nLEARNING ACTIVITIES\n1. Identify the four octets in 192.168.1.25.\n2. Explain the difference between a MAC address and an IP address.\n3. Describe what happens when a user enters a website name in a browser."
    ],
    [
      "Network Protocols and Internet Services",
      "LEARNING OBJECTIVES\n- Explain the purpose of common protocols.\n- Describe how web and email services use networks.\n\nNOTES\nProtocols are agreed rules for communication. Ethernet and Wi-Fi provide local network communication. IP addresses and routes packets. TCP provides reliable, ordered delivery; UDP provides lower-overhead datagrams without guaranteeing delivery. HTTP transfers web resources; HTTPS protects HTTP using TLS encryption and authentication. DNS resolves names. SMTP sends email; IMAP and POP3 are used to access email.\n\nA client requests a service and a server responds. Ports identify application services on a host. A secure connection depends on correct configuration, valid certificates and safe user behaviour.\n\nLEARNING ACTIVITIES\n1. Match HTTP, HTTPS, DNS, TCP, UDP and SMTP to their purposes.\n2. Explain why HTTPS is preferred for login pages.\n3. Trace the basic steps involved when a browser loads a website."
    ],
    [
      "Network Security, Troubleshooting and Design",
      "LEARNING OBJECTIVES\n- Identify common network threats.\n- Apply a systematic troubleshooting process.\n\nNOTES\nNetwork threats include malware, phishing, unauthorised access, denial-of-service attacks, eavesdropping and misconfiguration. Protect networks with firewalls, updates, strong authentication, encryption, backups, access control and user awareness. Use WPA2 or WPA3 for Wi-Fi and change default router passwords.\n\nTroubleshoot from simple causes to complex ones: check power and cables, Wi-Fi status, IP configuration, gateway, DNS and service availability. Useful tools include ping, ipconfig/ifconfig, tracert/traceroute and nslookup. Record symptoms and changes, test one cause at a time and document the solution.\n\nLEARNING ACTIVITIES\n1. Prepare a checklist for a computer that cannot access the internet.\n2. Explain why a strong Wi-Fi password and software updates matter.\n3. Design a secure small-school network with student, staff and guest access separated."
    ]
  ]
}
with app.app_context():
    for course_title, lesson_items in lesson_catalog.items():
        course_record = Course.query.filter_by(title=course_title).first()
        if course_record and Lesson.query.filter_by(course_id=course_record.id).count() == 0:
            for lesson_index, (lesson_title, lesson_content) in enumerate(lesson_items, start=1):
                db.session.add(Lesson(
                    course_id=course_record.id,
                    title=lesson_title,
                    content=lesson_content,
                    position=lesson_index
                ))
            db.session.commit()

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)))


# S4 and S5 ICT curriculum based on the two supplied prepared-notes documents.
# This migration is additive: existing courses, users, enrolments and lesson records remain untouched.
curriculum_units = [
("S4 ICT - Unit 1: Google Docs", "S4 ICT", "Google Docs: creating, formatting, organising and collaborating on documents.", [
("Getting started with Google Docs", "Google Docs is an online word processor used to create, edit, store and share documents. Access it with a Google account and create a blank document or use a template. The interface includes the document title, menus, toolbar, page workspace and sharing controls. Rename a document clearly and organise it in Drive.\n\nACTIVITY: Create a document named My ICT Learning Notes. Identify the menu bar, toolbar, page area and Share control."),
("Text formatting and page layout", "Text formatting changes the appearance and readability of a document. Select text before changing font family, size, colour, bold, italics, underline or highlight. Paragraph alignment, line spacing and paragraph spacing organise information. Use headings consistently to create a clear hierarchy.\n\nACTIVITY: Type three paragraphs and apply a title, heading, bold key terms, centre alignment and 1.5 line spacing."),
("Tables, images, links and collaboration", "Use bulleted and numbered lists to organise items. Insert tables to present structured information; adjust rows, columns and cell formatting. Insert images, drawings, shapes, links, bookmarks, headers, footers and page numbers where they improve a document. Sharing settings control who can view, comment or edit. Comments and Suggesting mode support review without silently replacing another person's work.\n\nACTIVITY: Prepare a one-page school club notice with a table, image, hyperlink, page number and a comment. Share it with a classmate using an appropriate permission.")
]),
("S4 ICT - Unit 2: Digital Logic Fundamentals", "S4 ICT", "Number systems, conversions, Boolean algebra, logic gates and circuit simulation.", [
("Number systems and place value", "A number system represents quantities using symbols and place values. Decimal is base 10 and uses digits 0-9; binary is base 2 and uses 0 and 1; octal is base 8; hexadecimal is base 16 and uses 0-9 and A-F. In positional notation, each digit is multiplied by a power of the base. Binary is important because digital circuits represent two states.\n\nACTIVITY: Identify the base and allowed digits of decimal, binary, octal and hexadecimal. Expand 1011₂ using powers of two."),
("Number-system conversion", "Convert a whole decimal number to another base by repeated division by the target base and reading remainders from bottom to top. Convert binary to decimal by summing each bit multiplied by its power of two. Binary groups of three bits correspond to octal digits; groups of four correspond to hexadecimal digits. Check conversions by converting the result back.\n\nACTIVITY: Convert 25₁₀ to binary, 11010₂ to decimal, 101101₂ to octal and 11111111₂ to hexadecimal. Show every step."),
("Boolean algebra, logic gates and simulation", "Boolean algebra works with two values, usually 0 and 1. AND produces 1 only when both inputs are 1; OR produces 1 when at least one input is 1; NOT reverses its input. Truth tables list outputs for all input combinations. Boolean expressions describe circuits, and Boolean rules can simplify expressions. Logic simulators such as Logisim or Proteus help construct and test interconnected gates.\n\nACTIVITY: Draw truth tables for AND, OR and NOT. Build a two-input AND circuit in a simulator and compare its output with your truth table.")
]),
("S4 ICT - Unit 3: Programming Algorithms", "S4 ICT", "Algorithms, variables, data types, operators, pseudocode, flowcharts, selection and iteration.", [
("Algorithms and variables", "An algorithm is a finite, ordered set of clear instructions for solving a problem. A good algorithm has clear inputs, outputs, definite steps and termination. Variables are named storage locations; choose meaningful names and follow language naming rules. Data types describe the kind of value, such as integer, real/decimal, character, string or Boolean. Operators perform arithmetic, comparison and logical operations.\n\nACTIVITY: Write an algorithm to calculate the sum and average of three marks. Identify its inputs, processing and outputs."),
("Input, output and algorithm representation", "Input statements receive values; output or write statements display results. Initialise variables before using them. Pseudocode expresses the logic in language-independent steps. A flowchart represents an algorithm with standard symbols: oval for start/end, parallelogram for input/output, rectangle for processing and diamond for decisions. Arrows show control flow.\n\nACTIVITY: Draw a flowchart for reading two numbers, adding them and displaying the sum. Label each symbol."),
("Selection and loops", "Selection chooses actions according to a condition. IF performs an action when a condition is true; IF-ELSE provides an alternative; nested IF statements test additional conditions. Loops repeat instructions. A FOR loop is useful when the number of repetitions is known; a WHILE loop repeats while its condition remains true. Update loop variables to avoid an infinite loop.\n\nACTIVITY: Write pseudocode to classify a mark as pass or fail. Then write a loop that displays numbers 1 to 10 and calculate their sum.")
]),
("S4 ICT - Unit 4: Python Programming I", "S4 ICT", "Python introduction, variables, data types, operators, input/output, conditions and loops.", [
("Introduction, installation and variables", "Python is a high-level programming language with readable syntax and uses in automation, web development, data analysis and AI. A Python program is a sequence of statements; indentation defines code blocks. Variables refer to values and are created by assignment. Common data types include int, float, str and bool. Use meaningful variable names and comments to make programs understandable.\n\nACTIVITY: Run print('Hello, ICT') and write a program that stores and displays your name, age and school."),
("Operators and input/output", "Arithmetic operators include +, -, *, /, //, % and **. Comparison operators compare values and return True or False. Logical operators and, or and not combine conditions. input() receives text from the keyboard; convert numeric input using int() or float() before calculations. print() displays output.\n\nACTIVITY: Ask the user for two numbers and display their sum, difference, product and quotient. Test with whole and decimal numbers."),
("Conditional statements and loops", "Use if, elif and else to make decisions. Conditions may compare values or combine expressions. Nested conditions place one decision inside another. A while loop repeats while its condition is true; a for loop iterates over a sequence or range. Indentation is essential in Python. Test boundary values and ensure loops terminate.\n\nACTIVITY: Build a grading program with at least four grade categories. Write a for loop to display 1-20 and a while loop that counts down from 5.")
]),
("S4 ICT - Unit 5: HTML-Based Web Development", "S4 ICT", "HTML page structure, text formatting, lists, media, tables, forms and hyperlinks.", [
("Introduction and HTML page structure", "HTML (HyperText Markup Language) describes the structure and content of web pages. An HTML document commonly contains the doctype declaration, html element, head with metadata and title, and body containing visible content. Elements are represented by tags. Headings h1-h6 express hierarchy; p represents a paragraph. Save a page with the .html extension and open it in a browser.\n\nACTIVITY: Create index.html with a title, one h1 heading and two paragraphs."),
("Text, lists, links and media", "Use strong and em to give text semantic emphasis. Lists use ul or ol with li items. Hyperlinks use the a element and href attribute to identify a destination; target can control where a link opens. Images use img and a source; meaningful alternative text improves accessibility. Audio and video elements can embed media in a page.\n\nACTIVITY: Create a page about your school with an ordered list, an unordered list, a hyperlink and an image with descriptive alternative text."),
("Tables and forms", "HTML tables organise tabular information using table, tr, th and td. Forms collect user input using form, label, input, select, textarea and button elements. Choose suitable input types such as text, email, password, date and number. Labels should identify each control. Browser validation is useful, but applications must also validate submitted data on the server.\n\nACTIVITY: Build a student registration form with name, email, gender and course fields. Create a separate table showing five students and their marks.")
]),
("S4 ICT - Unit 6: Cascading Style Sheets (CSS)", "S4 ICT", "CSS typography, text appearance, spacing, layout, effects, borders, backgrounds and ways to apply styles.", [
("CSS and font styling", "CSS (Cascading Style Sheets) controls the presentation of HTML. A rule contains a selector and declarations; each declaration has a property and value. Font properties include font-family, font-size, font-weight, font-style and font-variant. CSS separates content structure from presentation and makes a site easier to maintain.\n\nACTIVITY: Apply a font family, size, weight and colour to headings and paragraphs on an HTML page."),
("Text appearance, spacing and layout", "Text properties include color, text-align, text-decoration, text-transform, text-indent and text-shadow. Spacing properties include line-height, letter-spacing and word-spacing. Margin creates space outside an element; padding creates space between content and its border. Width and height control element dimensions.\n\nACTIVITY: Style a page with readable line spacing, aligned headings, margins and padding. Explain the difference between margin and padding."),
("Effects, borders, backgrounds and CSS methods", "CSS effects include text-shadow, box-shadow, hover effects, opacity, transform and transition. Borders define an element's edge and have width, style and colour. Background properties control colour, image, repeat, size and position. CSS can be inline, internal (style element) or external (separate stylesheet linked to the page). External CSS is generally best for consistent multi-page websites.\n\nACTIVITY: Create an external style sheet, add a bordered card with a background, shadow and hover transition, and link it to two HTML pages.")
]),
("S4 ICT - Unit 7: Database Design", "S4 ICT", "Database concepts, users and access levels, data independence, relational models, keys and relationships.", [
("Database concepts and users", "A database is an organised collection of related data. A database management system (DBMS) supports creating, storing, retrieving and protecting data. Database users may include administrators, designers, developers and end users. Access levels should give each user only the permissions required for their role. Data independence separates the way data is viewed by applications from details of physical storage.\n\nACTIVITY: Identify database users in a school system and describe the access each role should receive."),
("Relational database model and keys", "A relational database stores data in tables made of rows and columns. A primary key uniquely identifies each record and must be unique and not null. A foreign key refers to a key in another table and links related records. Relationships may be one-to-one, one-to-many or many-to-many; a junction table is commonly used for many-to-many relationships.\n\nACTIVITY: Design Student, Course and Enrolment tables. Mark the primary and foreign keys and draw the relationships."),
("Database design and integrity", "Good database design identifies entities, attributes, keys and relationships before implementation. Appropriate data types and constraints protect data quality. Normalisation reduces unnecessary duplication and update anomalies. Referential integrity ensures foreign-key references remain valid. Plan access permissions, validation and backups as part of database design.\n\nACTIVITY: Design a simple school database for students, subjects and marks. Identify possible duplicate data and explain how your design avoids it.")
]),
("S5 ICT - Unit 1: Google Sheets", "S5 ICT", "Spreadsheet creation, data entry, formatting, formulas, functions, charts and sharing.", [
("Getting started and spreadsheet structure", "Google Sheets is an online spreadsheet application. A spreadsheet contains sheets made of rows, columns and cells. Each cell has an address such as A1. Enter text, numbers, dates and other values into cells. Use clear sheet names and headings so data are easy to understand.\n\nACTIVITY: Create a class marks sheet with columns for student name and five subjects. Enter at least five sample records."),
("Formatting, formulas and functions", "Format cells to improve readability using number formats, alignment, borders, colours and appropriate column widths. Formulas begin with = and can use cell references and operators. Common functions include SUM, AVERAGE, COUNT, MIN and MAX. Relative references adjust when copied; absolute references use dollar signs to keep a row or column fixed.\n\nACTIVITY: Calculate each student's total and average. Use SUM, AVERAGE, COUNT, MIN and MAX and check the results manually."),
("Charts, collaboration and sharing", "Charts present spreadsheet data visually. Select an appropriate chart type for the comparison or trend being shown, and add a meaningful title and labels. Sharing controls determine who can view, comment or edit a spreadsheet. Check permissions before sharing and avoid exposing private student information.\n\nACTIVITY: Create a column chart of class averages and share the sheet with a classmate as a viewer.")
]),
("S5 ICT - Unit 2: Database Queries", "S5 ICT", "SQL querying, data manipulation, constraints, aggregate functions, filtering and sorting.", [
("Database queries and SQL environment", "A database query requests information or performs an operation on stored data. SQL is a language used with relational databases. A table contains columns and rows. SELECT retrieves data; FROM identifies the table. Choose only the columns needed and use clear aliases when appropriate.\n\nACTIVITY: Given Student and Marks tables, write SELECT statements to display all records and selected columns."),
("Data manipulation and constraints", "INSERT adds records, UPDATE changes existing records and DELETE removes records. Use WHERE to restrict UPDATE and DELETE to intended rows. Constraints such as PRIMARY KEY, FOREIGN KEY and NOT NULL protect integrity. A primary key uniquely identifies a row; a foreign key links related tables.\n\nACTIVITY: Write SQL to insert a student, update that student's email and delete a test record using a safe WHERE condition."),
("Aggregate functions, filtering and sorting", "COUNT counts rows or values; SUM totals numeric values; AVG calculates the mean; MIN and MAX return the smallest and largest values. WHERE filters rows using comparison and logical conditions. AND requires all conditions to be true; OR requires at least one. ORDER BY sorts results in ascending (ASC) or descending (DESC) order.\n\nACTIVITY: Query the number of students, average mark and highest mark. Filter marks above 70 and sort them from highest to lowest.")
]),
("S5 ICT - Unit 3: Python Programming II", "S5 ICT", "Functions, parameters, return values, local/global variables, lists and object-oriented programming.", [
("Functions and calling functions", "A function is a reusable block of code that performs a task. Python provides built-in functions and allows programmers to define their own with def. A function may receive parameters and return a result. Calling a function runs its body. Use meaningful names and divide complex tasks into smaller functions.\n\nACTIVITY: Write functions to calculate the area of a rectangle and the average of three numbers. Call each function with different arguments."),
("Local/global variables and lists", "A local variable is created inside a function and is normally available only there. A global variable is defined outside functions; avoid changing global state unnecessarily. Python lists are ordered, changeable collections. Create lists with square brackets, access elements by index (starting at zero), and modify, append, insert, remove or iterate through elements. Common methods include append, extend, insert, remove, pop, sort and reverse.\n\nACTIVITY: Store five marks in a list, calculate their average, add a new mark and display the sorted list."),
("Object-oriented programming: classes and objects", "Object-oriented programming organises software around classes and objects. A class defines attributes and methods; an object is an instance of a class. In Python, define a class with class and initialise instance attributes using __init__ and self. Create objects by calling the class, then access their attributes and methods.\n\nACTIVITY: Create a Student class with name and age attributes and a method that displays a student summary. Create and use two Student objects.")
]),
("S5 ICT - Unit 4: Machine Learning", "S5 ICT", "Data fundamentals, data preparation, analysis, ML concepts, algorithms, workflow and tools.", [
("Data fundamentals and quality", "Data are raw facts; information is processed data with meaning, and knowledge uses information to make decisions. Data may be numeric, categorical, text, image, audio or other formats. Sources include surveys, sensors, transactions and public datasets. Quality data should be accurate, complete, consistent, relevant, timely and valid.\n\nACTIVITY: Identify data sources for a school attendance project and describe how to check accuracy and completeness."),
("Data collection, preparation and analysis", "Data acquisition gathers data from appropriate sources. Preprocessing prepares data for analysis: cleaning errors, handling missing values, removing duplicates, treating outliers, integrating sources and transforming formats. Ethical collection requires a lawful purpose, transparency, privacy and secure storage. Descriptive statistics summarise observed data; inferential statistics use samples to draw conclusions about a population. Visualisations such as bar charts, line graphs and histograms reveal patterns.\n\nACTIVITY: Prepare a small dataset, identify missing or duplicate values and create a chart with a short interpretation."),
("Machine Learning foundations and workflow", "Artificial Intelligence is the broad field of systems performing tasks associated with intelligence. Machine Learning enables systems to learn patterns from data. Deep Learning uses multi-layer neural networks. Supervised learning uses labelled examples; unsupervised learning finds patterns in unlabelled data; reinforcement learning learns through feedback and rewards. A typical ML workflow defines a problem, gathers and prepares data, splits datasets, trains a model, evaluates it and improves it. Overfitting occurs when a model memorises training data and performs poorly on new data; underfitting occurs when it fails to learn important patterns.\n\nACTIVITY: Classify example tasks as supervised or unsupervised. Describe a model workflow and explain why separate training and test data are needed."),
("Machine Learning tools and evaluation", "Model evaluation depends on the task. Classification can use accuracy, precision, recall and F1-score; regression can use measures such as mean absolute error or mean squared error. Clustering uses measures suited to grouping quality. Tools in the notes include Google Teachable Machine, Scratch ML extensions and Python-based notebooks. Choose tools appropriate to the dataset, learner level and project.\n\nACTIVITY: Use Teachable Machine to create a simple image or sound classifier, test it with new examples and discuss errors and limitations.")
]),
("S5 ICT - Unit 5: Web Database Connectivity", "S5 ICT", "Web application components, frontend/backend design, forms, database connection and CRUD operations.", [
("Web application components and frontend/backend", "A web application commonly has a frontend (client side) and backend (server side). The frontend presents pages and collects user input using HTML, CSS and JavaScript. The backend processes requests, applies validation and business rules, and communicates with a database. A client sends a request; the server processes it and returns a response.\n\nACTIVITY: Draw a diagram showing browser, web server and database, and label the flow of a student registration request."),
("Forms and database design", "An HTML form collects information from users. Use labels and suitable input types and validate submitted values. Design database tables to store the information, selecting appropriate fields, data types and keys. Never trust client-side validation alone; validate on the server and use parameterised queries to protect against SQL injection.\n\nACTIVITY: Design a student registration form and a matching Student database table. Identify the primary key and required fields."),
("Connecting, inserting, retrieving, updating and deleting", "The backend connects to the database using a suitable database driver and protected connection settings. INSERT stores submitted form values; SELECT retrieves records for display; UPDATE changes selected records; DELETE removes selected records. Use parameterised statements, handle errors, restrict database permissions and confirm destructive operations.\n\nACTIVITY: Build or diagram a small registration workflow that inserts a student and displays stored records. Explain how you would update and delete a record safely.")
]),
("S5 ICT - Unit 6: Computer Networking", "S5 ICT", "Network concepts, benefits, connection types, LAN/MAN/WAN/PAN, devices, addressing and troubleshooting.", [
("Network fundamentals and types", "A computer network connects devices so they can exchange data and share resources. Networks support education, business, healthcare, banking, government and communication. Wired connections commonly use copper or fibre; wireless connections use radio. PAN covers personal devices, LAN a limited site, MAN a metropolitan area and WAN large geographic areas. Each type has different coverage, cost and management needs.\n\nACTIVITY: Classify a school computer lab, Bluetooth headset connection and international company network as PAN, LAN, MAN or WAN."),
("Network devices, addresses and configuration", "A hub broadcasts traffic; a switch forwards frames within a LAN; a router connects networks; a modem connects to a service provider; an access point provides Wi-Fi; a network interface card connects a device. A MAC address identifies a network interface at the link layer. An IP address is a logical address; IPv4 uses 32 bits. A subnet mask identifies the network portion, and a default gateway forwards traffic outside the local network. Packet Tracer can be used to place devices, connect cables and configure addresses.\n\nACTIVITY: Draw a small LAN with a switch, router and three PCs. Assign example IPv4 addresses and identify the default gateway."),
("Troubleshooting and connectivity testing", "Troubleshooting should proceed systematically: check power and cables, wireless connection, IP configuration, subnet mask, gateway and DNS. The ping command tests reachability using ICMP. Verify the connection and correct one suspected fault at a time. Packet Tracer can simulate network configuration and help practise troubleshooting. Record the problem, test and resolution.\n\nACTIVITY: Use Packet Tracer to connect two PCs through a switch, configure IP addresses and test connectivity. Change one address incorrectly and diagnose the fault.")
]),
("S5 ICT - Unit 7: Artificial Neural Networks", "S5 ICT", "ANN concepts, architecture, training, types, applications and ethics.", [
("Introduction to Artificial Neural Networks", "An Artificial Neural Network (ANN) is a computing model inspired by networks of biological neurons. It consists of connected units that process inputs using weights, biases and activation functions. AI is the broad field; Machine Learning is a way to learn patterns from data; neural networks are one family of ML models; deep learning uses neural networks with multiple layers.\n\nACTIVITY: Explain the relationship between AI, Machine Learning, ANN and Deep Learning using a labelled diagram."),
("Network architecture and training", "A basic neural network has an input layer, one or more hidden layers and an output layer. Inputs pass through weighted connections and activation functions to produce predictions. During training, the model compares predictions with target values and adjusts weights to reduce a loss function. Training data, validation data and test data have different roles. Types include deep neural networks and convolutional neural networks, which are often used for image tasks. Transfer learning reuses knowledge from a model trained on another dataset.\n\nACTIVITY: Draw and label an ANN with input, hidden and output layers. Describe how changing weights can improve predictions."),
("Applications and ethics of ANN", "ANNs can support image recognition, speech recognition and other pattern-recognition tasks. Their performance depends on representative data, suitable training and evaluation. Ethical issues include privacy, consent, bias, explainability, security and the impact of incorrect predictions. Human oversight is important, especially in high-impact decisions.\n\nACTIVITY: Choose an ANN application and discuss its benefits, possible errors, affected people and safeguards. If using a sample Python program, identify its inputs, outputs and training data.")
])
]

with app.app_context():
    for course_title, category, description, course_level, in []:
        pass
    for course_title, category, description, unit_lessons in curriculum_units:
        course_record = Course.query.filter_by(title=course_title).first()
        if course_record is None:
            course_record = Course(title=course_title, category=category, level=category, description=description)
            db.session.add(course_record)
            db.session.flush()
        # Add or repair only curriculum lesson titles that are absent; preserve existing lesson records.
        existing_titles = {x.title.strip().lower() for x in Lesson.query.filter_by(course_id=course_record.id).all()}
        next_position = db.session.query(db.func.max(Lesson.position)).filter_by(course_id=course_record.id).scalar() or 0
        for lesson_title, lesson_content in unit_lessons:
            if lesson_title.strip().lower() not in existing_titles:
                next_position += 1
                db.session.add(Lesson(course_id=course_record.id, title=lesson_title, content=lesson_content, position=next_position))
                existing_titles.add(lesson_title.strip().lower())
        db.session.commit()
