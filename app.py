from __future__ import annotations

import json
import os
import random
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).parent
DB_PATH = ROOT / "careerbrigade.db"
UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get("CAREERBRIGADE_SECRET", "development-key-change-before-deploy")
app.permanent_session_lifetime = timedelta(days=30)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

COMPANIES = ["Infosys", "Capgemini", "Microsoft", "Google", "TCS", "Wipro", "Accenture", "Amazon", "Cognizant", "IBM"]
LANGUAGES = ["Python", "Java", "C", "C++", "JavaScript", "HTML & CSS", "SQL", "C#", "PHP", "Kotlin", "Swift", "Go"]

APTITUDE = [
    ("A train travels 180 km in 3 hours. What is its average speed?", ["45 km/h", "60 km/h", "75 km/h", "90 km/h"], "60 km/h", "Speed = distance ÷ time = 180 ÷ 3."),
    ("What is 25% of 240?", ["40", "50", "60", "80"], "60", "25% is one quarter; 240 ÷ 4 = 60."),
    ("If 3x + 5 = 20, what is x?", ["3", "5", "7", "15"], "5", "Subtract 5 and divide by 3."),
    ("A bag has 3 red and 2 blue balls. Probability of red?", ["2/5", "3/5", "1/2", "3/2"], "3/5", "There are 3 red balls out of 5 total."),
    ("Find the next number: 2, 6, 12, 20, 30, ?", ["36", "40", "42", "44"], "42", "The pattern is n × (n+1): 1×2, 2×3, …, 6×7."),
    ("A product costs ₹800 after a 20% discount. What was the original price?", ["₹960", "₹1,000", "₹1,020", "₹1,200"], "₹1,000", "₹800 is 80% of the original price."),
    ("The average of 8, 12, 16 and 24 is:", ["14", "15", "16", "18"], "15", "(8 + 12 + 16 + 24) ÷ 4 = 15."),
    ("If 5 workers finish a task in 12 days, how many days for 10 workers at the same rate?", ["3", "6", "12", "24"], "6", "Workers and days are inversely proportional."),
    ("Choose the word closest in meaning to 'concise'.", ["Brief", "Unclear", "Careful", "Polite"], "Brief", "Concise means brief and to the point."),
    ("All roses are flowers. Some flowers fade quickly. Which conclusion is certain?", ["All roses fade quickly", "Some roses fade quickly", "All roses are flowers", "No flowers are roses"], "All roses are flowers", "This is exactly the stated universal premise."),
]
LOGICAL = [
    ("Find the next number: 3, 6, 12, 24, ?", ["36", "42", "48", "54"], "48", "Each number is multiplied by 2."),
    ("If CAT is coded as DBU, how is DOG coded?", ["EPH", "CNG", "FQI", "EOG"], "EPH", "Move each letter one step forward."),
    ("Riya is taller than Amit. Amit is taller than Neha. Who is shortest?", ["Riya", "Amit", "Neha", "Cannot say"], "Neha", "The order is Riya > Amit > Neha."),
    ("Choose the odd one out.", ["Square", "Triangle", "Circle", "Cube"], "Cube", "Cube is three-dimensional; the others are plane shapes."),
    ("A is the brother of B. B is the sister of C. What is A to C?", ["Brother", "Sister", "Father", "Cannot say"], "Brother", "A is male and is B's sibling; B and C are siblings."),
    ("If today is Tuesday, what day will it be after 10 days?", ["Thursday", "Friday", "Saturday", "Sunday"], "Friday", "Ten days later is three days after Tuesday."),
    ("Complete the pattern: AZ, BY, CX, ?", ["DW", "EV", "DU", "EX"], "DW", "First letters move forward; second letters move backward."),
    ("All pens are blue. This object is a pen. What follows?", ["It is blue", "It is red", "It is not blue", "Cannot say"], "It is blue", "The object belongs to the group of pens."),
    ("Five people stand in a row. Sam is before Jo and after Lee. Who is in the middle of these three?", ["Sam", "Jo", "Lee", "Cannot say"], "Sam", "Their order is Lee, Sam, Jo."),
    ("Which number does not fit: 4, 9, 16, 20, 25?", ["4", "16", "20", "25"], "20", "The others are perfect squares."),
]
GROUP_BANK = [
    ("A teammate disagrees with your idea during a group task. What is the best first response?", ["Listen and ask them to explain", "Interrupt and repeat your idea", "Ignore the teammate", "Ask to leave the task"], "Listen and ask them to explain", "Respectful listening helps the group compare ideas."),
    ("Your group is running out of time. What should you do?", ["Agree on priorities and divide tasks", "Let one person do everything", "Stop discussing", "Start a new topic"], "Agree on priorities and divide tasks", "A quick plan and clear roles help the group finish."),
]
HR_BANK = [
    ("What is a strong way to answer 'Tell me about yourself'?", ["Give a brief, role-related introduction", "Read your full resume word for word", "Discuss unrelated personal details", "Say only your name"], "Give a brief, role-related introduction", "Connect your background, skills and interest in the role."),
    ("You made a mistake at work. What should you do first?", ["Be honest, explain the fix and learn from it", "Hide it from everyone", "Blame a teammate", "Wait for someone else to notice"], "Be honest, explain the fix and learn from it", "Accountability and a clear correction build trust."),
]
GK_BANK = [
    ("Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Mercury"], "Mars", "Iron oxide gives Mars its reddish appearance."),
    ("What is the capital of India?", ["Mumbai", "New Delhi", "Kolkata", "Chennai"], "New Delhi", "New Delhi is India's capital."),
    ("Which is the largest ocean on Earth?", ["Atlantic", "Indian", "Arctic", "Pacific"], "Pacific", "The Pacific Ocean is the largest."),
    ("How many sides does a hexagon have?", ["5", "6", "7", "8"], "6", "A hexagon is a six-sided polygon."),
    ("Which gas do plants absorb during photosynthesis?", ["Oxygen", "Nitrogen", "Carbon dioxide", "Hydrogen"], "Carbon dioxide", "Plants use carbon dioxide, water and light to make sugars."),
]
COUNTRY_FACTS = [
    ("India","New Delhi","Asia"),("Japan","Tokyo","Asia"),("China","Beijing","Asia"),("South Korea","Seoul","Asia"),("Thailand","Bangkok","Asia"),("Vietnam","Hanoi","Asia"),("Philippines","Manila","Asia"),("Indonesia","Jakarta","Asia"),("Malaysia","Kuala Lumpur","Asia"),("Singapore","Singapore","Asia"),("Nepal","Kathmandu","Asia"),("Bhutan","Thimphu","Asia"),("Bangladesh","Dhaka","Asia"),("Pakistan","Islamabad","Asia"),("Afghanistan","Kabul","Asia"),("Saudi Arabia","Riyadh","Asia"),("United Arab Emirates","Abu Dhabi","Asia"),("Qatar","Doha","Asia"),("France","Paris","Europe"),("Germany","Berlin","Europe"),("Italy","Rome","Europe"),("Spain","Madrid","Europe"),("Portugal","Lisbon","Europe"),("United Kingdom","London","Europe"),("Ireland","Dublin","Europe"),("Norway","Oslo","Europe"),("Sweden","Stockholm","Europe"),("Finland","Helsinki","Europe"),("Denmark","Copenhagen","Europe"),("Poland","Warsaw","Europe"),("Austria","Vienna","Europe"),("Greece","Athens","Europe"),("Iceland","Reykjavik","Europe"),("Belgium","Brussels","Europe"),("Netherlands","Amsterdam","Europe"),("Switzerland","Bern","Europe"),("Czechia","Prague","Europe"),("Romania","Bucharest","Europe"),("Ukraine","Kyiv","Europe"),("Canada","Ottawa","North America"),("United States","Washington, D.C.","North America"),("Mexico","Mexico City","North America"),("Cuba","Havana","North America"),("Jamaica","Kingston","North America"),("Brazil","Brasilia","South America"),("Argentina","Buenos Aires","South America"),("Chile","Santiago","South America"),("Peru","Lima","South America"),("Colombia","Bogota","South America"),("Australia","Canberra","Oceania"),("New Zealand","Wellington","Oceania"),("Fiji","Suva","Oceania"),("Egypt","Cairo","Africa"),("Kenya","Nairobi","Africa"),("Nigeria","Abuja","Africa"),("South Africa","Pretoria","Africa"),("Ghana","Accra","Africa"),("Ethiopia","Addis Ababa","Africa"),("Tanzania","Dodoma","Africa"),("Morocco","Rabat","Africa"),("Algeria","Algiers","Africa"),("Senegal","Dakar","Africa")
]
TECH = {
    "Python": [("What does len([2, 4, 6]) return?", ["2", "3", "6", "Error"], "3", "len returns the number of items."), ("Which keyword defines a function?", ["func", "def", "function", "lambda"], "def", "Python uses def to define a named function."), ("What is the result of 7 // 2?", ["3", "3.5", "4", "1"], "3", "// performs floor division."), ("Which type is immutable?", ["list", "dict", "set", "tuple"], "tuple", "A tuple cannot be modified after creation."), ("What does range(3) produce?", ["0, 1, 2", "1, 2, 3", "0, 1, 2, 3", "3"], "0, 1, 2", "The stop value is excluded." )],
    "Java": [("Which keyword creates an object?", ["new", "class", "this", "make"], "new", "The new operator instantiates a class."), ("Which type stores true or false?", ["int", "boolean", "String", "char"], "boolean", "boolean is Java's logical type."), ("Java source is compiled to:", ["Native code only", "Bytecode", "HTML", "SQL"], "Bytecode", "The JVM runs compiled Java bytecode."), ("Which collection does not allow duplicate elements?", ["List", "Set", "ArrayList", "Queue"], "Set", "Set implementations hold unique elements."), ("Which keyword inherits a class?", ["implements", "extends", "inherits", "super"], "extends", "A Java class extends another class." )],
    "JavaScript": [("Which keyword declares a block-scoped variable?", ["var", "let", "define", "dim"], "let", "let is block-scoped."), ("What does typeof [] return?", ["array", "object", "list", "undefined"], "object", "Arrays are objects in JavaScript."), ("Which method adds to the end of an array?", ["push", "pop", "shift", "join"], "push", "push appends an element."), ("JSON stands for:", ["Java Source Object Notation", "JavaScript Object Notation", "Joined Syntax Object Names", "None"], "JavaScript Object Notation", "JSON is a text data interchange format."), ("Which value represents intentional absence?", ["null", "NaN", "false", "0"], "null", "null is an intentional empty value." )],
    "SQL": [("Which clause filters rows?", ["ORDER BY", "WHERE", "GROUP BY", "JOIN"], "WHERE", "WHERE filters rows before grouping."), ("Which function counts rows?", ["SUM()", "TOTAL()", "COUNT()", "NUMBER()"], "COUNT()", "COUNT returns a row or value count."), ("Which command retrieves data?", ["SELECT", "FETCH", "OPEN", "READ"], "SELECT", "SELECT queries data."), ("A primary key must be:", ["Unique", "Nullable", "Repeated", "Text"], "Unique", "A primary key uniquely identifies each row."), ("Which join returns matching rows in both tables?", ["LEFT JOIN", "INNER JOIN", "CROSS JOIN", "FULL JOIN"], "INNER JOIN", "INNER JOIN returns rows matching the join condition." )],
}

