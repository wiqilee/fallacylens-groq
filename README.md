# 🧠 FallacyLens (Groq Edition)

FallacyLens is an AI-powered logical fallacy detection toolkit for arguments, essays, and debates.

This version uses the Groq Chat Completions API (e.g. `llama-3.3-70b-versatile`) as the
reasoning engine. Your Python code controls the prompt, parsing, and presentation.

---

## ✨ Features

- **Logical fallacy span detection** with severity + confidence
- **Inline highlighting** for detected fallacies in your text
- **Clarity / Persuasion / Reliability scores** (0–100)
- **Assistant tools**: rewrite, teacher feedback, persuasion optimizer, bias review
- **Batch CSV analysis** (column: `text`)
- **Multi-model comparison** across Groq-hosted models

---

## 🧰 Tech Stack

- **Python**
- **Streamlit** (demo UI)
- **FastAPI** (service API)
- **Groq Chat Completions API** (LLM inference)

---

## ⚙️ Setup

1. Create a Groq API key at https://console.groq.com.
2. Export your key as an environment variable:

   ```bash
   export GROQ_API_KEY="YOUR_REAL_GROQ_API_KEY"
   ```

   For quick local testing only, you can also edit `fallacylens/detector.py`
   and replace the string `"YOUR_GROQ_API_KEY_HERE"` with your real key,
   but you must not commit that to GitHub.

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the Streamlit demo:

   ```bash
   streamlit run demo/app.py
   ```

5. Run the FastAPI service:

   ```bash
   uvicorn api.main:app --reload
   ```

Notes:
- The Tinker / Thinking Machines API key is **not** used in this project.

---

## 🗂️ Project Structure

```text
.
├─ api/                 # FastAPI service
├─ demo/                # Streamlit demo app
├─ fallacylens/         # Core library (detector, models, taxonomy)
├─ requirements.txt
└─ README.md
```

---

## 🔐 Security Notes

- **Never commit secrets** (API keys, `.env`, or Streamlit secrets).
- Use environment variables (recommended) or your deployment platform’s secret manager.
- This repo includes a `.gitignore` that helps prevent accidental commits of credentials.

---

## 👤 Author

Built by **Wiqi Lee**  
X / Twitter: [@wiqi_lee](https://x.com/wiqi_lee)

---

## 📄 License

MIT — see [`LICENSE`](LICENSE).
