let lastQuestion = "";

const $ = (id) => document.getElementById(id);
const renderJson = (id, value) => { $(id).textContent = JSON.stringify(value, null, 2); };

function renderEvidence(id, evidence) {
  const list = $(id);
  list.innerHTML = "";
  evidence.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${item.title} (${item.source}, score ${item.score}): ${item.snippet}`;
    list.appendChild(li);
  });
}

function renderKpis(data) {
  const metrics = [
    ["Vector evidence", data.vector.metrics.evidence_count],
    ["Wiki evidence", data.wiki.metrics.evidence_count],
    ["Fastest", data.comparison.fastest],
    ["Wiki score Δ", data.comparison.wiki_top_score_delta],
    ["Vector backend", data.vector.metrics.search_backend || "n/a"],
    ["Vector LLM", data.vector.metrics.llm_used ? data.vector.metrics.model : "off"],
    ["Wiki LLM", data.wiki.metrics.llm_used ? data.wiki.metrics.model : "off"],
  ];
  $("kpis").innerHTML = metrics.map(([label, value]) => `<div class="kpi"><span>${label}</span><strong>${value}</strong></div>`).join("");
}

$("inspect-wiki").addEventListener("click", async () => {
  const response = await fetch("/api/wiki");
  renderJson("wiki-json", await response.json());
  $("wiki-inspector").open = true;
});

$("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData();
  [...$("files").files].forEach((file) => form.append("files", file));
  renderJson("status", { state: "building" });
  const response = await fetch("/api/ingest", { method: "POST", body: form });
  renderJson("status", await response.json());
});

$("query-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  lastQuestion = $("question").value;
  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: lastQuestion, session_id: "demo" }),
  });
  const data = await response.json();
  $("vector-answer").textContent = data.vector.answer;
  $("wiki-answer").textContent = data.wiki.answer;
  renderEvidence("vector-evidence", data.vector.evidence);
  renderEvidence("wiki-evidence", data.wiki.evidence);
  renderKpis(data);
});

$("feedback-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: lastQuestion || $("question").value, correction: $("correction").value, rating: Number($("rating").value), session_id: "demo" }),
  });
  renderJson("feedback-result", await response.json());
});

fetch("/api/status").then((r) => r.json()).then((data) => renderJson("status", data));
