const form = document.getElementById("reportForm");
const $ = id => document.getElementById(id);
const field = name => form.elements[name];
const LAST_KEY = "wellness:lastContext";
const MAX_PHOTO = 2 * 1024 * 1024;
let options = null;
let photoFile = null;

function defaultYear() {
  const now = new Date();
  const y = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1; // Indian year starts in April
  return `${y}-${String((y + 1) % 100).padStart(2, "0")}`;
}

function loadLast() {
  try { return JSON.parse(localStorage.getItem(LAST_KEY)) || {}; } catch { return {}; }
}
function saveLast(s) {
  try {
    localStorage.setItem(LAST_KEY, JSON.stringify({
      school_name: s.school_name, class_name: s.class_name, academic_year: s.academic_year,
    }));
  } catch { /* storage unavailable: fine */ }
}

function showError(msg, retryId) {
  const box = $("formError");
  box.textContent = msg;
  if (retryId) {
    const actions = document.createElement("div");
    actions.className = "alert-actions";
    actions.innerHTML = `<button type="button" class="btn primary small" id="retryBtn">Try the AI step again</button>
      <a class="btn secondary small" href="/">Go to all reports</a>`;
    box.appendChild(actions);
    $("retryBtn").onclick = () => runGenerate(retryId);
  }
  box.hidden = false;
  box.scrollIntoView({ behavior: "smooth", block: "center" });
}
function clearError() { $("formError").hidden = true; $("formError").textContent = ""; }

function setProgress(text) {
  $("progress").hidden = !text;
  $("progressText").textContent = text || "";
}

// ---------- Build the form from the server's option lists ----------
function renderTraits() {
  $("traits").innerHTML = options.nature_traits.map(t =>
    `<label class="chip"><input type="checkbox" name="trait" value="${esc(t)}"><span>${esc(t)}</span></label>`
  ).join("");
  $("traits").addEventListener("change", updateTraitCount);
}

function updateTraitCount() {
  const boxes = [...form.querySelectorAll("input[name=trait]")];
  const n = boxes.filter(b => b.checked).length;
  boxes.forEach(b => { b.disabled = !b.checked && n >= 8; });
  const c = $("traitCount");
  c.textContent = n >= 8 ? `${n} selected (maximum reached)` : `${n} selected`;
  c.classList.toggle("bad", false);
}

function renderRatings() {
  $("ratings").innerHTML = options.wellness_categories.map(c => `
    <div class="rating" data-key="${c.key}">
      <span class="rating-label" id="lbl_${c.key}">${esc(c.label)}</span>
      <fieldset class="stars" aria-labelledby="lbl_${c.key}">
        ${[1, 2, 3, 4, 5].map(n => `
          <label class="star"><input type="radio" name="r_${c.key}" value="${n}">
            <span aria-hidden="true">★</span><span class="sr">${n} out of 5</span></label>`).join("")}
      </fieldset>
      <span class="rating-value">–</span>
    </div>`).join("");

  $("ratings").querySelectorAll(".rating").forEach(row => {
    const stars = [...row.querySelectorAll(".star")];
    const paint = v => stars.forEach((s, i) => s.classList.toggle("on", i < v));
    const checked = () => Number((row.querySelector("input:checked") || {}).value || 0);
    row.addEventListener("change", () => {
      paint(checked());
      row.querySelector(".rating-value").textContent = `${checked()}/5`;
    });
    stars.forEach((s, i) => s.addEventListener("mouseenter", () => paint(i + 1)));
    row.querySelector(".stars").addEventListener("mouseleave", () => paint(checked()));
  });
}

// ---------- Photo ----------
$("photo").addEventListener("change", e => {
  const file = e.target.files[0];
  const preview = $("photoPreview");
  photoFile = null;
  preview.style.backgroundImage = "";
  preview.classList.remove("has-photo");
  if (!file) return;
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
    e.target.value = "";
    return showError("The photo must be a JPG, PNG or WebP image.");
  }
  if (file.size > MAX_PHOTO) {
    e.target.value = "";
    return showError("The photo is larger than 2 MB. Pick a smaller one or resize it.");
  }
  clearError();
  photoFile = file;
  preview.style.backgroundImage = `url(${URL.createObjectURL(file)})`;
  preview.classList.add("has-photo");
});

field("teacher_observation").addEventListener("input", e => {
  $("obsCount").textContent = `${e.target.value.trim().length} / 800 characters (minimum 30)`;
});

// ---------- Submit ----------
function collect() {
  const v = n => field(n).value.trim();
  return {
    student: {
      school_name: v("school_name"),
      name: v("name"),
      gender: (form.querySelector("input[name=gender]:checked") || {}).value,
      class_name: v("class_name"),
      academic_year: v("academic_year"),
      roll_number: v("roll_number"),
    },
    nature_traits: [...form.querySelectorAll("input[name=trait]:checked")].map(i => i.value),
    wellness: Object.fromEntries(options.wellness_categories.map(c =>
      [c.key, Number((form.querySelector(`input[name=r_${c.key}]:checked`) || {}).value || 0)])),
    teacher_observation: v("teacher_observation"),
  };
}

function checkExtras(data) {
  const problems = [];
  const n = data.nature_traits.length;
  if (n < 3 || n > 8) {
    problems.push(`Nature & behaviour: tick between 3 and 8 qualities (you have ${n}).`);
    $("traitCount").classList.add("bad");
  }
  const missing = options.wellness_categories.filter(c => !data.wellness[c.key]).map(c => c.label);
  if (missing.length) problems.push(`Overall wellness: give a star rating for ${missing.join(", ")}.`);
  if (data.teacher_observation.length < 30) problems.push("Teacher's observation: write at least 30 characters.");
  return problems;
}

async function runGenerate(id) {
  clearError();
  setProgress("The AI is writing the report. This usually takes 10 to 20 seconds…");
  try {
    await API.generate(id);
    location.href = `/report.html?id=${id}`;
  } catch (e) {
    setProgress("");
    showError(`The student's details are saved, but the AI step failed:\n${e.message}`, id);
  }
}

form.addEventListener("submit", async e => {
  e.preventDefault();
  clearError();
  if (!form.reportValidity()) return;
  const data = collect();
  const problems = checkExtras(data);
  if (problems.length) return showError(problems.join("\n"));

  $("submitBtn").disabled = true;
  setProgress("Saving the student's details…");
  let report;
  try {
    report = await API.create(data);
  } catch (err) {
    setProgress("");
    $("submitBtn").disabled = false;
    return showError(err.message);
  }
  saveLast(data.student);

  if (photoFile) {
    setProgress("Uploading the photo…");
    try { await API.uploadPhoto(report.id, photoFile); }
    catch { /* the report still works without a photo; it can be retried later */ }
  }
  await runGenerate(report.id);
  $("submitBtn").disabled = false;
});

// ---------- Start ----------
(async function init() {
  try {
    options = await API.options();
  } catch (e) {
    $("submitBtn").disabled = true;
    return showError(e.message);
  }
  renderTraits();
  renderRatings();
  const last = loadLast();
  field("school_name").value = last.school_name || "";
  field("class_name").value = last.class_name || "";
  field("academic_year").value = last.academic_year || defaultYear();

  API.list().then(rs => {
    const schools = [...new Set(rs.map(r => r.teacher_input.student.school_name))];
    $("schoolList").innerHTML = schools.map(s => `<option value="${esc(s)}">`).join("");
  }).catch(() => {});
})();
