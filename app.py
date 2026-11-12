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
=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)))

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
