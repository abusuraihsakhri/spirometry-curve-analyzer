/**
 * Browser-only waveform measurement extraction.
 * No reference equations, clinical classification, network calls or storage.
 */
function columns(line) {
  const out = [];
  let value = "", quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') { value += '"'; i++; }
      else quoted = !quoted;
    } else if (ch === "," && !quoted) { out.push(value.trim()); value = ""; }
    else value += ch;
  }
  if (quoted) throw new Error("Unclosed CSV quotation");
  out.push(value.trim());
  return out;
}
const finite = x => typeof x === "number" && Number.isFinite(x);
const interp = (x, xs, ys) => {
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  let lo = 0, hi = xs.length - 1;
  while (hi - lo > 1) {
    const mid = (hi + lo) >>> 1;
    if (xs[mid] <= x) lo = mid; else hi = mid;
  }
  return ys[lo] + (ys[hi] - ys[lo]) * (x - xs[lo]) / (xs[hi] - xs[lo]);
};

export function parseWaveformCsv(content) {
  if (typeof content !== "string" || content.length > 2_000_000)
    throw new Error("CSV must be text and less than 2 MB");
  const lines = content.replace(/^\uFEFF/, "").split(/\r?\n/).filter(l => l.trim());
  if (lines.length < 4 || lines.length > 20001)
    throw new Error("Provide 3–20,000 waveform samples plus a header");
  const header = columns(lines.shift()).map(s => s.toLowerCase().trim());
  const time = header.findIndex(h => /time|sec/.test(h));
  const flow = header.findIndex(h => /flow/.test(h));
  const volume = header.findIndex(h => /volume|^vol[_\s(]/.test(h));
  if (time < 0 || (flow < 0 && volume < 0))
    throw new Error("Expected time and flow or volume columns");
  const kind = flow >= 0 ? "flow" : "volume";
  const metric = flow >= 0 ? flow : volume;
  const timeScale = /(?:^|[^a-z])ms(?:[^a-z]|$)|milli/.test(header[time]) ? 0.001 : 1;
  const metricScale = /(?:^|[^a-z])ml(?:[^a-z]|$)|millil/.test(header[metric]) ? 0.001 : 1;
  const samples = lines.map((line, index) => {
    const row = columns(line);
    if (!row[time]?.trim() || !row[metric]?.trim())
      throw new Error("Missing numeric data at row " + (index + 2));
    const t = Number(row[time]) * timeScale;
    const value = Number(row[metric]) * metricScale;
    if (!finite(t) || !finite(value))
      throw new Error("Invalid numeric data at row " + (index + 2));
    return { t, value };
  }).sort((a, b) => a.t - b.t);
  for (let i = 1; i < samples.length; i++)
    if (samples[i].t <= samples[i - 1].t)
      throw new Error("Time values must be unique");
  return { kind, samples };
}

export function analyzeWaveform({ kind, samples }) {
  if (!Array.isArray(samples) || samples.length < 3 || samples.length > 20000 ||
      !["flow", "volume"].includes(kind))
    throw new Error("Expected 3–20,000 flow-time or volume-time samples");
  const t = samples.map(p => p.t), values = samples.map(p => p.value);
  if (!t.every(finite) || !values.every(finite) ||
      t.some((v, i) => i > 0 && v <= t[i - 1]))
    throw new Error("Samples must be finite and strictly time-ordered");
  const n = t.length, v = Array(n).fill(0), f = Array(n).fill(0);
  if (kind === "flow") {
    for (let i = 0; i < n; i++) {
      f[i] = values[i];
      if (i) v[i] = v[i - 1] + (f[i] + f[i - 1]) * (t[i] - t[i - 1]) / 2;
    }
  } else {
    for (let i = 0; i < n; i++) v[i] = values[i] - values[0];
    for (let i = 0; i < n; i++) {
      const j = Math.max(0, i - 1), k = Math.min(n - 1, i + 1);
      f[i] = (v[k] - v[j]) / (t[k] - t[j]);
    }
  }
  const pef = Math.max(...f);
  if (!(pef > 0) || !finite(pef)) throw new Error("No positive expiratory flow");
  const peak = f.indexOf(pef);
  const t0 = Math.max(t[0], t[peak] - v[peak] / pef);
  if (t[n - 1] < t0 + 1) throw new Error("At least 1 s after the corrected start is required");
  const mono = v.map((value, i) => i ? Math.max(value, v[i - 1]) : value);
  // Use a true cumulative maximum, including a possible noise dip after PEF.
  for (let i = 1; i < n; i++) mono[i] = Math.max(mono[i], mono[i - 1]);
  const v0 = interp(t0, t, mono);
  const fvc = mono[n - 1] - v0;
  if (!(fvc > 0)) throw new Error("Derived FVC is not positive");
  const fev1 = Math.min(fvc, Math.max(0, interp(t0 + 1, t, mono) - v0));
  const t25 = interp(v0 + .25 * fvc, mono, t);
  const t75 = interp(v0 + .75 * fvc, mono, t);
  const fef2575 = t75 > t25 ? .5 * fvc / (t75 - t25) : null;
  const bev = Math.max(0, v0 - mono[0]);
  return {
    fvc, fev1, ratio: fev1 / fvc, pef, fef2575,
    bev, bevPct: 100 * bev / fvc, t0,
    bevFlag: bev > Math.max(0.1, .05 * fvc),
    chart: { volume: v.map(x => x - v0), flow: f },
    disclaimer: "Exploratory measurements only. Not a validated clinical spirometry report."
  };
}

export function demoWaveform(fvc = 5.1, fev1 = 4.2) {
  if (!(fvc > fev1 && fev1 > 0)) throw new Error("Invalid demo parameters");
  const k = -Math.log(1 - fev1 / fvc);
  return {
    kind: "flow",
    samples: Array.from({ length: 1200 }, (_, i) => {
      const t = i * 8 / 1199;
      return { t, value: fvc * k * Math.exp(-k * t) };
    })
  };
}
