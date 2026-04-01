Now update the runner to include gemini as a valid choice and add the model default:Now update requirements.txt:Now zip everything up:Here's the zip. Steps to run:

---

**1. Unzip and enter the folder**
```bash
unzip correlation_engine.zip
cd correlation_engine
```

**2. Install dependencies**
```bash
pip install pydantic google-genai
```

**3. Set your API key**
```bash
export GEMINI_API_KEY=your-key-here
```

**4. Run against sample 1 — A→B (Inception → Shutter Island)**
```bash
python run_sample.py --sample a_to_b --provider gemini --model gemini-2.5-flash-preview-04-17
```

**5. Run against sample 2 — Critically Acclaimed (Parasite)**
```bash
python run_sample.py --sample critically_acclaimed --provider gemini --model gemini-2.5-flash-preview-04-17
```

















Now verify the structure is clean and zip it:Here's the zip. Steps to run:

---

**1. Setup**
```bash
unzip explainable_rec_pipeline.zip
cd explainable_rec_pipeline
pip install pydantic google-genai
export GEMINI_API_KEY=your-key-here
```

**2. Phase 1 — run to scene selection**
```bash
python run.py phase1 \
  --input samples/sample_a_to_b.json \
  --provider gemini \
  --model gemini-2.5-flash-preview-04-17
```

This runs T1→T2→T3→T5→T6A, then **pauses**. It prints something like:
```
State file: pipeline_state/state_2025-03-20_10-30-00.json
NEXT STEPS:
  1. Open pipeline_state/state_2025-03-20_10-30-00.json
  2. Find 'scene_selection.selectedScenes'
  3. Set 'clipStart' and 'clipEnd' for each scene
```

**3. Edit the state file**

Open the state file, find `selectedScenes`, and fill in the timestamps:
```json
"clipStart": 1860,
"clipEnd": 1920
```

**4. Phase 2 — produce the manifest**
```bash
python run.py phase2 \
  --state pipeline_state/state_2025-03-20_10-30-00.json \
  --provider gemini \
  --model gemini-2.5-flash-preview-04-17
```

Outputs `manifest_TIMESTAMP.json` in `output_manifests/` and a full structured log in `logs/TIMESTAMP/`.









---

You should see a clean JSON output in your terminal for each run. If Gemini returns the model name differently on your key (sometimes it's `gemini-1.5-flash` or `gemini-2.0-flash` depending on tier), just swap the `--model` value accordingly.
