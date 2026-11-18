import io, re
from itertools import zip_longest
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
import database as db
from validators import validate, validate_register
from pdf_generator import build_pdf

app = Flask(__name__)
app.secret_key = "change-me-in-production"
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024   # reject request bodies over 1 MB
db.init_db()

# ---------- authentication (Flask-Login) ----------
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "err"

class User(UserMixin):
    def __init__(self, row):
        self.id, self.name, self.email, self.phone = row["user_id"], row["name"], row["email"], row["phone"]

@login_manager.user_loader
def load_user(uid):
    row = db.get_user(int(uid)); return User(row) if row else None

def safe_next(url):   # only allow same-site relative redirects
    return url if url and url.startswith("/") and not url.startswith("//") else url_for("index")

@app.route("/register", methods=["GET", "POST"])
def register():
    f = {k: clean(request.form.get(k, "")) if k != "password" and k != "confirm" else request.form.get(k, "") for k in ("name", "email", "phone", "password", "confirm")}
    if request.method == "POST":
        errors = validate_register(f)
        if not errors and db.get_user_auth(f["email"]): errors["email"] = "An account with this email already exists."
        if not errors:
            uid = db.create_user(f["name"].strip(), f["email"].strip(), f["phone"].strip(), f["password"])
            login_user(User(db.get_user(uid))); flash("Account created. Welcome!", "ok")
            return redirect(url_for("index"))
        return render_template("register.html", f=f, errors=errors)
    return render_template("register.html", f=f, errors={})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        row = db.get_user_auth(request.form.get("email", "").strip())
        if row and check_password_hash(row["password_hash"], request.form.get("password", "")):
            login_user(User(row)); return redirect(safe_next(request.form.get("next")))
        return render_template("login.html", error="Invalid email or password.", email=request.form.get("email"), next=request.form.get("next"))
    return render_template("login.html", next=request.args.get("next"))

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user(); flash("Logged out.", "ok"); return redirect(url_for("login"))

# ---------- authorization ----------
def owned(rid):
    """Return the resume only if it belongs to the logged-in user; otherwise 404 (does not reveal that it exists)."""
    d = db.get_resume(rid)
    if not d or d["user_id"] != current_user.id: abort(404)
    return d

CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")   # control chars (keeps \n and \t)
clean = lambda v: CTRL.sub("", v).strip()

def uniq(items):   # case-insensitive de-duplication, keeps order
    seen = set(); return [s for s in items if not (s.lower() in seen or seen.add(s.lower()))]

def read_form(f):
    g = lambda k: clean(f.get(k, ""))
    # zip_longest: a tampered POST with missing columns can no longer silently drop rows
    rows = lambda *keys: [dict(zip(keys, r)) for r in zip_longest(*[[clean(v) for v in f.getlist(k)] for k in keys], fillvalue="")]
    edu = [{"institution": r["edu_institution"], "degree": r["edu_degree"], "year": r["edu_year"], "result": r["edu_result"]}
           for r in rows("edu_institution", "edu_degree", "edu_year", "edu_result") if any(r.values())]
    exp = [{"company": r["exp_company"], "job_title": r["exp_title"], "start_date": r["exp_start"], "end_date": r["exp_end"], "responsibilities": r["exp_resp"]}
           for r in rows("exp_company", "exp_title", "exp_start", "exp_end", "exp_resp") if any(r.values())]
    skills = {c: uniq([clean(s) for s in g("skills_" + c).splitlines() if clean(s)]) for c in db.CATS}
    return {"title": g("title"), "name": g("name"), "email": current_user.email, "phone": g("phone"), "address": g("address"),
            "linkedin": g("linkedin"), "objective": g("objective"), "education": edu, "experience": exp, "skills": skills}

def blank():
    return {"title": "", "name": current_user.name, "email": current_user.email, "phone": current_user.phone, "address": "", "linkedin": "",
            "objective": "", "education": [], "experience": [], "skills": {c: [] for c in db.CATS}}

@app.route("/")
@login_required
def index():
    return render_template("index.html", resumes=db.list_resumes(current_user.id))

@app.route("/resume/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        d = read_form(request.form); errors = validate(d)
        if not errors:
            rid = db.create_resume(current_user.id, d); flash("Resume saved successfully.", "ok")
            return redirect(url_for("preview", rid=rid))
        return render_template("form.html", d=d, errors=errors, mode="new")
    return render_template("form.html", d=blank(), errors={}, mode="new")

@app.route("/resume/<int:rid>/edit", methods=["GET", "POST"])
@login_required
def edit(rid):
    cur = owned(rid)
    if request.method == "POST":
        d = read_form(request.form); errors = validate(d)
        if not errors:
            if not db.update_resume(rid, current_user.id, d): abort(404)
            flash("Resume updated.", "ok"); return redirect(url_for("preview", rid=rid))
        return render_template("form.html", d=d, errors=errors, mode="edit", rid=rid)
    return render_template("form.html", d=cur, errors={}, mode="edit", rid=rid)

@app.route("/resume/<int:rid>")
@login_required
def preview(rid):
    return render_template("preview.html", d=owned(rid), rid=rid)

@app.route("/resume/<int:rid>/pdf")
@login_required
def pdf(rid):
    d = owned(rid)
    try: data = build_pdf(d)
    except Exception:
        flash("Could not generate the PDF. Please try again.", "err"); return redirect(url_for("preview", rid=rid))
    return send_file(io.BytesIO(data), mimetype="application/pdf", as_attachment=True,
                     download_name=f"{d['name'].replace(' ', '_')}_Resume.pdf")

@app.route("/resume/<int:rid>/delete", methods=["POST"])
@login_required
def delete(rid):
    owned(rid); db.delete_resume(rid, current_user.id); flash("Resume deleted.", "ok"); return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
