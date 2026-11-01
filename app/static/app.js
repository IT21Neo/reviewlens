// ReviewLens UI. Review text and model output are untrusted: they are always inserted with
// textContent (via h()), never parsed as HTML.
const SENTIMENTS = ["positive", "neutral", "negative"];
const ASPECTS = ["taste", "price", "service", "comfort", "portion", "other"];
const ASPECT_TH = {taste: "รสชาติ", price: "ราคา", service: "บริการ", comfort: "สถานที่/บรรยากาศ", portion: "ปริมาณ", other: "อื่นๆ"};

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}
const $ = (id) => document.getElementById(id);
const pct = (x) => (x === null || x === undefined ? "—" : x.toFixed(3));

async function api(path, body) {
  const res = await fetch(path, body ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)} : {});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((e) => e.msg).join("; ") : `HTTP ${res.status}`);
  }
  return data;
}

// ---------- tabs ----------
function showTab(name) {
  document.querySelectorAll("nav button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((s) => s.classList.toggle("active", s.id === name));
  if (name === "evaluation" && !evalLoaded) loadEvaluation();
}
document.querySelectorAll("nav button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));

function sentTag(s) { return s ? h("span", {class: `tag ${s}`}, s) : h("span", {class: "tag"}, "not analysed"); }
function aspectTags(list, cls = "") { return list.map((a) => h("span", {class: `tag ${cls}`, title: ASPECT_TH[a] || ""}, a)); }

// ---------- dashboard ----------
async function loadDashboard() {
  const s = await api("/api/stats");
  $("disclaimer").textContent = s.disclaimer;
  const cards = $("sent-cards");
  cards.replaceChildren(
    h("div", {class: "card"}, h("div", {class: "num"}, s.analysed), h("div", {class: "hint"}, `reviews analysed${s.failed ? ` (${s.failed} failed)` : ""}`)),
    ...SENTIMENTS.map((k) => h("div", {class: "card"},
      h("div", {class: "num"}, `${s.sentiment[k].percent}%`),
      h("div", {class: "hint"}, `${k} (${s.sentiment[k].count})`))));
  const bars = $("aspect-bars");
  bars.replaceChildren(...ASPECTS.map((a) => {
    const v = s.aspects[a];
    const bar = h("div", {class: "bar", title: v.description},
      ...SENTIMENTS.map((k) => h("span", {class: k, style: `width:${s.analysed ? (100 * v.by_sentiment[k]) / s.analysed : 0}%`, title: `${k}: ${v.by_sentiment[k]}`})));
    return h("div", {class: "bar-row", onclick: () => { setFilters({aspect: a}); showTab("reviews"); }},
      h("div", {}, a, h("div", {class: "hint"}, ASPECT_TH[a])), bar, h("div", {class: "hint"}, `${v.count} (${v.percent}%)`));
  }));
}

// ---------- reviews ----------
const form = $("filters");
SENTIMENTS.forEach((s) => form.sentiment.append(h("option", {value: s}, s)));
ASPECTS.forEach((a) => form.aspect.append(h("option", {value: a}, `${a} – ${ASPECT_TH[a]}`)));
[5, 4, 3, 2, 1].forEach((r) => form.rating.append(h("option", {value: r}, `${r} stars`)));
let offset = 0;
const LIMIT = 20;

function setFilters(f) {
  for (const k of ["sentiment", "aspect", "rating", "q"]) form[k].value = f[k] || "";
  offset = 0;
  loadReviews();
}
function reviewCard(r) {
  return h("div", {class: "review"},
    h("div", {class: "meta"}, h("b", {}, r.review_id), `${r.rating}★`, sentTag(r.sentiment), ...aspectTags(r.aspects)),
    h("div", {class: "text"}, r.text),
    r.evidence.length ? h("ul", {class: "ev"}, ...r.evidence.map((e) => h("li", {}, `“${e}”`))) : null);
}
async function loadReviews() {
  const p = new URLSearchParams();
  for (const k of ["sentiment", "aspect", "rating", "q"]) if (form[k].value) p.set(k, form[k].value);
  p.set("offset", offset); p.set("limit", LIMIT);
  try {
    const d = await api(`/api/reviews?${p}`);
    $("review-count").textContent = d.total ? `${d.offset + 1}–${Math.min(d.offset + LIMIT, d.total)} of ${d.total} reviews` : "No reviews match.";
    $("review-list").replaceChildren(...d.items.map(reviewCard));
    $("prev").disabled = offset === 0;
    $("next").disabled = offset + LIMIT >= d.total;
  } catch (e) { $("review-list").replaceChildren(h("p", {class: "error"}, e.message)); }
}
form.addEventListener("submit", (e) => { e.preventDefault(); offset = 0; loadReviews(); });
$("prev").addEventListener("click", () => { offset = Math.max(0, offset - LIMIT); loadReviews(); });
$("next").addEventListener("click", () => { offset += LIMIT; loadReviews(); });

// ---------- ask ----------
const askForm = $("ask-form");
["How many negative reviews talk about service?", "รีวิวที่ชมเรื่องรสชาติมีกี่รีวิว ขอตัวอย่างด้วย", "ลูกค้าพูดถึงราคาว่ายังไงบ้าง"].forEach((q) =>
  $("ask-examples").append(h("button", {type: "button", onclick: () => { askForm.question.value = q; askForm.requestSubmit(); }}, q)));
askForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = askForm.querySelector("button"); btn.disabled = true;
  $("ask-out").replaceChildren(h("p", {class: "hint"}, "Thinking… (the model may call tools)"));
  try {
    const d = await api("/api/ask", {question: askForm.question.value});
    const steps = d.trace.map((t) => t.tool
      ? `[round ${t.round}] ${t.tool}(${JSON.stringify(t.validated_arguments ?? t.raw_arguments)}) ok=${t.ok}\n  → ${JSON.stringify(t.result).slice(0, 400)}`
      : `error: ${t.error}`);
    $("ask-out").replaceChildren(
      h("div", {class: "answer"}, d.answer),
      h("p", {class: "hint"}, `stopped_by=${d.stopped_by} · rounds=${d.rounds}${d.forced_retry ? " · empty reply retried" : ""} · tool calls=${d.trace.filter((t) => t.tool).length}`),
      h("h2", {}, "Tool trace"),
      h("div", {class: "trace"}, steps.length ? steps.join("\n") : "(no tool was called — the answer is not backed by a tool result)"));
  } catch (err) { $("ask-out").replaceChildren(h("p", {class: "error"}, err.message)); }
  btn.disabled = false;
});

