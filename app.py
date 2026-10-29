from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timezone
import sqlite3, os, re, secrets, hashlib, hmac
from difflib import SequenceMatcher

APP_NAME = "CampusMate AI"
DB_PATH = os.path.join(os.path.dirname(__file__), "campusmate.db")
app = Flask(__name__)
app.secret_key = os.environ.get("CAMPUSMATE_SECRET_KEY") or "dev-only-change-this-secret-key"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# IMPORTANT: Replace this clearly-labelled demo data with verified campus information.
CAMPUS_INFO = {
    "college_name": "Your College Name (edit config.py)",
    "library_hours": "Not verified yet",
    "office_hours": "Not verified yet",
    "help_email": "Add your official campus help email",
    "facilities": ["Library", "Computer labs", "Sports facilities", "Cafeteria"],
}
DIRECTORY = [
    {"name":"Central Library","category":"Study","building":"Update building / block","detail":"Add verified floor and room details."},
    {"name":"Computer Science Lab","category":"Laboratory","building":"Update building / block","detail":"Add verified floor and room details."},
    {"name":"Administrative Office","category":"Office","building":"Update building / block","detail":"Add verified office location."},
    {"name":"Cafeteria","category":"Food","building":"Update building / block","detail":"Add verified location and timings."},
    {"name":"Health Centre","category":"Services","building":"Update building / block","detail":"Add verified location and contact details."},
]
SAMPLE_NOTICES = [
    {"title":"Welcome to CampusMate","category":"General","message":"Your student companion is ready. Campus information shown here is demo content until verified.","date":"Pinned"},
    {"title":"Study smarter","category":"Study","message":"Break large topics into small sessions, then practise recalling what you learned.","date":"Pinned"},
]

