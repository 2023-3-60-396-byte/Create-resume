const form = document.getElementById("rf"), pv = document.getElementById("pv");
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/, PHONE = /^\+?[0-9\s\-]{7,16}$/;
const CATS = ["technical","soft","language","certification","other"];
const esc = s => s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const val = n => (form.elements[n]?.value || "").trim();
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const fm = m => m ? MON[+m.slice(5) - 1] + " " + m.slice(0, 4) : "";
const lines = n => val(n).split("\n").map(s => s.trim()).filter(Boolean);
const all = n => [...form.querySelectorAll(`[name="${n}"]`)].map(e => e.value.trim());

function render() {   // dynamic live resume preview
  const edu = all("edu_institution").map((_, i) => `<p><b>${esc(all("edu_degree")[i])}</b> — ${esc(all("edu_institution")[i])} (${esc(all("edu_year")[i])})<br><span class="muted">${esc(all("edu_result")[i])}</span></p>`).join("");
  const exp = all("exp_company").map((_, i) => `<p><b>${esc(all("exp_title")[i])}</b>, ${esc(all("exp_company")[i])} <span class="muted">(${fm(all("exp_start")[i])} - ${fm(all("exp_end")[i]) || "Present"})</span><br>${esc(all("exp_resp")[i])}</p>`).join("");
  const sk = CATS.filter(c => lines("skills_"+c).length).map(c => `<p><b>${c[0].toUpperCase()+c.slice(1)}:</b> ${lines("skills_"+c).map(esc).join(", ")}</p>`).join("");
  pv.innerHTML = `<h2>${esc(val("name")) || "Your Name"}</h2><p class="muted">${[val("email"),val("phone"),val("address"),val("linkedin")].filter(Boolean).map(esc).join(" | ")}</p>
  <h4>Career Objective</h4><p>${esc(val("objective"))}</p><h4>Education</h4>${edu}${exp ? "<h4>Experience</h4>"+exp : ""}<h4>Skills</h4>${sk}`;
}
function addRow(t) { document.getElementById(t).appendChild(document.getElementById("t-"+t).content.cloneNode(true)); render(); }
document.querySelectorAll("[data-add]").forEach(b => b.onclick = () => addRow(b.dataset.add));
form.addEventListener("click", e => { if (e.target.classList.contains("rm")) { e.target.closest(".item").remove(); render(); } });
form.addEventListener("input", render);
if (!document.querySelector("#edu .item")) addRow("edu");

function setErr(el, msg) {   // "Show inline errors" (activity diagram)
  el.classList.toggle("bad", !!msg);
  const old = el.nextElementSibling; if (old && old.classList.contains("js")) old.remove();
  if (msg) { const s = document.createElement("small"); s.className = "err js"; s.textContent = msg; el.after(s); }
  return !msg;
}
// ---- rules mirrored from validators.py ----
const BAD_NAME = /[0-9<>@#$%^&*()=+\[\]{}|\\\/;:"~`?!_]/, LI = /^(https?:\/\/)?([a-z]{2,3}\.)?linkedin\.com\/(in|company)\/[\w\-%.]+\/?$/i;
const digits = s => s.replace(/\D/g, "").length, max = (v, n) => v.length > n ? `Maximum ${n} characters.` : "";
const NOW_Y = new Date().getFullYear(), NOW_M = new Date().toISOString().slice(0, 7);
document.querySelectorAll('input[type="month"]').forEach(i => i.max = NOW_M);
document.addEventListener("click", e => { if (e.target.dataset.add === "exp") document.querySelectorAll('#exp input[type="month"]').forEach(i => i.max = NOW_M); });

form.addEventListener("submit", e => {
  let ok = true; const set = (el, m) => { ok = setErr(el, m) && ok; };
  const F = n => form.elements[n];
  set(F("title"), !val("title") ? "Resume title is required." : max(val("title"), 100));
  const nm = val("name"); set(F("name"), !nm ? "Full name is required." : nm.length < 2 ? "Name must be at least 2 characters." : BAD_NAME.test(nm) ? "Name cannot contain digits or symbols." : max(nm, 100));
  set(F("email"), EMAIL.test(val("email")) ? "" : "Enter a valid email address.");
  const ph = val("phone"); set(F("phone"), /^\+?[0-9\s\-()]+$/.test(ph) && digits(ph) >= 7 && digits(ph) <= 15 ? max(ph, 20) : "Enter a valid phone number (7-15 digits, e.g. +8801712345678).");
  set(F("address"), max(val("address"), 200));
  set(F("linkedin"), val("linkedin") && !LI.test(val("linkedin")) ? "Enter a valid LinkedIn URL (e.g. linkedin.com/in/yourname)." : max(val("linkedin"), 200));
  set(F("objective"), !val("objective") ? "Career objective is required." : max(val("objective"), 1000));

  const rowsOf = (sel) => [...form.querySelectorAll(sel + " .item")].filter(it => [...it.querySelectorAll("input,textarea")].some(x => x.value.trim()));
  const edu = rowsOf("#edu");
  if (!edu.length) set(form.querySelector('#edu input[name="edu_institution"]'), "Add at least one education entry.");
  if (edu.length > 10) set(edu[10].querySelector("input"), "Maximum 10 education entries.");
  edu.forEach(it => {
    const [i, d, y, r] = it.querySelectorAll("input"), yr = +y.value;
    set(i, !i.value.trim() ? "Institution is required." : max(i.value.trim(), 150));
    set(d, !d.value.trim() ? "Degree is required." : max(d.value.trim(), 150));
    set(y, /^[0-9]{4}$/.test(y.value.trim()) && yr >= 1950 && yr <= NOW_Y + 6 ? "" : `Enter a valid passing year (1950-${NOW_Y + 6}).`);
    set(r, max(r.value.trim(), 50));
  });
  const exp = rowsOf("#exp");
  if (exp.length > 10) set(exp[10].querySelector("input"), "Maximum 10 experience entries.");
  exp.forEach(it => {
    const [c, t, s, en] = it.querySelectorAll("input"), resp = it.querySelector("textarea");
    set(c, !c.value.trim() ? "Company is required." : max(c.value.trim(), 150));
    set(t, !t.value.trim() ? "Position is required." : max(t.value.trim(), 100));
    set(s, !s.value ? "Enter a start date." : s.value > NOW_M ? "Start date cannot be in the future." : "");
    set(en, en.value && en.value > NOW_M ? "End date cannot be in the future (leave empty if currently working)." : en.value && s.value && en.value < s.value ? "End date cannot be before the start date." : "");
    set(resp, max(resp.value.trim(), 1000));
  });
  CATS.forEach((c, idx) => {
    const L = lines("skills_" + c), el = F("skills_" + c);
    set(el, L.length > 30 ? "Maximum 30 items per skill category." : L.some(s => s.length > 60) ? "Each skill can be at most 60 characters." :
        idx === 0 && !CATS.some(k => lines("skills_" + k).length) ? "Add at least one skill." : "");
  });
  if (!ok) { e.preventDefault(); form.querySelector(".bad")?.scrollIntoView({behavior: "smooth", block: "center"}); }
});
render();