// ---------- analyze ----------
const anForm = $("analyze-form");
anForm.text.addEventListener("input", () => { $("char-count").textContent = `${anForm.text.value.length} / 2000`; });
anForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = anForm.querySelector("button"); btn.disabled = true;
  const text = anForm.text.value;
  $("analyze-out").replaceChildren(h("p", {class: "hint"}, "Analyzing…"));
  try {
    const d = await api("/api/analyze", {text});
    if (d.status === "failed") {
      $("analyze-out").replaceChildren(h("p", {class: "error"}, `Analysis failed after ${d.attempts} attempt(s): ${d.error}. No label is guessed.`));
    } else {
      $("analyze-out").replaceChildren(h("div", {class: "review"},
        h("div", {class: "meta"}, sentTag(d.sentiment), ...aspectTags(d.aspects), `status=${d.status} · ${d.latency_s}s · prompt ${d.prompt_version}`),
        h("ul", {class: "ev"}, ...d.evidence.map((ev, i) => h("li", {class: d.evidence_verified[i] ? "" : "bad"},
          `“${ev}” `, d.evidence_verified[i] ? "✓ found in text" : "✗ not found verbatim — do not trust")))));
    }
  } catch (err) { $("analyze-out").replaceChildren(h("p", {class: "error"}, err.message)); }
  btn.disabled = false;
});

