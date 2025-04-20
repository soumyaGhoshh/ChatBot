from flask import Flask, render_template, request, session, jsonify
from google.generativeai import GenerativeModel
import os
import time
import textwrap

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['RATE_LIMIT'] = 5  # Seconds between requests

# Configure Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
model = GenerativeModel('gemini-1.5-pro')

def sanitize_text(text):
    """Remove unwanted formatting characters"""
    return text.replace('*', '').replace('_', '').strip()

def get_gemini_response(question, context, language):
    system_instruction = f"""
    You are a legal expert assistant that explains Indian laws including HMA, IPC, RTI, etc.
    - Respond in {language}
    - Use clear, plain text without any markdown or special characters
    - Maintain conversation context
    - Structure answers with clear headings and bullet points using normal text
    - Never use asterisks or other formatting symbols
    - Always stay factual and cite relevant sections
    """
    
    full_prompt = f"{system_instruction}\n\nContext: {context}\n\nQuestion: {question}"
    
    response = model.generate_content(full_prompt)
    return sanitize_text(textwrap.fill(response.text, width=80))

@app.route('/', methods=['GET'])
def index():
    if 'history' not in session:
        session['history'] = []
    if 'selected_language' not in session:
        session['selected_language'] = 'en'
    return render_template('index.html',
                         history=session['history'],
                         selected_language=session['selected_language'])

@app.route('/ask', methods=['POST'])
def ask():
    # Rate limiting check
    current_time = time.time()
    last_request = session.get('last_request_time', 0)
    
    if current_time - last_request < app.config['RATE_LIMIT']:
        return jsonify({'error': f'Please wait {app.config["RATE_LIMIT"]} seconds between requests'}), 429

    # Get form data
    question = request.form.get('question', '').strip()
    language = session.get('selected_language', 'en')
    
    if not question:
        return jsonify({'error': 'Please enter a valid question'}), 400

    # Get context and generate response
    context = "\n".join([f"Q: {q}\nA: {a}" for q, a in session['history'][-3:]])
    answer = get_gemini_response(question, context, language)

    # Update session
    session['history'].append((question, answer))
    session['last_request_time'] = current_time
    session.modified = True

    return jsonify({
        'question': question,
        'answer': answer
    })

@app.route('/clear', methods=['POST'])
def clear_history():
    session['history'] = []
    session.modified = True
    return jsonify({'status': 'History cleared'})

@app.route('/set-language', methods=['POST'])
def set_language():
    session['selected_language'] = request.form.get('language', 'en')
    session.modified = True
    return jsonify({'status': 'Language updated'})

if __name__ == '__main__':
    app.run(debug=True)