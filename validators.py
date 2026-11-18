"""Server-side validation: the single source of truth. static/js/form.js mirrors these rules for instant feedback."""
import re
from datetime import date

EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
PHONE_CHARS = re.compile(r"^\+?[0-9\s\-()]+$")
MONTH = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")
YEAR = re.compile(r"^[0-9]{4}$")                       # ASCII digits only (str.isdigit() accepts '²' and then int() crashes)
LINKEDIN = re.compile(r"^(https?://)?([a-z]{2,3}\.)?linkedin\.com/(in|company)/[\w\-%.]+/?$", re.I)
BAD_NAME = re.compile(r"[0-9<>@#$%^&*()=+\[\]{}|\\/;:\"~`?!_]")   # unicode-safe: blocks digits/symbols, allows Bangla etc.

LIMITS = dict(title=100, name=100, email=254, phone=20, address=200, linkedin=200, objective=1000,
              institution=150, degree=150, result=50, company=150, job_title=100, responsibilities=1000, skill=60)
MAX_EDU = MAX_EXP = 10
MAX_SKILLS = 30   # per category

def too_long(v, key): return f"Maximum {LIMITS[key]} characters." if len(v) > LIMITS[key] else ""

def check_name(v):
    v = v.strip()
    if not v: return "Full name is required."
    if len(v) < 2: return "Name must be at least 2 characters."
    if BAD_NAME.search(v): return "Name cannot contain digits or symbols."
    return too_long(v, "name")

def check_email(v):
    v = v.strip()
    if not EMAIL.match(v): return "Enter a valid email address."
    return too_long(v, "email")

def check_phone(v):
    v = v.strip(); n = len(re.sub(r"\D", "", v))
    if not PHONE_CHARS.match(v) or not 7 <= n <= 15: return "Enter a valid phone number (7-15 digits, e.g. +8801712345678)."
    return too_long(v, "phone")

def validate_register(f):
    e = {}
    if m := check_name(f["name"]): e["name"] = m
    if m := check_email(f["email"]): e["email"] = m
    if m := check_phone(f["phone"]): e["phone"] = m
    p = f["password"]
    if not 8 <= len(p) <= 128: e["password"] = "Password must be 8-128 characters."
    elif not (re.search(r"[A-Za-z]", p) and re.search(r"[0-9]", p)): e["password"] = "Password must contain at least one letter and one number."
    elif p != f["confirm"]: e["confirm"] = "Passwords do not match."
    return e

def validate(d):
    e = {}
    now_m, now_y = date.today().strftime("%Y-%m"), date.today().year
    if not d["title"].strip(): e["title"] = "Resume title is required."
    elif m := too_long(d["title"], "title"): e["title"] = m
    if m := check_name(d["name"]): e["name"] = m
    if m := check_email(d["email"]): e["email"] = m
    if m := check_phone(d["phone"]): e["phone"] = m
    if m := too_long(d["address"], "address"): e["address"] = m
    if d["linkedin"] and not LINKEDIN.match(d["linkedin"]): e["linkedin"] = "Enter a valid LinkedIn URL (e.g. linkedin.com/in/yourname)."
    elif m := too_long(d["linkedin"], "linkedin"): e["linkedin"] = m
    if not d["objective"].strip(): e["objective"] = "Career objective is required."
    elif m := too_long(d["objective"], "objective"): e["objective"] = m

    if not d["education"]: e["education"] = "Add at least one education entry."
    elif len(d["education"]) > MAX_EDU: e["education"] = f"Maximum {MAX_EDU} education entries."
    for i, r in enumerate(d["education"]):
        if not (r["institution"] and r["degree"]): e[f"edu{i}"] = "Institution and degree are required."
        elif not YEAR.match(r["year"]) or not 1950 <= int(r["year"]) <= now_y + 6: e[f"edu{i}"] = f"Enter a valid passing year (1950-{now_y + 6})."
        else:
            e_ = too_long(r["institution"], "institution") or too_long(r["degree"], "degree") or too_long(r["result"], "result")
            if e_: e[f"edu{i}"] = e_

    if len(d["experience"]) > MAX_EXP: e["experience"] = f"Maximum {MAX_EXP} experience entries."
    for i, r in enumerate(d["experience"]):
        s, en = r["start_date"], r["end_date"]
        if not (r["company"] and r["job_title"]): e[f"exp{i}"] = "Company and position are required."
        elif not MONTH.match(s): e[f"exp{i}"] = "Enter a valid start date."
        elif s > now_m: e[f"exp{i}"] = "Start date cannot be in the future."
        elif en and not MONTH.match(en): e[f"exp{i}"] = "Enter a valid end date."
        elif en and en > now_m: e[f"exp{i}"] = "End date cannot be in the future (leave empty if currently working)."
        elif en and en < s: e[f"exp{i}"] = "End date cannot be before the start date."
        else:
            e_ = too_long(r["company"], "company") or too_long(r["job_title"], "job_title") or too_long(r["responsibilities"], "responsibilities")
            if e_: e[f"exp{i}"] = e_

    if not any(d["skills"].values()): e["skills"] = "Add at least one skill."
    for cat, items in d["skills"].items():
        if len(items) > MAX_SKILLS: e["skills"] = f"Maximum {MAX_SKILLS} items per skill category."
        elif any(len(s) > LIMITS["skill"] for s in items): e["skills"] = f"Each skill can be at most {LIMITS['skill']} characters."
    return e
