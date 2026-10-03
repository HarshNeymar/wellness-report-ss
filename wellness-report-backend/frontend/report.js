const $ = id => document.getElementById(id);
const reportId = new URLSearchParams(location.search).get("id");

const WELLNESS_STYLE = {
  confidence:          { icon: "💪", color: "#d9f1ee" },
  communication:       { icon: "💬", color: "#fdefcf" },
  teamwork:            { icon: "🤝", color: "#e0f1d9" },
  leadership:          { icon: "🚩", color: "#dbe7f6" },
  creativity:          { icon: "💡", color: "#fbe0e8" },
  responsibility:      { icon: "🛡️", color: "#ece2f8" },
  emotional_wellbeing: { icon: "🌸", color: "#fde6d6" },
};
const WELLNESS_LABELS = {
  confidence: "Confidence", communication: "Communication", teamwork: "Teamwork",
  leadership: "Leadership", creativity: "Creativity", responsibility: "Responsibility",
  emotional_wellbeing: "Emotional Wellbeing",
};
const PERSONALITY_ICONS = {
  "Future Leader": "🏅", "Creative Thinker": "🎨", "Curious Explorer": "🔭", "Kind Helper": "🤝",
  "Team Player": "🧩", "Confident Communicator": "🎤", "Disciplined Achiever": "🎯", "Calm Thinker": "🧘",
};

function stars(n) {
  return `<span class="r-stars" aria-label="${n} out of 5">${"★".repeat(n)}<span class="off">${"★".repeat(5 - n)}</span></span>`;
}

function buildSheet(r) {
  const t = r.teacher_input, s = t.student, ai = r.ai_output;
  const photo = r.photo_url
    ? `<div class="r-photo" style="background-image:url('${esc(r.photo_url)}')" role="img" aria-label="Photo of ${esc(s.name)}"></div>`
    : `<div class="r-photo">${esc(initials(s.name))}</div>`;
  const medals = ["🥇", "🥈", "🥉"];

  return `<article class="sheet"><div class="sheet-inner">
    <header class="r-head">
      <div class="r-school">
        <div class="r-crest">${esc(initials(s.school_name))}</div>
        <div class="r-school-name">${esc(s.school_name)}</div>
      </div>
      <div class="r-title">
        <h1>Wellness &amp; Personality Report</h1>
        <p>Discovering Strengths. Nurturing Potential. Building Future.</p>
      </div>
      <div class="r-tree" aria-hidden="true">🌳</div>
    </header>

    <div class="r-grid">
      <section class="panel r-snap">
        <h2 class="pill bg-teal">Student Snapshot</h2>
        ${photo}
        <dl class="r-details">
          <div><span class="ico" aria-hidden="true">👤</span><dt>Student Name</dt><dd>${esc(s.name)}</dd></div>
          <div><span class="ico" aria-hidden="true">🎓</span><dt>Class</dt><dd>${esc(s.class_name)}</dd></div>
          <div><span class="ico" aria-hidden="true">📅</span><dt>Academic Year</dt><dd>${esc(s.academic_year)}</dd></div>
          <div><span class="ico" aria-hidden="true">🪪</span><dt>Roll Number</dt><dd>${esc(s.roll_number)}</dd></div>
        </dl>
      </section>

      <section class="panel r-pers">
        <h2 class="pill edge bg-pink">Personality Type</h2>
        <div class="r-ring"><div aria-hidden="true">${PERSONALITY_ICONS[ai.personality_type] || "⭐"}</div></div>
        <div>
          <h3 class="r-type">${esc(ai.personality_type)}</h3>
          <p>${esc(ai.personality_description)}</p>
        </div>
        <div class="r-ribbon" aria-hidden="true">🎖️</div>
      </section>

      <section class="panel r-well">
        <h2 class="pill edge bg-teal">Overall Wellness Profile</h2>
        <ul>${Object.entries(t.wellness).map(([k, v]) => `
          <li>
            <div class="ico" style="background:${WELLNESS_STYLE[k].color}" aria-hidden="true">${WELLNESS_STYLE[k].icon}</div>
            <span class="lbl">${WELLNESS_LABELS[k]}</span>
            ${stars(v)}
          </li>`).join("")}
        </ul>
      </section>

      <section class="panel r-nature">
        <h2 class="pill bg-green">Nature &amp; Behaviour Profile</h2>
        <ul>${t.nature_traits.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
        <div class="r-kids" aria-hidden="true">👧📚👦</div>
      </section>

      <section class="panel r-zones">
        <div>
          <h2 class="pill left bg-orange">Student's Strong Zones</h2>
          ${ai.strong_zones.map((z, i) => `
            <div class="r-zone">
              <div class="medal" aria-hidden="true">${medals[i]}</div>
              <div><h3>${esc(z.title)}</h3><p>${esc(z.description)}</p></div>
            </div>`).join("")}
        </div>
        <div>
          <h2 class="pill left bg-purple">Hidden Potential / Emerging Talent</h2>
          <div class="r-potential">
            <div class="rocket" aria-hidden="true">🚀</div>
            <p>${esc(ai.hidden_potential)}</p>
          </div>
        </div>
      </section>

      <section class="panel r-obs">
        <div class="teacher">
          <h3><span class="ico" aria-hidden="true">🧑‍🏫</span>Teacher's Wellness Observation</h3>
          <p>${esc(t.teacher_observation)}</p>
        </div>
        <div class="growth">
          <h3><span class="ico" aria-hidden="true">🎯</span>Growth Recommendations</h3>
          <ul>${ai.growth_recommendations.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
        </div>
      </section>

      <section class="panel r-final">
        <h2 class="pill edge bg-gold">Final Conclusion</h2>
        <div class="r-trophy" aria-hidden="true">🏆</div>
        <div class="r-badge">
          <div class="script">Student Personality Badge</div>
          <div class="r-banner">${esc(ai.personality_type)}</div>
        </div>
        <p>${esc(ai.final_conclusion)}</p>
      </section>
    </div>

    <footer class="r-foot"><span><span class="heart">♥</span> Every Child is Unique. Every Child can Shine. <span class="heart">♥</span></span></footer>
  </div></article>`;
}