def connect_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None: db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password TEXT NOT NULL, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS profiles(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, phone TEXT DEFAULT '', college TEXT DEFAULT '', degree TEXT DEFAULT '', skills TEXT DEFAULT '', github TEXT DEFAULT '', linkedin TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, category TEXT NOT NULL, label TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS activities(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, text TEXT NOT NULL, kind TEXT NOT NULL, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS resumes(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, filename TEXT NOT NULL, score INTEGER NOT NULL, data TEXT NOT NULL, updated TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS used_questions(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, question TEXT NOT NULL, created TEXT NOT NULL, PRIMARY KEY(user_id, question));
    """)
    db.commit(); db.close()

def now(): return datetime.now(timezone.utc).isoformat()

def logged_in(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        if not session.get("user_id"): return jsonify(error="Please log in first."), 401
        return fn(*args, **kwargs)
    return inner

def activity(db, uid, text, kind="general"):
    db.execute("INSERT INTO activities(user_id,text,kind,created) VALUES(?,?,?,?)", (uid, text, kind, now()))
    db.commit()

@app.get("/")
def home(): return send_from_directory(app.static_folder, "index.html")

@app.post("/api/register")
def register():
    data=request.get_json() or {}; name=data.get("name","").strip(); email=data.get("email","").strip().lower(); pw=data.get("password","")
    if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email): return jsonify(error="Enter your name and a valid email address."),400
    if len(pw)<8 or not re.search(r"[A-Z]",pw) or not re.search(r"[a-z]",pw) or not re.search(r"\d",pw) or not re.search(r"[^A-Za-z0-9]",pw): return jsonify(error="Password needs 8+ characters with uppercase, lowercase, a number and a special character."),400
    db=connect_db()
    try:
        cur=db.execute("INSERT INTO users(name,email,password,created) VALUES(?,?,?,?)",(name,email,generate_password_hash(pw),now())); uid=cur.lastrowid
        db.execute("INSERT INTO profiles(user_id) VALUES(?)",(uid,)); db.commit()
    except sqlite3.IntegrityError: return jsonify(error="An account with this email already exists."),409
    session["user_id"]=uid; activity(db,uid,"Welcome to CareerBrigade! Your account is ready.","welcome")
    return jsonify(user={"id":uid,"name":name,"email":email})

@app.post("/api/login")
def login():
    d=request.get_json() or {}; db=connect_db(); user=db.execute("SELECT * FROM users WHERE email=?",(d.get("email","").strip().lower(),)).fetchone()
    if not user or not check_password_hash(user["password"],d.get("password","")): return jsonify(error="Email or password is incorrect."),401
    session["user_id"]=user["id"]; session.permanent=bool(d.get("remember"))
    return jsonify(user={"id":user["id"],"name":user["name"],"email":user["email"]},remember=bool(d.get("remember")))

@app.post("/api/logout")
def logout(): session.clear(); return jsonify(ok=True)

@app.post("/api/shutdown")
@logged_in
def shutdown():
    server = app.config.get("server_instance")
    if server is None: return jsonify(error="Start the app with python app.py to use Close Project."), 400
    print("[CareerBrigade] Close requested. Shutting down the local server...", flush=True)
    threading.Timer(0.8, server.shutdown).start()
    return jsonify(ok=True, message="CareerBrigade is closing. Check the terminal.")

@app.get("/api/dashboard")
@logged_in
def dashboard():
    db=connect_db(); uid=session["user_id"]; user=db.execute("SELECT id,name,email FROM users WHERE id=?",(uid,)).fetchone()
    results=[dict(r) for r in db.execute("SELECT category,label,score,total,created FROM results WHERE user_id=? ORDER BY id DESC",(uid,))]
    latest={}
    for r in results: latest.setdefault(r["category"],r)
    resume=db.execute("SELECT score,data,filename FROM resumes WHERE user_id=?",(uid,)).fetchone()
    profile=db.execute("SELECT * FROM profiles WHERE user_id=?",(uid,)).fetchone()
    acts=[dict(r) for r in db.execute("SELECT text,kind,created FROM activities WHERE user_id=? ORDER BY id DESC LIMIT 8",(uid,))]
    return jsonify(user=dict(user),scores={k:v["score"] for k,v in latest.items()},resume=dict(resume) if resume else None,profile=dict(profile) if profile else {},activities=acts,results=results[:20])

@app.post("/api/profile")
@logged_in
def save_profile():
    d=request.get_json() or {}; uid=session["user_id"]; db=connect_db()
    db.execute("UPDATE profiles SET phone=?,college=?,degree=?,skills=?,github=?,linkedin=? WHERE user_id=?",tuple(d.get(k,"").strip() for k in ["phone","college","degree","skills","github","linkedin"])+(uid,)); db.commit()
    activity(db,uid,"Updated your profile.","profile"); return jsonify(ok=True)

@app.post("/api/resume")
@logged_in
def resume():
    f=request.files.get("resume")
    if not f or not f.filename.lower().endswith((".pdf",".docx")): return jsonify(error="Please choose a PDF or DOCX resume."),400
    raw=f.read()
    if len(raw)>8*1024*1024: return jsonify(error="File is larger than 8 MB."),400
    text=""
    try:
        if f.filename.lower().endswith(".docx"):
            from docx import Document
            import io
            text=" ".join(p.text for p in Document(io.BytesIO(raw)).paragraphs)
        else:
            import fitz
            doc=fitz.open(stream=raw,filetype="pdf"); text=" ".join(page.get_text() for page in doc)
    except ImportError: return jsonify(error="Resume parser is unavailable. Run pip install -r requirements.txt."),500
    except Exception: return jsonify(error="We couldn't read that document. Please upload a valid PDF or DOCX."),400
    text=text.lower(); skills=["python","java","sql","javascript","html","css","communication","teamwork","data structures","machine learning","flask","git","leadership","problem solving"]
    found=[s for s in skills if s in text]; missing=[s for s in skills if s not in text]
    checks={"Contact details":bool(re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}",text)),"Education":any(w in text for w in ["education","bachelor","degree","university","college"]),"Skills section":"skill" in text,"Projects section":"project" in text,"Experience / internship":any(w in text for w in ["intern","experience","employment"]),"Certifications":"certif" in text,"GitHub profile":"github" in text,"LinkedIn profile":"linkedin" in text}
    score=min(98,round((sum(checks.values())/len(checks))*65+(min(len(found),7)/7)*35)); suggestions=[]
    if not checks["Projects section"]: suggestions.append("Add 2–3 projects with measurable results and the tools you used.")
    if not checks["Experience / internship"]: suggestions.append("Include internship, volunteering or practical experience.")
    if not checks["Certifications"]: suggestions.append("Add relevant course certificates to strengthen your profile.")
    if not checks["GitHub profile"]: suggestions.append("Add a GitHub link with pinned, documented projects.")
    if missing: suggestions.append("Build evidence for these in-demand skills: "+", ".join(missing[:5])+".")
    report={"score":score,"found":found,"missing":missing,"checks":checks,"suggestions":suggestions or ["Great coverage. Tailor keywords to each job description and quantify achievements."],"wordCount":len(text.split())}
    db=connect_db(); db.execute("INSERT INTO resumes(user_id,filename,score,data,updated) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET filename=excluded.filename,score=excluded.score,data=excluded.data,updated=excluded.updated",(session["user_id"],f.filename,score,json.dumps(report),now())); db.commit(); activity(db,session["user_id"],"Uploaded and analysed resume · ATS score "+str(score)+"%","resume")
    return jsonify(report)

def mcq(prompt, answer, distractors, explanation, rng):
    answer = str(answer)
    options = [answer]
    for item in distractors:
        item = str(item)
        if item not in options: options.append(item)
        if len(options) == 4: break
    filler = 1
    while len(options) < 4:
        item = f"Option {filler}"; filler += 1
        if item not in options: options.append(item)
    rng.shuffle(options)
    return {"question": prompt, "options": options, "answer": answer, "explanation": explanation}

def number_choices(answer, rng, step=1):
    return [answer + step, answer - step, answer + 2 * step]

def aptitude_question(i, level, rng, label=""):
    hard = level.lower() == "hard"; medium = level.lower() == "medium"
    scale = (20 if hard else 8 if medium else 3)
    kind = i % 10
    if kind == 0:
        b=rng.randint(4,18)*scale; t=rng.randint(2,9); answer=b*t
        q=f"A car covers {answer} km in {t} hours. What is its average speed in km/h?"; exp=f"Speed = distance ÷ time = {answer} ÷ {t} = {b} km/h."
        return mcq(q,b,number_choices(b,rng),exp,rng)
    if kind == 1:
        p=rng.choice([5,10,12,15,20,25,30,40,50]); base=rng.randint(4,30)*20*scale//4; answer=base*p//100
        return mcq(f"What is {p}% of {base}?",answer,number_choices(answer,rng,max(1,scale)),f"{base} × {p} ÷ 100 = {answer}.",rng)
    if kind == 2:
        a=rng.randint(2,12); b=rng.randint(2,12); factor=rng.randint(3,16)*scale; total=(a+b)*factor; answer=a*factor
        return mcq(f"A sum of ₹{total} is divided in the ratio {a}:{b}. How much does the first share receive?",f"₹{answer}",[f"₹{answer+factor}",f"₹{max(1,answer-factor)}",f"₹{total//2}"],f"One ratio part is ₹{factor}; the first share is {a} × ₹{factor} = ₹{answer}.",rng)
    if kind == 3:
        principal=rng.randint(10,100)*100*scale; rate=rng.choice([4,5,6,8,10,12]); years=rng.randint(1,5); answer=principal*rate*years//100
        return mcq(f"Find the simple interest on ₹{principal} at {rate}% per year for {years} years.",f"₹{answer}",[f"₹{answer+principal//100}",f"₹{max(1,answer-principal//100)}",f"₹{principal*rate//100}"],f"Simple interest = principal × rate × time ÷ 100 = ₹{answer}.",rng)
    if kind == 4:
        nums=[rng.randint(5,80)*scale for _ in range(4)]; answer=round(sum(nums)/4,2)
        return mcq(f"Find the mean of {', '.join(map(str,nums))}.",answer,number_choices(answer,rng,max(1,scale)),f"Add the four values and divide by 4: {sum(nums)} ÷ 4 = {answer}.",rng)
    if kind == 5:
        marked=rng.randint(20,120)*100*scale; discount=rng.choice([5,10,15,20,25,30]); answer=marked*(100-discount)//100
        return mcq(f"A bag marked at ₹{marked} is discounted by {discount}%. What is its sale price?",f"₹{answer}",[f"₹{marked-answer}",f"₹{answer+marked//20}",f"₹{marked}"],f"Sale price = ₹{marked} × {100-discount}% = ₹{answer}.",rng)
    if kind == 6:
        workers=rng.randint(2,12); days=rng.randint(3,24)*scale; new_workers=workers*rng.choice([2,3,4]); answer=days*workers//new_workers
        return mcq(f"{workers} workers finish a job in {days} days. At the same rate, how many days will {new_workers} workers need?",answer,number_choices(answer,rng,max(1,scale)),f"Work is constant: {workers} × {days} = {new_workers} × days, so days = {answer}.",rng)
    if kind == 7:
        start=rng.randint(2,25)*scale; step=rng.randint(2,10)*scale; seq=[start+j*step for j in range(5)]; answer=seq[-1]+step
        return mcq(f"Find the next term: {', '.join(map(str,seq))}, ?",answer,number_choices(answer,rng,max(1,step)),f"The sequence increases by {step} each time; the next term is {answer}.",rng)
    if kind == 8:
        a=rng.randint(2,15); x=rng.randint(2,20)*scale; b=rng.randint(1,30)*scale; c=a*x+b
        answer=x
        return mcq(f"Solve for x: {a}x + {b} = {c}.",answer,[x+a,x-b,x*2],f"Subtract {b} from both sides and divide by {a}: x = {answer}.",rng)
    red=rng.randint(2,12)*scale; blue=rng.randint(2,12)*scale; sample=red+blue; answer=f"{red}/{sample}"
    return mcq(f"A box contains {red} red and {blue} blue counters. What is the probability of drawing a red counter?",answer,[f"{blue}/{sample}",f"{red}/{max(1,sample-1)}",f"1/{sample}"],f"Probability = favourable outcomes ÷ total outcomes = {red}/{sample}.",rng)

def logical_question(i, level, rng):
    n=rng.randint(2,30); step=rng.randint(2,15)*(3 if level.lower()=="hard" else 2 if level.lower()=="medium" else 1); kind=i%8
    if kind==0:
        seq=[n+j*step for j in range(5)]; ans=seq[-1]+step
        return mcq(f"Find the next number in the sequence {', '.join(map(str,seq))}, ?",ans,number_choices(ans,rng,step),f"The sequence increases by {step} each time.",rng)
    if kind==1:
        factor=rng.choice([2,3]); seq=[n*(factor**j) for j in range(4)]; ans=seq[-1]*factor
        return mcq(f"Complete the pattern: {', '.join(map(str,seq))}, ?",ans,[ans+factor,ans-factor,ans*factor],f"Each term is multiplied by {factor}.",rng)
    if kind==2:
        shift=rng.randint(1,5); word='CODE'; encoded=''.join(chr((ord(c)-65+shift)%26+65) for c in word)
        target='MATH'; result=''.join(chr((ord(c)-65+shift)%26+65) for c in target)
        return mcq(f"A code shifts every letter in CODE forward by {shift} places to make {encoded}. What does MATH become?",result,[target,encoded,result[:-1]+'Z',result[1:]+result[0]],f"Move each letter of MATH forward by {shift} places.",rng)
    if kind==3:
        names=rng.sample(["Asha","Ravi","Mina","Kabir","Tara","Dev","Nina","Omar","Leela","Ishaan"],3)
        return mcq(f"{names[0]} is taller than {names[1]}, and {names[1]} is taller than {names[2]}. Who is shortest?",names[2],names[:2]+["Cannot be determined"],f"The height order is {names[0]} > {names[1]} > {names[2]}.",rng)
    if kind==4:
        start=rng.randint(1,6); days=rng.randint(8,80); day=(start+days%7-1)%7+1; names=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        return mcq(f"If day {start} of the week is {names[start-1]}, what day will it be {days} days later?",names[day-1],[names[(day+j)%7] for j in [1,2,3]],f"{days} days is {days%7} week-days forward.",rng)
    if kind==5:
        a=rng.randint(2,20); b=rng.randint(2,20); c=rng.randint(2,20); answer=a+b+c
        return mcq(f"Jay has {c} points. Noor has {b} more than Jay, and Priya has {a} more than Noor. How many points does Priya have?",answer,[c+b,c+a,answer+a],f"Noor has {c}+{b}; Priya has {c}+{b}+{a} = {answer}.",rng)
    if kind==6:
        distance=rng.randint(2,12); turns=rng.choice([2,4,6,8]); return mcq(f"A person walks {distance} km north, turns right, then walks {distance} km. Which direction are they facing?", "East",["West","North","South"],"Facing north, a right turn points east.",rng)
    x=rng.randint(3,20); return mcq(f"All devices in Room {x} are tested. This tablet is in Room {x}. What must be true?","The tablet is tested",["The tablet is broken","The tablet is new","The tablet is not tested"],"The rule applies to every device in that room.",rng)

def technical_question(i, language, level, rng):
    # Each problem uses fresh values and a language-specific code fragment.
    if language=="HTML & CSS":
        k=i%4; token=f"card{rng.randint(10,9999)}"; tag=rng.choice(["article","section","button","header","nav","aside"]); attr=rng.choice(["data-role","aria-label","data-state","title"]); value=f"v{rng.randint(10,9999)}"
        if k==0: return mcq(f"In CSS, which selector targets elements with class='{token}'?",f".{token}",[f"#{token}",token,f"[{token}]"],"A class selector starts with a period.",rng)
        if k==1: return mcq(f"In CSS, which selector targets the element whose id is '{token}'?",f"#{token}",[f".{token}",token,f"[{token}]"],"An ID selector starts with #.",rng)
        if k==2: return mcq(f"Which CSS selector targets every <{tag}> element?",tag,[f".{tag}",f"#{tag}",f"[{tag}]"],"A type selector is written using the HTML tag name.",rng)
        return mcq(f"Which CSS selector matches elements with {attr}=\"{value}\"?",f"[{attr}=\"{value}\"]",[f".{attr}",f"#{attr}",f"{attr}=\"{value}\""],"Attribute selectors use square brackets around the attribute test.",rng)
    if language=="SQL":
        nums=[rng.randint(10,90) for _ in range(5)]; threshold=sorted(nums)[rng.randrange(1,4)]; kind=i%4
        if kind==0:
            ans=sum(nums); q=f"For the rows with scores {', '.join(map(str,nums))}, what does SELECT SUM(score) return?"; exp=f"SUM adds every score: {ans}."
        elif kind==1:
            ans=sum(v>threshold for v in nums); q=f"Scores are {', '.join(map(str,nums))}. How many rows match WHERE score > {threshold}?"; exp=f"There are {ans} scores greater than {threshold}."
        elif kind==2:
            ans=max(nums); q=f"For scores {', '.join(map(str,nums))}, what does SELECT MAX(score) return?"; exp=f"The highest score is {ans}."
        else:
            ans=len(set(nums)); q=f"How many distinct values are in the score rows {', '.join(map(str,nums))}?"; exp=f"There are {ans} distinct score values."
        return mcq(q,ans,number_choices(ans,rng),exp,rng)
    a=rng.randint(2,99); b=rng.randint(2,19); c=rng.randint(1,10); kind=i%12
    if language=="Python":
        if kind==0: code=f"a={a}; b={b}; print(a // b)"; ans=a//b; expl="Python // returns the floored quotient."
        elif kind==1: code=f"a={a}; b={b}; print(a % b)"; ans=a%b; expl="% returns the remainder after division."
        elif kind==2: code=f"values=[{a}, {b}, {c}]; print(values[1])"; ans=b; expl="List indices start at 0, so index 1 is the second value."
        elif kind==3: code=f"print(sum(range({a%15+1}, {a%15+1+c})))"; ans=sum(range(a%15+1,a%15+1+c)); expl="range stops before its end value; sum the generated integers."
        elif kind==4: code=f"x={a}; print(x > {b} and x % {c} == 0)"; ans=str(a>b and a%c==0); expl="Both comparisons joined by and must be true."
        elif kind==5: code=f"word='career{a}'; print(len(word))"; ans=len(f"career{a}"); expl="len returns the number of characters in the string."
        elif kind==6: code=f"print(max([{a}, {b}, {c}]))"; ans=max(a,b,c); expl="max returns the largest value in the list."
        elif kind==7: code=f"score={a}; print('pass' if score >= {b} else 'retry')"; ans="pass" if a>=b else "retry"; expl="The conditional expression selects the first value when the comparison is true."
        elif kind==8: code=f"record={{'id': {a}, 'score': {b}}}; print(record['score'])"; ans=b; expl="The dictionary key 'score' maps to the stored score value."
        elif kind==9: code=f"items=[{a}, {b}]; items.append({c}); print(len(items))"; ans=3; expl="append adds one item; the list then contains three values."
        elif kind==10: code=f"values=[{a}, {b}, {c}]; print(sum(n % 2 == 0 for n in values))"; ans=sum(v%2==0 for v in [a,b,c]); expl="The expression counts how many values are even."
        else: code=f"print(({a} + {b}) * {c})"; ans=(a+b)*c; expl="Evaluate the parentheses first, then multiply by the final value."
    elif language in ("Java","C","C++","C#","Go","Kotlin","Swift","PHP","JavaScript"):
        if language=="Java": out=f"int a={a}, b={b}; System.out.println(a / b);"
        elif language=="C": out=f"int a={a}, b={b}; printf(\"%d\", a / b);"
        elif language=="C++": out=f"int a={a}, b={b}; cout << a / b;"
        elif language=="C#": out=f"int a={a}, b={b}; Console.WriteLine(a / b);"
        elif language=="Go": out=f"a, b := {a}, {b}; fmt.Println(a / b)"
        elif language=="Kotlin": out=f"val a={a}; val b={b}; println(a / b)"
        elif language=="Swift": out=f"let a={a}; let b={b}; print(a / b)"
        elif language=="PHP": out=f"$a={a}; $b={b}; echo intdiv($a, $b);"
        else: out=f"const a={a}, b={b}; console.log(a / b);"
        if kind==0:
            code=out; ans=(a/b if language=="JavaScript" else a//b); expl=(f"JavaScript number division gives {a}/{b} = {ans:.4g}." if language=="JavaScript" else f"Integer division discards the fractional part: {a} / {b} = {ans}.")
        elif kind==1:
            code=f"{language}: {a} % {b}"; ans=a%b; expl="The remainder operator gives the leftover after division."
        elif kind==2:
            code=f"{language}: values = [{a}, {b}, {c}]; print(values[1])"; ans=b; expl="Index 1 selects the second item in a zero-based array or list."
        elif kind==3:
            code=f"{language}: sum integers from 1 through {c}"; ans=c*(c+1)//2; expl=f"The sum is {c} × ({c}+1) ÷ 2 = {ans}."
        elif kind==4:
            code=f"{language}: ({a} > {b}) && ({a} % {c} == 0)"; ans=str(a>b and a%c==0).lower(); expl="The expression is true only when both conditions are true."
        elif kind==5:
            code=f"{language}: array [{a}, {b}, {c}]; read item at index 1"; ans=b; expl="With zero-based indexing, index 1 refers to the second item."
        elif kind==6:
            code=f"{language}: max of array [{a}, {b}, {c}]"; ans=max(a,b,c); expl="The maximum operation returns the largest array value."
        elif kind==7:
            code=f"{language}: if {a} >= {b} then 'pass' else 'retry'"; ans="pass" if a>=b else "retry"; expl="The condition selects the pass result when the score meets the threshold."
        elif kind==8:
            code=f"{language}: map['score'] where map contains score={b}"; ans=b; expl="The key 'score' retrieves its associated value."
        elif kind==9:
            code=f"{language}: append {c} to array [{a}, {b}], then get length"; ans=3; expl="Appending one item to a two-item array gives a length of three."
        elif kind==10:
            vals=[a,b,c]; code=f"{language}: count even values in [{a}, {b}, {c}]"; ans=sum(v%2==0 for v in vals); expl="Count the values whose remainder after division by 2 is zero."
        else:
            code=f"{language}: ({a} + {b}) * {c}"; ans=(a+b)*c; expl="Evaluate the parenthesized sum before multiplying."
    else:
        if kind==0: code=f"{a} + {b}"; ans=a+b; expl="Add the two operands."
        elif kind==1: code=f"{a} % {b}"; ans=a%b; expl="% gives the remainder."
        elif kind==2: code=f"[{a}, {b}, {c}][1]"; ans=b; expl="Index 1 selects the second item."
        elif kind==3: code=f"sum from 1 through {c}"; ans=c*(c+1)//2; expl="Use n(n+1)/2 to sum the first n integers."
        elif kind==4: code=f"{a} > {b} and {a} divisible by {c}"; ans=str(a>b and a%c==0); expl="Both conditions must be true."
        elif kind==5: code=f"read item at index 1 from [{a}, {b}, {c}]"; ans=b; expl="Index 1 selects the second value in a zero-based sequence."
        elif kind==6: code=f"maximum of [{a}, {b}, {c}]"; ans=max(a,b,c); expl="The maximum is the largest of the three values."
        elif kind==7: code=f"choose 'pass' if {a} >= {b}, otherwise 'retry'"; ans="pass" if a>=b else "retry"; expl="The comparison determines which result is selected."
        elif kind==8: code=f"lookup 'score' in a map where score={b}"; ans=b; expl="A map lookup returns the value associated with its key."
        elif kind==9: code=f"append {c} to [{a}, {b}] and find the length"; ans=3; expl="The resulting sequence has three elements."
        elif kind==10: code=f"count even values in [{a}, {b}, {c}]"; ans=sum(v%2==0 for v in [a,b,c]); expl="Count each value divisible by 2."
        else: code=f"({a} + {b}) * {c}"; ans=(a+b)*c; expl="Evaluate the parenthesized sum, then multiply."
    prompt=f"{language} {level.lower()} practice — evaluate `{code}` and choose its result."
    if isinstance(ans,(int,float)): opts=number_choices(ans,rng,max(1,c))
    elif ans in ("pass","retry"): opts=["pass","retry","hold","error"]
    elif ans in ("true","false","True","False"):
        alternate="false" if ans=="true" else "true" if ans=="false" else "False" if ans=="True" else "True"
        opts=[alternate,"0","1"]
    else: opts=["Other value","No result","None"]
    return mcq(prompt,ans,opts,expl,rng)

def general_knowledge_question(i, rng, prefix=""):
    country,capital,continent=rng.choice(COUNTRY_FACTS)
    if rng.randrange(2)==0:
        wording=rng.choice(["What is the capital city of {country}?","Which city serves as the capital of {country}?","Choose the capital of {country}.","A map labels {country}; which city is its capital?","Select {country}'s national capital."])
        answer=capital; distractors=[c for _,c,_ in COUNTRY_FACTS if c!=capital]
        return mcq(prefix+wording.format(country=country),answer,rng.sample(distractors,3),f"{capital} is the capital of {country}.",rng)
    wording=rng.choice(["On which continent is {country} located?","{country} is part of which continent?","Select the continent where {country} is located.","Which continent should be shown for {country} on a world map?","Choose the correct continent for {country}."])
    continents=["Africa","Asia","Europe","North America","South America","Oceania","Antarctica"]
    return mcq(prefix+wording.format(country=country),continent,[x for x in continents if x!=continent],f"{country} is located in {continent}.",rng)

def company_technical_question(i, company, level, rng):
    cases=[
        ("an API response is slow","Add timing metrics and trace the slow dependency before changing code",["Increase every timeout","Remove validation","Rewrite the service immediately"],"Measure the request path first so the actual bottleneck is known."),
        ("a database has duplicate account rows","Add a uniqueness constraint and handle conflicts in a transaction",["Hide duplicate rows in the UI","Run a cleanup only once","Use a slower page query"],"A database constraint protects the invariant under concurrent requests."),
        ("a release introduces a production regression","Stop further rollout, compare the change and roll back if users are affected",["Delete the monitoring alerts","Wait for more users to report it","Make several untracked edits"],"Contain impact, inspect evidence and restore a known-good version."),
        ("a form accepts user-provided SQL text","Use parameterized queries and validate the expected input",["Join the text into the SQL string","Hide the query in the browser","Encrypt the text and still concatenate it"],"Parameter binding prevents input from changing query structure."),
        ("an access token is accidentally exposed","Revoke and rotate the token, then review access logs",["Rename the token variable","Leave it active until expiry","Put it in a public issue for tracking"],"Treat exposed credentials as compromised and investigate their use."),
        ("a service retries payment requests","Use an idempotency key so retries cannot create duplicate charges",["Remove the transaction ID","Retry forever without limits","Disable all error responses"],"Idempotency makes repeated requests safe to process."),
        ("two threads update the same inventory count","Protect the update with an atomic operation or transaction",["Add a longer sleep","Assume updates never overlap","Cache the old value indefinitely"],"Atomic updates prevent lost writes during concurrent changes."),
        ("a cache returns outdated profile data","Define a clear invalidation or short time-to-live policy",["Cache every response forever","Disable the source database","Ignore the mismatch"],"A cache needs an explicit freshness and invalidation strategy."),
        ("an upload endpoint receives very large files","Enforce a size limit and validate file type on the server",["Trust the filename extension only","Store every file in a public folder","Remove all size checks"],"Server-side limits and content validation reduce upload risk."),
        ("a batch job repeatedly scans a large list for matches","Use a set or indexed lookup for membership checks",["Add another nested scan","Sort the list after every lookup","Convert all values to display strings"],"An indexed or hash-based lookup avoids repeatedly scanning the full list."),
        ("a test fails only when run after other tests","Isolate shared state and control test setup and teardown",["Randomly rerun until it passes","Remove the failing assertion","Depend on test execution order"],"Tests should create and clean up their own state."),
        ("application logs contain personal data","Redact sensitive fields before writing structured logs",["Increase log retention","Copy the logs to a public bucket","Log the full request body"],"Logs should support diagnosis without exposing personal information."),
        ("a client sends the same create request twice","Make the endpoint idempotent or detect the duplicate request",["Create two records by design","Return success without checking state","Disable request identifiers"],"Idempotent handling prevents duplicate side effects."),
        ("a new database query becomes expensive as rows grow","Inspect the query plan and add an appropriate index if justified",["Fetch every column and filter in the browser","Add indexes to every column blindly","Increase the page size"],"Use query plans and workload evidence to select useful indexes."),
        ("a teammate cannot reproduce a reported bug","Record exact steps, input, environment and expected versus actual results",["Guess at the user's intent","Close the issue immediately","Change unrelated code"],"A reproducible report gives the team evidence to diagnose the defect."),
        ("a third-party API is intermittently unavailable","Set bounded retries with backoff and a clear failure path",["Retry in a tight infinite loop","Block every application request forever","Discard the error"],"Bounded exponential backoff reduces load and prevents a retry storm."),
        ("a user can view another user's record by changing an ID","Check authorization on the server for every requested record",["Use an obscure record ID","Hide the ID in the page","Rely only on client-side checks"],"The server must verify that the signed-in user may access the record."),
        ("a deployment needs a risky schema change","Use a backward-compatible migration and deploy in small steps",["Drop the old column before updating the app","Edit production rows manually without a backup","Deploy app and schema changes with no rollback plan"],"Expand-and-contract migrations reduce compatibility and rollback risks."),
        ("a dashboard counter disagrees with the source records","Define the metric and verify its query, filters and time window",["Change the displayed number by hand","Remove the counter","Count records from a different table"],"A metric needs a documented definition and consistent source query."),
        ("a service exposes a secret in its repository","Revoke it, remove it from active history where possible and move it to secret storage",["Rename the file only","Keep using the exposed secret","Put the replacement in the same repository"],"Rotate exposed credentials and store future secrets outside source control."),
    ]
    situation,good,bad,why=cases[i%len(cases)]; endpoint=rng.choice(["/api/profile","/api/search","/api/orders","/api/results","/api/upload","/api/report","/api/accounts","/api/catalog","/api/teams","/api/status"]); ref=rng.randint(1100,98999)
    return mcq(f"{company} {level.lower()} technical interview — incident #{ref} on {endpoint}: {situation}. What is the best engineering response?",good,bad,why,rng)

def company_gk_question(i, company, rng):
    facts=[
        ("HTTP 404","The requested resource was not found",["The request succeeded","The server is unavailable","The client must authenticate"],"HTTP 404 means the requested resource could not be found."),
        ("DNS","It translates domain names into network addresses",["It encrypts database rows","It compiles source code","It stores browser cookies"],"DNS resolves host names to IP addresses."),
        ("RAM","It is volatile working memory",["It is permanent optical storage","It is a network protocol","It is a CPU instruction"],"RAM normally loses its contents when power is removed."),
        ("HTTPS","It protects HTTP traffic using TLS",["It replaces DNS","It compresses all files","It is a database query language"],"HTTPS uses TLS to protect data in transit."),
        ("Git commit","It records a snapshot in repository history",["It deletes the repository","It installs a compiler","It opens a network port"],"A commit stores a versioned change in Git history."),
        ("CPU","It executes program instructions",["It stores long-term files","It resolves domain names","It renders only CSS"],"The processor executes instructions for running programs."),
        ("JSON","It is a text format for structured data exchange",["It is a transport cable","It is a CPU architecture","It is a file compression algorithm"],"JSON represents structured data using objects, arrays and values."),
        ("an HTTP 500 response","The server encountered an unexpected error",["The resource was not found","The request was redirected","The client is unauthenticated"],"HTTP 500 indicates an internal server error."),
        ("two-factor authentication","It requires a second proof in addition to a password",["It stores two copies of every file","It doubles network speed","It removes account authorization"],"A second factor adds another independent proof of identity."),
        ("a primary key","It uniquely identifies a row in a table",["It sorts every table automatically","It stores only images","It allows duplicate identifiers"],"A primary key provides a unique row identifier."),
        ("an API","It defines a way for software components to communicate",["It is a graphics card","It is a password format","It is a spreadsheet formula"],"An API defines an interface for software interaction."),
        ("a software license","It describes the permissions and conditions for using software",["It guarantees zero defects","It encrypts every source file","It is a server address"],"A license sets terms for use, modification and distribution."),
        ("a phishing message","It attempts to trick someone into revealing data or taking an unsafe action",["It is a routine backup","It is a network speed test","It is a database index"],"Phishing uses deceptive messages to steal information or prompt unsafe actions."),
        ("a foreign key","It links a row to a key in another table",["It encrypts the table","It removes every duplicate automatically","It formats a date"],"A foreign key expresses a relationship between tables."),
        ("a software test","It checks whether behavior matches an expected result",["It guarantees the program has no bugs","It replaces source control","It is a user password"],"Tests check specified behavior but cannot prove the absence of every defect."),
        ("a cloud region","It is a geographic area containing cloud infrastructure",["It is a programming language","It is a file extension","It is a login credential"],"Cloud regions group infrastructure in a geographic area."),
        ("open-source software","Its source is available under a license that grants specified freedoms",["It has no license","It is always free of cost and restrictions","It cannot be modified"],"Open-source status depends on license-granted rights, not simply price."),
        ("a firewall","It filters network traffic according to security rules",["It formats source code","It increases monitor brightness","It creates a database backup"],"A firewall controls allowed and blocked network traffic."),
        ("a database index","It can speed up selected lookups at a storage and write cost",["It encrypts the network","It stores source code comments","It guarantees every query is instant"],"Indexes help specific lookups but use space and can add write overhead."),
        ("a password hash","It stores a one-way transformed password verifier",["It stores the password in plain text","It is a recovery email","It is a public username"],"A salted password hash can be checked without storing the original password."),
    ]
    concept,answer,distractors,explanation=facts[i%len(facts)]; wording=rng.choice(["Which statement best describes {concept}?","In a software team, what is the purpose of {concept}?","Choose the accurate explanation of {concept}."]); ref=rng.randint(100,9999)
    return mcq(f"{company} general knowledge #{ref}: {wording.format(concept=concept)}",answer,distractors,explanation,rng)

def company_question(i, company, round_name, level, rng):
    if round_name=="Technical Round":
        return company_technical_question(i,company,level,rng)
    if round_name=="Aptitude & Logical Reasoning":
        q=(logical_question(i,level,rng) if i%2 else aptitude_question(i,level,rng))
        q["question"]=f"{company} aptitude round: {q['question']}"
        return q
    if round_name=="General Knowledge":
        return company_gk_question(i,company,rng)
    if round_name=="Group Discussion":
        topics=["hybrid work", "campus sustainability", "responsible AI", "digital privacy", "public transport", "online learning", "team deadlines", "accessible design", "cyber safety", "renewable energy", "internship access", "local entrepreneurship"]
        topic=topics[i%len(topics)]; scenario=rng.choice(["the team has two different proposals", "one member has not had a chance to speak", "the discussion is moving away from the topic", "the group has limited time to decide", "a new fact changes the initial assumptions"]); minutes=rng.randint(2,18)
        return mcq(f"{company} group discussion: With {minutes} minutes left while discussing {topic}, {scenario}. What is the most constructive next step?","Acknowledge the views, invite evidence and help the group agree on a clear next step",["Interrupt and insist on your first idea","Dismiss the concern and change the subject","Stay silent and let the discussion end"],"Good group discussion combines active listening, evidence and a shared next step.",rng)
    scenarios=[("a deadline may be missed", "Tell the manager early, explain the impact and propose a recovery plan",["Hide the delay until the deadline","Blame another team","Submit incomplete work without context"],"Clear early communication and a recovery plan show ownership."),("you receive a difficult piece of feedback","Ask for an example, clarify expectations and make an improvement plan",["Argue before hearing the details","Ignore the feedback","Blame the reviewer"],"Specific examples and an action plan turn feedback into improvement."),("you do not know an answer in an interview","Be honest, explain how you would find the answer and reason through what you know",["Invent a confident answer","Change the topic","Stop responding"],"Honest reasoning is more useful than guessing."),("two urgent tasks compete for your time","Confirm deadlines and impact, then agree priorities with the stakeholders",["Choose randomly","Do the easiest task only","Ignore one task"],"Prioritize by impact and deadline, then communicate."),("a teammate asks for help while you have your own deadline","Clarify the urgency, offer a bounded time or connect them to the right resource",["Promise unlimited help","Refuse without discussion","Leave your task without telling anyone"],"Set clear expectations while being supportive."),("you notice a possible privacy issue in a project","Pause the risky action, protect the data and report it through the right channel",["Share the data to get quick help","Ignore the concern","Delete evidence without telling anyone"],"Protecting data and reporting through the proper channel reduces harm."),("a project you owned did not meet its goal","Explain the outcome, your part in it and what you would change next time",["Claim it was entirely someone else's fault","Hide the result","Describe only the successful parts"],"Accountability and learning show professional maturity."),("the project requirements change close to delivery","Confirm the new priority and impact, then agree on a realistic updated plan",["Continue with the old plan without discussion","Promise everything immediately","Reject the change without understanding it"],"Clarify scope, impact and expectations before committing."),("a stakeholder gives unclear instructions","Ask focused questions and summarize the expected outcome before starting",["Guess and begin","Wait silently until the deadline","Ask several people to interpret it differently"],"Confirming expectations prevents avoidable rework."),("you disagree with a teammate's technical decision","Discuss evidence and trade-offs respectfully, then support the agreed team decision",["Make the change secretly","Turn it into a personal argument","Stop sharing information"],"Evidence-based discussion keeps the focus on the work.")]
    situation,good,bad,why=scenarios[i%len(scenarios)]; role=rng.choice(["graduate trainee","software developer","data analyst","QA engineer","business analyst","cloud associate","product designer","support engineer","project coordinator","security analyst"]); stage=rng.choice(["during onboarding","in your first month","while working with a client team","during a release week","as part of a cross-functional project","during an incident review","while ramping up on a new system","before a customer demo","after a sprint retrospective","while reviewing a teammate's work"])
    return mcq(f"{company} HR round for a {role}: How would you handle {situation} {stage}?",good,bad,why,rng)

def generate_question(category, label, round_name, level, i, rng):
    if category=="aptitude":
        if label.lower().startswith("logical"): return logical_question(i,level,rng)
        if label.lower().startswith("general knowledge"): return general_knowledge_question(i,rng)
        return logical_question(i//2,level,rng) if i%4==3 else aptitude_question(i,level,rng,label)
    if category=="technical": return technical_question(i,label,level,rng)
    return company_question(i,label,round_name,level,rng)

def question_set(category, label, round_name, level, count, seed, previously_used):
    rng=random.Random(seed); out=[]; used=set(previously_used); attempts=0
    while len(out)<count and attempts<count*30:
        q=generate_question(category,label,round_name,level,attempts,rng); attempts+=1
        if q["question"] in used: continue
        used.add(q["question"]); out.append(q)
    if len(out)<count: raise ValueError(f"Only {len(out)} unused unique questions are available for this set.")
    rng.shuffle(out)
    for i,q in enumerate(out,1): q["id"]=i
    return out

@app.get("/api/questions")
@logged_in
def questions():
    category=request.args.get("category","aptitude").lower(); label=request.args.get("label","Aptitude"); round_name=request.args.get("round",""); level=request.args.get("level","Easy"); count=min(100,max(1,int(request.args.get("count",50)))); seed=f"{session['user_id']}-{category}-{label}-{round_name}-{level}"
    if category not in ("aptitude","technical","company"): return jsonify(error="Unknown test category."),400
    db=connect_db(); uid=session["user_id"]
    used=[r["question"] for r in db.execute("SELECT question FROM used_questions WHERE user_id=?",(uid,))]
    try: result=question_set(category,label,round_name,level,count,secrets.token_hex(12),used)
    except ValueError as e: return jsonify(error=str(e)),409
    db.executemany("INSERT OR IGNORE INTO used_questions(user_id,question,created) VALUES(?,?,?)",[(uid,q["question"],now()) for q in result]); db.commit()
    return jsonify(category=category,label=label,round=round_name,level=level,questions=result)

@app.post("/api/submit")
@logged_in
def submit():
    d=request.get_json() or {}; qs=d.get("questions",[]); answers=d.get("answers",[])
    if not qs: return jsonify(error="No questions to submit."),400
    review=[]; correct=0
    for i,q in enumerate(qs):
        selected=answers[i] if i<len(answers) else None; ok=selected==q.get("answer"); correct+=int(ok)
        review.append({"question":q.get("question"),"selected":selected,"answer":q.get("answer"),"correct":ok,"explanation":q.get("explanation")})
    score=round(correct*100/len(qs)); category=d.get("category","aptitude"); label=d.get("label",category.title()); db=connect_db(); uid=session["user_id"]
    db.execute("INSERT INTO results(user_id,category,label,score,total,created) VALUES(?,?,?,?,?,?)",(uid,category,label,score,len(qs),now())); db.commit()
    activity(db,uid,f"Completed {label} practice · {correct}/{len(qs)} correct ({score}%).","practice")
    print(f"[CareerBrigade] Process complete: {label} | Score {score}% | {correct}/{len(qs)} correct", flush=True)
    return jsonify(score=score,correct=correct,total=len(qs),review=review)

@app.get("/api/meta")
def meta(): return jsonify(companies=COMPANIES,languages=LANGUAGES)

@app.errorhandler(413)
def too_large(_): return jsonify(error="File is larger than 8 MB."),413

init_db()
if __name__=="__main__":
    from werkzeug.serving import make_server
    port=int(os.environ.get("PORT",5000))
    server=make_server("127.0.0.1",port,app,threaded=True)
    app.config["server_instance"]=server
    print(f"CareerBrigade is running at http://127.0.0.1:{port}",flush=True)
    try: server.serve_forever()
    finally: print("[CareerBrigade] Process complete. Project server is fully closed.",flush=True)
