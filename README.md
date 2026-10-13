# Spirometry Curve Analyzer

A Python toolkit and browser viewer for exploratory analysis of digitized spirometry waveforms. **For education and research only — not validated for clinical use.**

## Browser viewer

The static application in [web/](web/) reads time-series CSV files entirely locally, derives expiratory FVC, FEV1, FEV1/FVC, PEF, FEF25–75, and back-extrapolated volume, draws a flow–volume plot, and exports JSON measurements.

1. Supply a CSV containing a time column (e.g., `time_s`) and either flow (`flow_Lps`) or volume (`volume_L`). The maximum is 20,000 samples / 2 MB.
2. Select **Analyze CSV**, or choose one of two synthetic examples.
3. Inspect the measurements and the back-extrapolated volume warning. Optionally export the JSON result.

All calculations and plotting for the browser viewer use JavaScript; no Python runtime, backend calls, cookies, analytics, or remote uploads are required. Maneuver acceptability, repeatability, end-of-test plateau, and inspiratory data are not established. No clinical diagnosis or validated predicted value is provided.

Run locally from the repository root:

```bash
python -m http.server 8000
# Open http://localhost:8000/web/
```

The workflow publishes the `web/` directory to GitHub Pages on successful pushes to `master`. Repository Pages settings must select **GitHub Actions** as the deployment source. Do not treat the intended URL as a verified working deployment until it has been independently checked.

## Python toolkit

Tested in CI with Python 3.10–3.12. Requires NumPy, SciPy, Matplotlib, Pydantic, FastAPI, and Uvicorn.

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m spirometry_analyzer.cli sample_data/normal_male_42y.csv --age 42 --height 178 --sex M --plot example.png
python cli.py single --fev1 3.5 --fvc 4.5 --age 40 --height 175 --sex M
python cli.py predicted --age 40 --height 175 --sex M
python cli.py batch -i input.csv -o results.csv
```

- `spirometry_analyzer/`: waveform extraction, exploratory interpretation and plotting. Its `gli2012.py` coefficients are **approximations**, not the published GLI-2012 tables; adult reference values, LLN and z-scores are **not clinically validated**.
- `spiro_analyze.py`: legacy simplified NHANES-like calculations and pattern thresholds. Its GOLD stage is illustrative; COPD staging requires an established clinical diagnosis and post-bronchodilator measurements. Its 12% + 200 mL bronchodilator response rule is a **historical 2005 rule**, not the current 2022 ERS/ATS recommendation.

The 2022 ERS/ATS interpretive standard defines a positive bronchodilator response as an increase **greater than 10% of the predicted** FEV1 or FVC, rather than a percentage of the initial measured value: [ERS/ATS interpretation](https://publications.ersnet.org/content/erj/60/1/2101499).

For patient care, use quality-assured instrumentation and verified reference equations, not this repository's exploratory calculations.

## REST API and security

The optional FastAPI service exposes public `/health` and bearer-token-protected `/metrics`, `/api/audit`, `/api/chat`, and `/api/audit/logs` endpoints. The supervisor uses generic, deterministic mock rules, **not validated clinical thresholds or clinical verification**.

```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export API_ACCESS_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python cli.py serve --host 127.0.0.1 --port 8000
curl -H "Authorization: Bearer $API_ACCESS_TOKEN" http://127.0.0.1:8000/metrics
# Alternatively, with both variables exported: docker compose up --build
```

Do not submit actual patient identifiers. The PHI interceptor is regex-based and not a comprehensive HIPAA de-identification solution. HMAC-chained audit records are held only **in memory**: they are not durable or verified across restarts. With no `AUDIT_SECRET_KEY`, a random ephemeral development key is generated. Production operation requires durable audit storage, transport security, operational monitoring and further review.

## Testing

```bash
python -m pytest -q
node --check web/analyzer.mjs
node --test web/analyzer.test.mjs
```

Key directories: `spirometry_analyzer/` (core Python), `agents/` (API/mock supervisor), `tests/` (Python tests), `sample_data/` (synthetic CSV), `web/` (browser app), and `.github/workflows/` (CI/deployment).

The browser viewer requires a modern browser with JavaScript modules, SVG, and the local File API. No Pyodide or Python-in-browser runtime is used.

## License

MIT; see [LICENSE](LICENSE).