// Shrinks the report slightly when printing if the text is too long for one A4 page
function fitToPage() {
  const sheet = document.querySelector(".sheet");
  const inner = document.querySelector(".sheet-inner");
  if (!sheet || !inner) return;
  const available = (297 - 7 - 5 - 2.4) * 96 / 25.4; // A4 height minus padding and border, in px
  const needed = inner.scrollHeight;
  sheet.style.setProperty("--fit", needed > available ? (available / needed).toFixed(3) : "1");
}
window.addEventListener("beforeprint", fitToPage);

function showMessage(html) { $("msg").innerHTML = html; $("msg").hidden = false; }

function render(r) {
  const s = r.teacher_input.student;
  // The browser uses the page title as the PDF file name
  document.title = `${s.name} ${s.class_name} Wellness Report`.replace(/[^\w\s-]/g, "").replace(/\s+/g, "_");

  if (!r.ai_output) {
    $("report").innerHTML = `<div class="pending">
      <h2>${esc(s.name)}'s report isn't written yet</h2>
      <p>${r.status === "failed" ? "The last AI attempt failed. " : ""}The student's details are saved. Let the AI write the report now.</p>
      <button class="btn primary large" id="genNow">Write report with AI</button></div>`;
    $("genNow").onclick = regenerate;
    return;
  }
  $("report").innerHTML = buildSheet(r);
  fitToPage();
  document.fonts.ready.then(fitToPage);
  $("regenBtn").hidden = false;
  $("pdfBtn").hidden = false;
}

async function load() {
  if (!reportId) return showMessage(`<div class="alert error">No report selected. <a href="/">Go to all reports</a>.</div>`);
  try { render(await API.get(reportId)); }
  catch (e) { showMessage(`<div class="alert error">${esc(e.message)}</div>`); }
}

async function regenerate() {
  $("progress").hidden = false;
  try { render(await API.generate(reportId)); $("msg").hidden = true; }
  catch (e) { showMessage(`<div class="alert error">${esc(e.message)}</div>`); }
  finally { $("progress").hidden = true; }
}

$("regenBtn").onclick = () => {
  if (confirm("Rewrite the AI sections? The current text will be replaced.")) regenerate();
};
$("pdfBtn").onclick = () => window.print();

load();
