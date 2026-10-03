// Shared helpers used by every page.

const FIELD_LABELS = {
  school_name: "School name", name: "Student name", gender: "Gender",
  class_name: "Class", academic_year: "Academic year", roll_number: "Roll number",
  nature_traits: "Nature & behaviour", teacher_observation: "Teacher's observation",
};

class ApiError extends Error {
  constructor(status, body) {
    super(ApiError.describe(status, body));
    this.status = status;
  }
  static describe(status, body) {
    const d = body && body.detail;
    if (Array.isArray(d)) {
      return d.map(e => {
        const key = e.loc[e.loc.length - 1];
        return `${FIELD_LABELS[key] || e.loc.slice(1).join(" > ")}: ${e.msg}`;
      }).join("\n");
    }
    if (typeof d === "string") return d;
    return `The server returned an error (${status}).`;
  }
}

const API = {
  async request(path, opts = {}) {
    let res;
    try {
      res = await fetch(path, opts);
    } catch {
      throw new Error("Can't reach the server. Check that it's running in VS Code, then try again.");
    }
    if (res.status === 204) return null;
    let body = null;
    try { body = await res.json(); } catch { /* empty body */ }
    if (!res.ok) throw new ApiError(res.status, body);
    return body;
  },
  options: () => API.request("/api/meta/options"),
  list: () => API.request("/api/reports"),
  get: id => API.request(`/api/reports/${id}`),
  create: data => API.request("/api/reports", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  }),
  uploadPhoto: (id, file) => {
    const fd = new FormData();
    fd.append("file", file);
    return API.request(`/api/reports/${id}/photo`, { method: "POST", body: fd });
  },
  generate: id => API.request(`/api/reports/${id}/generate`, { method: "POST" }),
  remove: id => API.request(`/api/reports/${id}`, { method: "DELETE" }),
};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function initials(text, max = 2) {
  return String(text || "")
    .split(/\s+/)
    .filter(w => w && !/^(the|of|and|&)$/i.test(w))
    .slice(0, max)
    .map(w => w[0].toUpperCase())
    .join("");
}

const STATUS_TEXT = { generated: "Ready", draft: "Not generated", failed: "AI step failed" };
