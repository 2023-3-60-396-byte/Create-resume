import sqlite3, os
from werkzeug.security import generate_password_hash
from datetime import datetime
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "resume.db")
CATS = ["technical", "soft", "language", "certification", "other"]

def fmt_period(start, end):
    f = lambda m: datetime.strptime(m, "%Y-%m").strftime("%b %Y")
    return f"{f(start)} - {f(end) if end else 'Present'}"

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON"); return c

def init_db(seed=True):
    c = conn(); c.executescript(open(os.path.join(BASE, "schema.sql")).read())
    if seed and c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        for n, e, p in (("Rahim Uddin", "rahim@example.com", "+8801712345678"), ("Nusrat Jahan", "nusrat@example.com", "+8801812345678")):
            c.execute("INSERT INTO users(name,email,phone_number,password_hash) VALUES(?,?,?,?)", (n, e, p, generate_password_hash("password123")))
        c.executescript(open(os.path.join(BASE, "seed.sql")).read())
    c.commit(); c.close()

def get_user(uid):
    with conn() as c:
        return c.execute("SELECT user_id, name, email, phone_number AS phone FROM users WHERE user_id=?", (uid,)).fetchone()

def get_user_auth(email):
    with conn() as c:
        return c.execute("SELECT user_id, name, email, phone_number AS phone, password_hash FROM users WHERE email=?", (email.lower(),)).fetchone()

def create_user(name, email, phone, password):
    with conn() as c:
        return c.execute("INSERT INTO users(name,email,phone_number,password_hash) VALUES(?,?,?,?)",
                         (name, email.lower(), phone, generate_password_hash(password))).lastrowid

def list_resumes(uid):
    """Only the logged-in user's resumes."""
    with conn() as c:
        return c.execute("""SELECT r.resume_id, r.title, r.last_modified, u.name, u.email
            FROM resumes r JOIN users u USING(user_id) WHERE r.user_id=? ORDER BY r.last_modified DESC""", (uid,)).fetchall()

def get_resume(rid):
    """RETRIEVE: returns the whole resume as one dict (or None)."""
    with conn() as c:
        r = c.execute("""SELECT r.*, u.name, u.email, u.phone_number AS phone FROM resumes r
            JOIN users u USING(user_id) WHERE resume_id=?""", (rid,)).fetchone()
        if not r: return None
        d = dict(r); d["objective"] = d.pop("career_objective") or ""
        d["education"] = [dict(x, year=str(x["graduation_year"])) for x in
            c.execute("SELECT * FROM education WHERE resume_id=? ORDER BY graduation_year DESC", (rid,))]
        d["experience"] = [dict(x, duration=fmt_period(x["start_date"], x["end_date"])) for x in
            c.execute("SELECT * FROM experience WHERE resume_id=? ORDER BY start_date DESC", (rid,))]
        d["skills"] = {k: [] for k in CATS}
        for s in c.execute("SELECT * FROM skills WHERE resume_id=? ORDER BY skill_id", (rid,)):
            d["skills"][s["category"]].append(s["skill_name"])
        return d

def _children(c, rid, d):
    for r in d["education"]:
        c.execute("INSERT INTO education(resume_id,institution,degree,graduation_year,result) VALUES(?,?,?,?,?)",
                  (rid, r["institution"], r["degree"], int(r["year"]), r["result"]))
    for r in d["experience"]:
        c.execute("INSERT INTO experience(resume_id,company,job_title,start_date,end_date,responsibilities) VALUES(?,?,?,?,?,?)",
                  (rid, r["company"], r["job_title"], r["start_date"], r["end_date"] or None, r["responsibilities"]))
    for cat, items in d["skills"].items():
        for s in items:
            c.execute("INSERT INTO skills(resume_id,skill_name,category) VALUES(?,?,?)", (rid, s, cat))

def _profile(c, uid, d):   # name/phone belong to the account; the email can never be changed here
    c.execute("UPDATE users SET name=?, phone_number=? WHERE user_id=?", (d["name"], d["phone"], uid))

def create_resume(uid, d):
    with conn() as c:
        _profile(c, uid, d)
        rid = c.execute("INSERT INTO resumes(user_id,title,address,linkedin,career_objective) VALUES(?,?,?,?,?)",
                        (uid, d["title"], d["address"], d["linkedin"], d["objective"])).lastrowid
        _children(c, rid, d); return rid

def update_resume(rid, uid, d):
    """UPDATE: only succeeds if the resume belongs to uid. Returns False otherwise."""
    with conn() as c:
        cur = c.execute("""UPDATE resumes SET title=?, address=?, linkedin=?, career_objective=?,
                     last_modified=? WHERE resume_id=? AND user_id=?""",
                  (d["title"], d["address"], d["linkedin"], d["objective"],
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rid, uid))
        if cur.rowcount == 0: return False
        _profile(c, uid, d)
        for t in ("education", "experience", "skills"):
            c.execute(f"DELETE FROM {t} WHERE resume_id=?", (rid,))
        _children(c, rid, d); return True

def delete_resume(rid, uid):
    with conn() as c: return c.execute("DELETE FROM resumes WHERE resume_id=? AND user_id=?", (rid, uid)).rowcount > 0
