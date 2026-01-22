import os
import io
import requests
from flask import Flask, render_template, request
from dotenv import load_dotenv
from pathlib import Path
import PyPDF2
import google.generativeai as genai

load_dotenv(Path(".") / ".env")

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not HF_API_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("Variáveis de ambiente não carregadas corretamente.")

app = Flask(__name__)

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-pro")

CLASSIFICATION_API_URL = (
    "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"
)

headers = {
    "Authorization": f"Bearer {HF_API_TOKEN}"
}

def query_api(payload, url):
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    try:
        return response.json()
    except Exception:
        return {"error": response.text}

def classify_email(text):
    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": ["Productive", "Unproductive"]
        }
    }

    output = query_api(payload, CLASSIFICATION_API_URL)

    if "error" in output:
        print("Erro HF:", output["error"])
        return "Improdutivo"

    labels = output.get("labels", [])
    if not labels:
        return "Improdutivo"

    return "Produtivo" if labels[0] == "Productive" else "Improdutivo"

def generate_response(classification, email_text):
    if classification == "Produtivo":
        prompt = f"""
Você recebeu o seguinte email de trabalho.

Classificação: PRODUTIVO

Escreva uma resposta profissional, objetiva e educada em português do Brasil.

Email:
---
{email_text}
---

Resposta:
"""
    else:
        prompt = f"""
Você recebeu o seguinte email.

Classificação: IMPRODUTIVO

Escreva uma resposta educada e neutra, apenas agradecendo o contato,
sem indicar ações futuras.

Email:
---
{email_text}
---

Resposta:
"""
        
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Erro ao gerar resposta automática: {e}"

@app.route("/", methods=["GET", "POST"])
def index():
    classification = None
    suggestion = None
    email_text = ""

    if request.method == "POST":
        email_text_from_form = request.form.get("email_text")
        email_file = request.files.get("email_file")

        if email_file and email_file.filename:
            if email_file.filename.endswith(".txt"):
                email_text = email_file.read().decode("utf-8")

            elif email_file.filename.endswith(".pdf"):
                try:
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(email_file.read()))
                    email_text = "".join(
                        page.extract_text() or "" for page in pdf_reader.pages
                    )
                except Exception as e:
                    email_text = f"Erro ao ler PDF: {e}"
        else:
            email_text = email_text_from_form or ""

        if email_text:
            email_text = email_text[:2000]
            classification = classify_email(email_text[:512])
            suggestion = generate_response(classification, email_text)

    return render_template(
        "index.html",
        classification=classification,
        suggestion=suggestion,
        email_text=email_text
    )

if __name__ == "__main__":
    app.run(debug=True)
