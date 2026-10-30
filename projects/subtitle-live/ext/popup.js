const API = "http://127.0.0.1:8321";
const $ = (id) => document.getElementById(id);
const RANGES = ["cue_poll", "cue_stable", "tts_rate", "duck",
                "bottom_frac", "tr_pt", "de_pt"];
const CHECKS = ["speak", "show_de", "feed_subs"];

let refresh = null;

function setStatus(s) {
  const el = $("status");
  el.textContent = s.running ? "RUNNING" : "stopped";
  el.className = "status " + (s.running ? "on" : "off");
  $("pid").textContent = s.running ? "pid " + s.pid : "";
  $("log").textContent = s.log || "(no log yet)";
  $("log").scrollTop = $("log").scrollHeight;
}

function fill(t) {
  for (const k of RANGES) {
    if (t[k] != null) { $(k).value = t[k]; $("v_" + k).textContent = t[k]; }
  }
  for (const k of CHECKS) if (t[k] != null) $(k).checked = !!t[k];
  if (t.lang) $("lang").value = t.lang;
  if (t.tts) $("tts").value = t.tts;
  if (t.voice) $("voice").value = t.voice;
  if (t.src_lang) $("src_lang").value = t.src_lang;
  if (t.mt === "local" && t.mt_model) $("mt").value = t.mt_model;
  else if (t.mt === "strata") $("mt").value = "strata";
}

function buildMt(roster) {
  const sel = $("mt");
  if (!roster || !roster.length) return;
  const sig = roster.map(m => m.id).join(",");
  if (sel.dataset.built === sig) return;
  sel.innerHTML = "";
  const add = (v, label, dis) => {
    const o = document.createElement("option");
    o.value = v; o.textContent = label; o.disabled = !!dis;
    sel.appendChild(o);
  };
  add("strata", "Strata (best quality)");
  for (const m of roster) {
    if (m.id === "strata") continue;   // already added above
    if (m.kind === "text-mt")
      add(m.id, m.label + (m.status === "ready" ? "" : " [" + m.status + "]"),
          m.status !== "ready");
    else
      add(m.id, m.label + " — " + m.status + " (audio mode)", true);
  }
  sel.dataset.built = sig;
}

async function status() {
  try {
    const s = await (await fetch(API + "/status")).json();
    setStatus(s); buildMt(s.roster || []); fill(s.tuning || {});
  } catch (e) {
    $("status").textContent = "subctl DOWN";
    $("status").className = "status off";
    $("hint").textContent = "start subctl: python subctl.py";
  }
}

async function tune(key, value) {
  try {
    const r = await (await fetch(API + "/tune", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [key]: value })
    })).json();
    if (r.needRestart && r.needRestart.length)
      $("hint").textContent = "restart to apply: " + r.needRestart.join(", ");
    else $("hint").textContent = "";
    status();
  } catch (e) { $("hint").textContent = "tune failed — subctl down?"; }
}

async function action(ep) {
  $("hint").textContent = ep + "…";
  try {
    const r = await (await fetch(API + "/" + ep, { method: "POST" })).json();
    $("hint").textContent = r.out || (r.ok ? "ok" : "failed");
  } catch (e) { $("hint").textContent = "subctl down?"; }
  setTimeout(status, 400);
}

for (const k of RANGES) {
  $(k).addEventListener("change", () => {
    $("v_" + k).textContent = $(k).value;
    tune(k, parseFloat($(k).value));
  });
}
for (const k of CHECKS)
  $(k).addEventListener("change", () => tune(k, $(k).checked));
$("lang").addEventListener("change", () => tune("lang", $("lang").value));
$("src_lang").addEventListener("change", () => tune("src_lang", $("src_lang").value));
$("voice").addEventListener("change", () => tune("voice", $("voice").value));
$("tts").addEventListener("change", () => tune("tts", $("tts").value));
$("mt").addEventListener("change", async () => {
  const v = $("mt").value;
  $("hint").textContent = "switching translator… (flex + model load)";
  try {
    const r = await (await fetch(API + "/mt", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: v === "strata" ? "off" : v })
    })).json();
    $("hint").textContent = r.ok ? "translator: " + v : (r.error || r.out || "failed");
  } catch (e) { $("hint").textContent = "mt switch failed — subctl down?"; }
  status();
});
$("start").addEventListener("click", () => action("start"));
$("stop").addEventListener("click", () => action("stop"));
$("restart").addEventListener("click", () => action("restart"));

status();
refresh = setInterval(status, 2000);