def db():
    con=sqlite3.connect(DB_PATH)
    con.row_factory=sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL DEFAULT 0, title TEXT NOT NULL, subject TEXT DEFAULT '', due_date TEXT DEFAULT '', done INTEGER DEFAULT 0, created_at TEXT);
        CREATE TABLE IF NOT EXISTS skills(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, teaches TEXT NOT NULL, wants TEXT DEFAULT '', availability TEXT DEFAULT '', format TEXT DEFAULT '', contact TEXT DEFAULT '', consent INTEGER DEFAULT 0, created_at TEXT);
        CREATE TABLE IF NOT EXISTS lost_items(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, item TEXT NOT NULL, category TEXT DEFAULT '', colour TEXT DEFAULT '', place TEXT DEFAULT '', details TEXT DEFAULT '', created_at TEXT);
        CREATE TABLE IF NOT EXISTS issues(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, category TEXT DEFAULT '', place TEXT DEFAULT '', details TEXT DEFAULT '', status TEXT DEFAULT 'Submitted', created_at TEXT);
        """)
init_db()

# Add user_id safely when opening a database created by an earlier demo version.
with db() as con:
    task_columns = [row[1] for row in con.execute("PRAGMA table_info(tasks)").fetchall()]
    if "user_id" not in task_columns:
        con.execute("ALTER TABLE tasks ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")

def current_user():
    if not session.get("user_id"):
        return None
    with db() as con:
        row = con.execute("SELECT id,name,email FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return dict(row) if row else None

def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/"):
                return jsonify({"ok":False,"error":"Please log in to continue."}), 401
            return redirect(url_for("auth_page"))
        return view(*args, **kwargs)
    return wrapped

def password_digest(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000).hex()
    return f"{salt}${digest}"

def password_matches(password, stored):
    try:
        salt, expected = stored.split("$", 1)
        actual = password_digest(password, salt).split("$", 1)[1]
        return hmac.compare_digest(actual, expected)
    except ValueError:
        return False

def json_error(message, code=400):
    return jsonify({"ok":False,"error":message}), code

def clean(value, limit=240):
    return str(value or "").strip()[:limit]

def assistant_reply(message):
    q=message.lower().strip()
    if not q: return {"reply":"Ask me something about studying or campus life.","source":"CampusMate guide"}
    if re.search(r"\b(hi|hello|hey|good morning|good evening)\b",q):
        return {"reply":"Hey! ✨ I’m CampusMate, your student-sidekick. I can help you plan revision, explain topics, find campus services, and understand the demo features. What are we tackling?","source":"CampusMate"}
    if any(w in q for w in ["who are you","your name","what can you do","help me"]):
        return {"reply":"I’m CampusMate AI. I can: build a study plan, share learning strategies, search the campus directory, explain how Skill Exchange / Lost & Found / Green Campus work, and clarify what data is still demo-only. Try “make a 5-day Python revision plan” or “where is the library?”","source":"CampusMate guide"}
    if any(w in q for w in ["study plan","timetable","revision plan","exam in","days"]):
        days=re.search(r"(\d+)\s*[- ]?(day|days)",q)
        n=max(1,min(int(days.group(1)),30)) if days else 5
        topics=re.search(r"(?:topics?|subjects?)\s*:\s*(.+)",message,re.I)
        items=[x.strip(" .") for x in re.split(r",| and ",topics.group(1)) if x.strip()] if topics else ["Review key concepts","Work through examples","Practise questions","Review mistakes","Quick recap"]
        lines=[]
        for i in range(n):
            topic=items[i%len(items)]
            lines.append(f"Day {i+1}: {topic} — 25 min learning + 15 min active recall/practice.")
        return {"reply":"Here’s an editable starter plan. Adjust the workload to your available time:\n"+"\n".join(lines)+"\n\nTip: finish each session by writing down what still feels unclear.","source":"Generated study template"}
    if any(w in q for w in ["library","classroom","class room","lab","office","cafeteria","location","where is"]):
        term=next((w for w in ["library","computer science lab","cse lab","lab","office","cafeteria","health centre"] if w in q),"")
        match=next((d for d in DIRECTORY if term and (term in d["name"].lower() or term=="cse lab" and "computer science" in d["name"].lower())),None)
        if match:
            return {"reply":f"{match['name']}: {match['building']}. {match['detail']} This directory currently contains placeholder entries, so confirm the location with campus staff before relying on it.","source":"Campus directory · demo data"}
        return {"reply":"I can search the Campus Directory, but the current entries are placeholders. Add verified building, block, floor and room details before using directions. You can open the Classroom Finder section to browse entries.","source":"Campus directory · demo data"}
    if any(w in q for w in ["exam date","next exam","hall ticket","attendance","result","event date","when is"]):
        return {"reply":"I don’t have access to your college’s live exam calendar, attendance, results or event system. Check the official student portal or a verified college notice. If you paste a notice here, I can help explain its wording—but confirm dates with the issuing department.","source":"No verified calendar connected"}
    if any(w in q for w in ["notice","explain this","simple english"]):
        return {"reply":"Paste the notice text into the chat and I can help simplify it. I can’t verify whether a notice is official, so check its source and confirm important dates with the college.","source":"Notice helper"}
    if any(w in q for w in ["lost","missing","found","water bottle","wallet"]):
        return {"reply":"Open Lost & Found to submit a Lost or Found report. CampusMate compares category, colour, place and description to suggest possible matches. A suggestion is not proof of ownership; staff/owner confirmation is required. Keep private identifying details out of public descriptions.","source":"Lost & Found guide"}
    if any(w in q for w in ["skill","teach","peer","python helper","learn from"]):
        return {"reply":"Use Skill Exchange to list a skill you can teach and a topic you want help with. Matches are suggestions only. Contact information is hidden unless the student explicitly opts in to share it.","source":"Skill Exchange guide"}
    if any(w in q for w in ["leak","broken","maintenance","green campus","overflow","light"]):
        return {"reply":"Submit a Green Campus report with the issue type and location. Similar reports may be grouped into one case, then tracked as Submitted, In progress or Resolved. Please report urgent safety issues directly to campus staff too.","source":"Green Campus guide"}
    if any(w in q for w in ["voice","speak","telugu"]):
        return {"reply":"Tap the microphone beside the chat box and allow browser microphone access. Voice input depends on your browser and device; English is the default recognition language. Telugu support is a planned enhancement, not guaranteed in this demo.","source":"Voice assistant"}
    if any(w in q for w in ["thank","thanks"]):
        return {"reply":"Anytime! Go make something awesome happen today. 🌱","source":"CampusMate"}
    return {"reply":"I’m not fully sure about that yet. I can help with study planning, topic explanations, campus directory entries, notices you paste, Skill Exchange, Lost & Found, and Green Campus reports. I won’t invent campus dates or locations—those need verified data.","source":"CampusMate guide"}

@app.get("/auth")
def auth_page():
    if current_user(): return redirect(url_for("home"))
    return render_template("auth.html")

@app.post("/api/register")
def register():
    data=request.get_json(silent=True) or {}
    name=clean(data.get("name"),60)
    email=clean(data.get("email"),120).lower()
    password=str(data.get("password") or "")
    if len(name)<2: return json_error("Please enter your name.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email): return json_error("Enter a valid email address.")
    if len(password)<8: return json_error("Use a password with at least 8 characters.")
    try:
        with db() as con:
            cur=con.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",(name,email,password_digest(password),datetime.now(timezone.utc).isoformat()))
        session.clear(); session["user_id"]=cur.lastrowid
        return jsonify({"ok":True,"user":{"name":name,"email":email}}),201
    except sqlite3.IntegrityError:
        return json_error("An account with that email already exists.",409)

@app.post("/api/login")
def login():
    data=request.get_json(silent=True) or {}; email=clean(data.get("email"),120).lower(); password=str(data.get("password") or "")
    with db() as con: row=con.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
    if not row or not password_matches(password,row["password_hash"]): return json_error("Email or password is incorrect.",401)
    session.clear(); session["user_id"]=row["id"]
    return jsonify({"ok":True,"user":{"name":row["name"],"email":row["email"]}})

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok":True})

@app.get("/api/me")
@login_required
def me(): return jsonify({"ok":True,"user":current_user()})

@app.get("/")
@login_required
def home():
    return render_template("index.html", user=current_user())

@app.get("/api/health")
def health():
    return jsonify({"ok":True,"app":APP_NAME,"version":"2.0.0"})

@app.post("/api/chat")
@login_required
def chat():
    data=request.get_json(silent=True) or {}
    message=clean(data.get("message"),1000)
    if not message: return json_error("Please enter a message.")
    result=assistant_reply(message)
    return jsonify({"ok":True,**result,"timestamp":datetime.now(timezone.utc).isoformat()})

@app.get("/api/campus")
def campus():
    return jsonify({"ok":True,"college":CAMPUS_INFO,"directory":DIRECTORY,"verified":False})

@app.get("/api/notices")
def notices():
    return jsonify({"ok":True,"notices":SAMPLE_NOTICES,"verified":False})

@app.route("/api/tasks",methods=["GET","POST"])
@login_required
def tasks():
    if request.method=="GET":
        with db() as con: rows=con.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY done,due_date,id DESC",(session["user_id"],)).fetchall()
        return jsonify({"ok":True,"tasks":[dict(r) for r in rows]})
    d=request.get_json(silent=True) or {}; title=clean(d.get("title"),120)
    if not title:return json_error("Task title is required.")
    with db() as con:
        cur=con.execute("INSERT INTO tasks(user_id,title,subject,due_date,created_at) VALUES(?,?,?,?,?)",(session["user_id"],title,clean(d.get("subject"),60),clean(d.get("due_date"),10),datetime.now(timezone.utc).isoformat()))
        row=con.execute("SELECT * FROM tasks WHERE id=?",(cur.lastrowid,)).fetchone()
    return jsonify({"ok":True,"task":dict(row)}),201

@app.patch("/api/tasks/<int:task_id>")
@login_required
def update_task(task_id):
    d=request.get_json(silent=True) or {}
    with db() as con:
        cur=con.execute("UPDATE tasks SET done=? WHERE id=? AND user_id=?",(1 if d.get("done") else 0,task_id,session["user_id"]))
    if not cur.rowcount:return json_error("Task not found.",404)
    return jsonify({"ok":True})

@app.delete("/api/tasks/<int:task_id>")
@login_required
def delete_task(task_id):
    with db() as con: cur=con.execute("DELETE FROM tasks WHERE id=? AND user_id=?",(task_id,session["user_id"]))
    if not cur.rowcount:return json_error("Task not found.",404)
    return jsonify({"ok":True})

@app.get("/api/directory")
@login_required
def directory():
    q=clean(request.args.get("q"),100).lower()
    items=[x for x in DIRECTORY if not q or q in (x["name"]+" "+x["category"]+" "+x["building"]).lower()]
    return jsonify({"ok":True,"items":items,"verified":False})

@app.route("/api/skills",methods=["GET","POST"])
@login_required
def skills():
    if request.method=="GET":
        with db() as con: rows=con.execute("SELECT id,name,teaches,wants,availability,format,consent,created_at FROM skills ORDER BY id DESC").fetchall()
        return jsonify({"ok":True,"skills":[dict(r) for r in rows]})
    d=request.get_json(silent=True) or {}
    name=clean(d.get("name"),60); teaches=clean(d.get("teaches"),100)
    if not name or not teaches:return json_error("Name and skill to teach are required.")
    with db() as con:
        cur=con.execute("INSERT INTO skills(name,teaches,wants,availability,format,contact,consent,created_at) VALUES(?,?,?,?,?,?,?,?)",(name,teaches,clean(d.get("wants"),100),clean(d.get("availability"),100),clean(d.get("format"),40),clean(d.get("contact"),120),1 if d.get("consent") else 0,datetime.now(timezone.utc).isoformat()))
        rows=con.execute("SELECT id,name,teaches,wants,availability,format,consent FROM skills ORDER BY id DESC").fetchall()
    return jsonify({"ok":True,"id":cur.lastrowid,"matches":[dict(r) for r in rows if d.get("wants") and d.get("wants").lower() in (r["teaches"] or "").lower()]}),201

def item_similarity(a,b):
    fields=["item","category","colour","place","details"]
    vals=[]
    for f in fields:
        x=(a.get(f) or "").lower(); y=(b.get(f) or "").lower()
        if x and y: vals.append(SequenceMatcher(None,x,y).ratio())
    return sum(vals)/len(vals) if vals else 0

@app.route("/api/lost-found",methods=["GET","POST"])
@login_required
def lost_found():
    if request.method=="GET":
        with db() as con: rows=con.execute("SELECT * FROM lost_items ORDER BY id DESC").fetchall()
        return jsonify({"ok":True,"items":[dict(r) for r in rows]})
    d=request.get_json(silent=True) or {}; kind=clean(d.get("kind"),10).lower(); item=clean(d.get("item"),100)
    if kind not in ["lost","found"] or not item:return json_error("Choose Lost or Found and enter an item description.")
    record={k:clean(d.get(k),180) for k in ["item","category","colour","place","details"]}
    with db() as con:
        cur=con.execute("INSERT INTO lost_items(kind,item,category,colour,place,details,created_at) VALUES(?,?,?,?,?,?,?)",(kind,record["item"],record["category"],record["colour"],record["place"],record["details"],datetime.now(timezone.utc).isoformat()))
        rows=con.execute("SELECT * FROM lost_items WHERE kind!=? ORDER BY id DESC",(kind,)).fetchall()
    matches=[]
    for row in rows:
        score=item_similarity(record,dict(row))
        if score>=0.24: matches.append({"id":row["id"],"kind":row["kind"],"item":row["item"],"colour":row["colour"],"place":row["place"],"score":round(score*100)})
    matches.sort(key=lambda x:x["score"],reverse=True)
    return jsonify({"ok":True,"id":cur.lastrowid,"matches":matches[:5],"note":"Possible matches only. Confirm ownership with the owner or campus staff."}),201

@app.route("/api/issues",methods=["GET","POST"])
@login_required
def issues():
    if request.method=="GET":
        with db() as con: rows=con.execute("SELECT * FROM issues ORDER BY id DESC").fetchall()
        return jsonify({"ok":True,"issues":[dict(r) for r in rows]})
    d=request.get_json(silent=True) or {}; title=clean(d.get("title"),100); place=clean(d.get("place"),100)
    if not title or not place:return json_error("Issue and location are required.")
    category=clean(d.get("category"),40)
    with db() as con:
        rows=con.execute("SELECT * FROM issues WHERE status!='Resolved'").fetchall()
        duplicate=next((r for r in rows if SequenceMatcher(None,(r["title"]+" "+r["place"]).lower(),(title+" "+place).lower()).ratio()>.72),None)
        if duplicate:
            return jsonify({"ok":True,"duplicate":True,"issue":dict(duplicate),"message":"This looks similar to an existing report. We linked you to that case instead of creating another."})
        cur=con.execute("INSERT INTO issues(title,category,place,details,created_at) VALUES(?,?,?,?,?)",(title,category,place,clean(d.get("details"),300),datetime.now(timezone.utc).isoformat()))
        row=con.execute("SELECT * FROM issues WHERE id=?",(cur.lastrowid,)).fetchone()
    return jsonify({"ok":True,"duplicate":False,"issue":dict(row)}),201

@app.patch("/api/issues/<int:issue_id>")
@login_required
def update_issue(issue_id):
    d=request.get_json(silent=True) or {}; status=clean(d.get("status"),20)
    if status not in ["Submitted","In progress","Resolved"]:return json_error("Invalid status.")
    with db() as con: cur=con.execute("UPDATE issues SET status=? WHERE id=?",(status,issue_id))
    if not cur.rowcount:return json_error("Issue not found.",404)
    return jsonify({"ok":True})

@app.errorhandler(404)
def not_found(_): return jsonify({"ok":False,"error":"That page or API endpoint was not found."}),404
@app.errorhandler(405)
def method_not_allowed(_): return jsonify({"ok":False,"error":"That action is not allowed here."}),405

if __name__=="__main__":
    app.run(host="127.0.0.1",port=int(os.environ.get("PORT",5000)),debug=False)
