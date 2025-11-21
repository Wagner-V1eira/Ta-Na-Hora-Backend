from flask import Flask, request, jsonify
from flask_cors import CORS
from agno.agent import Agent
from agno.models.google import Gemini
import os
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

CHAVE_API_GEM = os.getenv('GEMINI_API_KEY')
DB_PATH = "medicamentos.db"

if not CHAVE_API_GEM:
    raise ValueError("❌ GEMINI_API_KEY não encontrada! Crie um arquivo .env com sua chave.")

def init_db():
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            dosagem TEXT NOT NULL,
            dias INTEGER NOT NULL,
            dataInicio TEXT NOT NULL,
            conselho_ia TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_med INTEGER NOT NULL,
            data TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(id_med, data)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✓ Banco de dados inicializado")

def obter_agente_medicamento():
    return Agent(
        model=Gemini(id="gemini-2.5-flash-lite", api_key=CHAVE_API_GEM),
        description="Assistente especializado em saúde geriátrica e gestão de medicamentos.",
        instructions=[
            "Você é um assistente médico especializado em orientações para idosos.",
            "NUNCA repita a mesma dica genérica para medicamentos diferentes.",
            "Para CADA medicamento, dê uma orientação ESPECÍFICA baseada em:",
            "- Interações com alimentos (ex: tomar antes/depois de comer, evitar leite/álcool)",
            "- Horário ideal (manhã/noite, jejum)",
            "- Efeitos colaterais comuns do medicamento específico",
            "- Cuidados especiais (tomar com água, não mastigar, protetor solar, etc.)",
            "Seja breve (máximo 2 frases), direto, gentil e em português.",
            "Use o NOME DO MEDICAMENTO na resposta para personalizar.",
            "NUNCA use formatação markdown."
        ],
        markdown=False
    )

@app.route('/api/medicamentos', methods=['POST'])
def adicionar_medicamento():
    dados = request.json
    
    conselho_ia = "Lembre-se de tomar com água."

    try:
        nome_med = dados.get('nome')
        dosagem = dados.get('dosagem')
        print(f"Consultando Gemini para: {nome_med} ({dosagem})...")
        
        agente = obter_agente_medicamento()
        
        prompt = f"""Medicamento: {nome_med}
Dosagem: {dosagem}

Dê uma orientação ESPECÍFICA e PERSONALIZADA para este medicamento. 
Foque em informações únicas deste remédio (horário, alimentos, efeitos).
Não use dicas genéricas que servem para qualquer remédio."""
        
        resposta_ia = agente.run(prompt)
        conselho_ia = resposta_ia.content.strip()
        print(f"Gemini respondeu: {conselho_ia}")
    except Exception as e:
        print(f"Aviso: Não foi possível consultar a IA, usando padrão. Erro: {e}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO medicamentos (nome, dosagem, dias, dataInicio, conselho_ia)
        VALUES (?, ?, ?, ?, ?)
    ''', (dados.get('nome'), dados.get('dosagem'), int(dados.get('dias', 0)), 
          dados.get('dataInicio'), conselho_ia))
    
    conn.commit()
    id_novo = cursor.lastrowid
    conn.close()
    
    novo_medicamento = {
        "id": id_novo,
        "nome": dados.get('nome'),
        "dosagem": dados.get('dosagem'),
        "dias": int(dados.get('dias', 0)),
        "dataInicio": dados.get('dataInicio'),
        "conselho_ia": conselho_ia
    }
    
    print(f"✓ Medicamento salvo no banco: {novo_medicamento}")
    return jsonify(novo_medicamento), 201

@app.route('/api/medicamentos', methods=['GET'])
def listar_medicamentos():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM medicamentos')
    medicamentos = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(medicamentos)

@app.route('/api/medicamentos/<int:id_med>', methods=['DELETE'])
def excluir_medicamento(id_med):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM medicamentos WHERE id = ?', (id_med,))
    cursor.execute('DELETE FROM registros WHERE id_med = ?', (id_med,))
    
    conn.commit()
    conn.close()
    
    print(f"✓ Medicamento {id_med} excluído do banco.")
    return jsonify({"sucesso": True})

@app.route('/api/historico', methods=['GET'])
def listar_historico():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM medicamentos')
    medicamentos = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(medicamentos)

@app.route('/api/registro', methods=['POST'])
def registrar_dose():
    dados = request.json
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO registros (id_med, data, status)
        VALUES (?, ?, ?)
    ''', (dados['id_med'], dados['data'], dados['status']))
    
    conn.commit()
    conn.close()
    
    print(f"✓ Registro salvo: Med {dados['id_med']} em {dados['data']} - {dados['status']}")
    return jsonify({"sucesso": True, "status": "verde"})

if __name__ == '__main__':
    init_db()
    print("Servidor rodando na porta 5000...")
    app.run(debug=True, port=5000)