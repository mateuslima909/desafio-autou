from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email_text = request.form.get('email_text')

        classification = "Produtivo (Simulação)"
        suggestion = "Resposta sugerida (Simulação): Obrigado por sua mensagem. Estamos analisando sua solicitação e retornaremos em breve."
    
        return render_template('index.html', 
                               classification = classification,
                               suggestion = suggestion,
                               email_text = email_text)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)