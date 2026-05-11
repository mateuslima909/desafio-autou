import os
import io
import PyPDF2
import google.generativeai as genai
from flask import Flask, render_template, request, flash
from dotenv import load_dotenv
from pathlib import Path

# 1. SEGURANÇA E CONFIGURAÇÕES (Pontos 3 e 4)
load_dotenv(Path(".") / ".env")

ALLOWED_EXTENSIONS = {'.txt', '.pdf'}
MAX_FILE_SIZE_MB = 2

app = Flask(__name__)
# Nunca use hardcoded. Se não houver no .env, gera uma string aleatória por segurança.
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE_MB * 1024 * 1024

# 2. CONFIGURAÇÃO DA IA (Pontos 5 e 6)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Baixa temperatura para classificação (Ponto 6)
generation_config = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1024,
}

gemini_model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=generation_config
)

# 3. FUNÇÕES DE SUPORTE (Ponto 1 e 3)
def allowed_file(filename):
    return '.' in filename and \
           Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def extract_text(file):
    """Extração segura e tipada (Ponto 1)."""
    if not file or not allowed_file(file.filename):
        return None
    
    try:
        ext = Path(file.filename).suffix.lower()
        if ext == ".txt":
            return file.read().decode("utf-8")
        elif ext == ".pdf":
            reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            return "".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e:
        # Ponto 1: Capturando a exceção específica para log, sem derrubar o sistema
        print(f"Erro crítico na extração do arquivo: {e}")
    return None

# 4. O CÉREBRO (Ponto 2, 5 e 7)
def analyze_email_pro(email_text):
    """Engenharia de Prompt Avançada com Score de Confiança (Ponto 5 e 7)."""
    
    prompt = f"""
    Você é um assistente executivo especializado em triagem de emails corporativos.
    Analise o conteúdo abaixo quanto à urgência, relevância operacional e contexto profissional.

    Classificações:
    - Produtivo: Requer ação, decisão ou agendamento.
    - Improdutivo: Spam, marketing, newsletters ou social sem contexto.

    Retorne EXATAMENTE neste formato:
    CLASSIFICAÇÃO: [Produtivo ou Improdutivo]
    CONFIANÇA: [valor de 0 a 100]%
    RESPOSTA: [Sua sugestão de resposta curta e profissional ou 'N/A']

    Email:
    ---
    {email_text[:4000]}
    ---
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        raw_text = response.text.upper()
        
        # Ponto 2: Parser muito mais seguro contra falsos positivos
        data = {
            "classification": "Produtivo",
            "confidence": "0",
            "suggestion": ""
        }

        if "CLASSIFICAÇÃO: IMPRODUTIVO" in raw_text:
            data["classification"] = "Improdutivo"
            data["suggestion"] = "Conteúdo de baixa relevância detectado."
        else:
            # Extração de Resposta e Confiança
            if "RESPOSTA:" in raw_text:
                data["suggestion"] = response.text.split("RESPOSTA:")[1].strip()
            if "CONFIANÇA:" in raw_text:
                data["confidence"] = raw_text.split("CONFIANÇA:")[1].split("%")[0].strip()

        return data
    except Exception as e:
        print(f"Erro na API Gemini: {e}")
        return None

# 5. ROTAS
@app.route("/", methods=["GET", "POST"])
def index():
    context = {"classification": None, "suggestion": None, "email_text": "", "confidence": None}

    if request.method == "POST":
        email_text = request.form.get("email_text", "")
        email_file = request.files.get("email_file")

        file_content = extract_text(email_file)
        if file_content:
            email_text = file_content
        
        context["email_text"] = email_text

        if email_text.strip():
            analysis = analyze_email_pro(email_text)
            if analysis:
                context.update(analysis)
            else:
                flash("Houve um erro na análise inteligente. Tente novamente.")

    return render_template("index.html", **context)

if __name__ == "__main__":
    app.run(debug=True)