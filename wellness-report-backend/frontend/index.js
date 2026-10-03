let reports = [];
const $ = id => document.getElementById(id);

function showError(msg) { $("error").textContent = msg; $("error").hidden = !msg; }

function fillSelect(sel, values, allLabel) {
  const current = sel.value;
  sel.innerHTML = `<option value="">${allLabel}</option>` +
    values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join("");
  if (values.includes(current)) sel.value = current;
}

function fillFilters() {
  const uniq = arr => [...new Set(arr)].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  fillSelect($("school"), uniq(reports.map(r => r.teacher_input.student.school_name)), "All schools");
  const school = $("school").value;
  const forSchool = reports.filter(r => !school || r.teacher_input.student.school_name === school);
  fillSelect($("cls"), uniq(forSchool.map(r => r.teacher_input.student.class_name)), "All classes");
}

function render() {
  const list = $("list");
  $("filters").hidden = reports.length === 0;

  if (reports.length === 0) {
    list.innerHTML = `<div class="empty">
      <h2>No reports yet</h2>
      <p>Enter a student's details and the AI will write their wellness report.</p>
      <a class="btn primary large" href="/new.html">Create the first report</a></div>`;
    return;
  }

  const q = $("q").value.trim().toLowerCase();
  const school = $("school").value, cls = $("cls").value;
  const rows = reports
    .filter(r => {
      const s = r.teacher_input.student;
      return (!q || s.name.toLowerCase().includes(q)) &&
             (!school || s.school_name === school) &&
             (!cls || s.class_name === cls);
    })
    .sort((a, b) => {
      const x = a.teacher_input.student, y = b.teacher_input.student;
      return x.school_name.localeCompare(y.school_name) ||
             x.class_name.localeCompare(y.class_name, undefined, { numeric: true }) ||
             x.roll_number.localeCompare(y.roll_number, undefined, { numeric: true });
    });

  if (rows.length === 0) {
    list.innerHTML = `<div class="empty"><h2>No matching students</h2><p>Try a different name, school or class.</p></div>`;
    return;
  }

  list.innerHTML = `<div class="table-wrap"><table>
    <thead><tr><th>Roll no.</th><th>Student</th><th>Class</th><th>Year</th><th>School</th><th>Status</th><th><span class="sr">Actions</span></th></tr></thead>
    <tbody>${rows.map(r => {
      const s = r.teacher_input.student;
      const main = r.status === "generated"
        ? `<a class="btn secondary small" href="/report.html?id=${r.id}">View report</a>`
        : `<button class="btn primary small" data-generate="${r.id}">${r.status === "failed" ? "Try again" : "Generate"}</button>`;
      return `<tr>
        <td>${esc(s.roll_number)}</td>
        <td class="name">${esc(s.name)}</td>
        <td>${esc(s.class_name)}</td>
        <td>${esc(s.academic_year)}</td>
        <td class="school">${esc(s.school_name)}</td>
        <td><span class="status ${r.status}">${STATUS_TEXT[r.status]}</span></td>
        <td class="actions">${main}<button class="btn danger-text small" data-delete="${r.id}" data-name="${esc(s.name)}">Delete</button></td>
      </tr>`;
    }).join("")}</tbody></table></div>
    <p class="summary">Showing ${rows.length} of ${reports.length} reports</p>`;
}

async function load() {
  try {
    reports = await API.list();
    showError("");
  } catch (e) { showError(e.message); }
  fillFilters();
  render();
}

$("list").addEventListener("click", async e => {
  const gen = e.target.closest("[data-generate]");
  const del = e.target.closest("[data-delete]");
  if (gen) {
    gen.disabled = true;
    gen.textContent = "Writing…";
    try {
      await API.generate(gen.dataset.generate);
      location.href = `/report.html?id=${gen.dataset.generate}`;
    } catch (err) { showError(err.message); load(); }
  }
  if (del && confirm(`Delete the report for ${del.dataset.name}? This can't be undone.`)) {
    try { await API.remove(del.dataset.delete); load(); }
    catch (err) { showError(err.message); }
  }
});
$("q").addEventListener("input", render);
$("school").addEventListener("change", () => { fillFilters(); render(); });
$("cls").addEventListener("change", render);

load();