// ---------- evaluation ----------
let evalLoaded = false, evalData = null;
function table(head, rows) {
  return h("div", {class: "scroll"}, h("table", {}, h("tr", {}, ...head.map((x) => h("th", {}, x))), ...rows.map((r) => h("tr", {}, ...r))));
}
function caseCard(c) {
  const ok = c.all_correct;
  return h("div", {class: `review ${ok ? "ok-box" : "bad-box"}`},
    h("div", {class: "meta"}, h("b", {}, c.review_id), `${c.rating}★`, `status=${c.status}`),
    h("div", {class: "meta"}, "gold:", sentTag(c.gold_sentiment), ...aspectTags(c.gold_aspects)),
    h("div", {class: "meta"}, "model:", sentTag(c.pred_sentiment), ...aspectTags(c.pred_aspects),
      c.sentiment_correct ? null : h("b", {class: "error"}, "sentiment wrong")),
    c.missed_aspects.length ? h("div", {class: "meta"}, "missed:", ...aspectTags(c.missed_aspects, "miss")) : null,
    c.extra_aspects.length ? h("div", {class: "meta"}, "extra:", ...aspectTags(c.extra_aspects, "extra")) : null,
    h("div", {class: "text"}, c.text),
    h("ul", {class: "ev"}, ...c.evidence.map((ev, i) => h("li", {class: c.evidence_verified[i] ? "" : "bad"}, `“${ev}”`))));
}
function showCases(fail) {
  $("show-fail").classList.toggle("active", fail);
  $("show-ok").classList.toggle("active", !fail);
  const list = fail ? evalData.cases.failures : evalData.cases.successes;
  $("case-list").replaceChildren(...list.map(caseCard));
}
async function loadEvaluation() {
  try {
    evalData = await api("/api/evaluation");
    evalLoaded = true;
  } catch (e) { $("metric-table").replaceChildren(h("p", {class: "error"}, e.message)); return; }
  const m = evalData.metrics;
  $("metric-table").replaceChildren(m.available
    ? table(["method", "sentiment acc", "sentiment macro F1", "aspect micro F1", "evidence validity", "failed"],
        m.rows.map((r) => [h("td", {}, r.method), ...[r.sentiment_accuracy, r.sentiment_macro_f1, r.aspect_micro_f1, r.evidence_validity].map((x) => h("td", {class: "num"}, pct(x))), h("td", {class: "num"}, r.failed_or_missing)]))
    : h("p", {class: "error"}, `${m.file} not found`));
  if (m.available) $("metric-table").append(h("p", {class: "hint"}, `n=${m.n} test reviews · generated ${m.generated} · source ${m.file}. Small sample: one review changes accuracy by 0.033.`));
  const a = evalData.agent;
  $("agent-table").replaceChildren(a.available
    ? h("div", {},
        h("p", {class: "hint"}, Object.entries(a.summary).map(([k, v]) => `${k} ${pct(v.score)} (n=${v.n})`).join(" · ") + ` · source ${a.file}`),
        table(["id", "question", "tools called", "right tool", "right args", "answer ok", "answer"],
          a.rows.map((r) => [r.id, r.question, r.tools_called.map((t) => `${t[0]} ${JSON.stringify(t[1])}`).join("; ") || "—",
            String(r.tool_choice), String(r.args_exact), r.answer_ok === null ? "not scored" : String(r.answer_ok), r.answer || "(empty)"]
            .map((x, i) => h("td", {class: i >= 3 && i <= 5 && (x === "false") ? "error" : ""}, x)))))
    : h("p", {class: "hint"}, "No agent evaluation file found."));
  const c = evalData.cases;
  $("case-summary").textContent = `${c.all_correct} of ${c.n} test reviews fully correct (sentiment, exact aspect set and all evidence verbatim). ` +
    `${c.failures.length} have at least one difference from the hand-checked label. Gold labels were Claude-suggested and author-checked, so they can be wrong too.`;
  showCases(true);
}
$("show-fail").addEventListener("click", () => showCases(true));
$("show-ok").addEventListener("click", () => showCases(false));

loadDashboard().catch((e) => $("sent-cards").replaceChildren(h("p", {class: "error"}, e.message)));
loadReviews();
