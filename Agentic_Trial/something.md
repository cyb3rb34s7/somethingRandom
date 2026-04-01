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

---

You should see a clean JSON output in your terminal for each run. If Gemini returns the model name differently on your key (sometimes it's `gemini-1.5-flash` or `gemini-2.0-flash` depending on tier), just swap the `--model` value accordingly.
