import test from "node:test";
import assert from "node:assert/strict";
import {analyzeWaveform,parseWaveformCsv,demoWaveform} from "./analyzer.mjs";

test("synthetic normal-like flow waveform produces plausible metrics",()=>{
 const r=analyzeWaveform(demoWaveform(5.1,4.2));
 assert.ok(Math.abs(r.fev1-4.2)<0.02);
 assert.ok(Math.abs(r.fvc-5.1)<0.05);
 assert.ok(Math.abs(r.ratio-4.2/5.1)<0.02);
 assert.ok(r.pef>0 && r.fef2575>0);
 assert.equal(r.bevFlag,false);
});
test("CSV flow headers parse and normalize millilitre/millisecond data",()=>{
 const parsed=parseWaveformCsv("time_ms,flow_ml/s\n0,2000\n500,1000\n1000,600\n1500,300");
 assert.equal(parsed.kind,"flow");
 assert.equal(parsed.samples[1].t,0.5);
 assert.equal(parsed.samples[1].value,1);
 assert.ok(analyzeWaveform(parsed).fev1>0);
});
test("volume waveform metrics are supported",()=>{
 const samples=Array.from({length:201},(_,i)=>{
   const t=i*.02;return {t,value:3*(1-Math.exp(-1.6*t))};
 });
 const r=analyzeWaveform({kind:"volume",samples});
 assert.ok(r.fvc>2.9 && r.fev1>1.9 && r.fev1<2.5);
});
test("invalid data cannot silently produce a measurement",()=>{
 assert.throws(()=>parseWaveformCsv("time_s,flow_Lps\n0,1\n0,2\n1,3"),/unique/);
 assert.throws(()=>parseWaveformCsv("time_s,flow_Lps\n0,1\n.5,NaN\n1,2"),/Invalid numeric/);
 assert.throws(()=>parseWaveformCsv("time_s,flow_Lps\n0,1\n.5,2\n1,"),/Missing numeric/);
 assert.throws(()=>analyzeWaveform({kind:"flow",samples:[{t:0,value:1},{t:.2,value:1},{t:.4,value:1}]}),/At least 1 s/);
});


test("browser HTML module script parses and links to local analyzer", async () => {
 const {readFileSync} = await import("node:fs");
 const {Script} = await import("node:vm");
 const html=readFileSync(new URL("./index.html",import.meta.url),"utf8");
 const match=html.match(/<script type="module">([\s\S]*?)<\/script>/);
 assert.ok(match,"inline module present");
 const code=match[1].replace(/^\s*import\s+\{[^}]+\}\s+from\s+["'][^"']+["'];/m,"");
 assert.doesNotThrow(()=>new Script(code));
 assert.match(html,/from "\.\/analyzer\.mjs"/);
});
