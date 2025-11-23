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
            conselho_ia TEXT,
            intervaloHoras INTEGER DEFAULT 12,
            horarioInicio TEXT,
            horarioFim TEXT,
            alertaSonoro INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_med INTEGER NOT NULL,
            data TEXT NOT NULL,
            horario TEXT NOT NULL,
            status TEXT NOT NULL,
            dataHoraTomada TEXT,
            UNIQUE(id_med, data, horario)
        )
    ''')
    
    try:
        cursor.execute("SELECT intervaloHoras FROM medicamentos LIMIT 1")
    except sqlite3.OperationalError:
        print("⚙️ Migrando banco de dados...")
        cursor.execute("ALTER TABLE medicamentos ADD COLUMN intervaloHoras INTEGER DEFAULT 12")
        cursor.execute("ALTER TABLE medicamentos ADD COLUMN horarioInicio TEXT")
        cursor.execute("ALTER TABLE medicamentos ADD COLUMN horarioFim TEXT")
        cursor.execute("ALTER TABLE medicamentos ADD COLUMN alertaSonoro INTEGER DEFAULT 1")
        print("✓ Novos campos adicionados")
    
    try:
        cursor.execute("SELECT horario FROM registros LIMIT 1")
    except sqlite3.OperationalError:
        print("⚙️ Migrando tabela registros...")
        cursor.execute("ALTER TABLE registros ADD COLUMN horario TEXT DEFAULT ''")
        cursor.execute("ALTER TABLE registros ADD COLUMN dataHoraTomada TEXT")
        print("✓ Tabela registros atualizada")
    
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
        INSERT INTO medicamentos (nome, dosagem, dias, dataInicio, conselho_ia, 
                                   intervaloHoras, horarioInicio, horarioFim, alertaSonoro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (dados.get('nome'), 
          dados.get('dosagem'), 
          int(dados.get('dias', 0)), 
          dados.get('dataInicio'), 
          conselho_ia,
          int(dados.get('intervaloHoras', 12)),
          dados.get('horarioInicio'),
          dados.get('horarioFim'),
          int(dados.get('alertaSonoro', 1))))
    
    conn.commit()
    id_novo = cursor.lastrowid
    conn.close()
    
    novo_medicamento = {
        "id": id_novo,
        "nome": dados.get('nome'),
        "dosagem": dados.get('dosagem'),
        "dias": int(dados.get('dias', 0)),
        "dataInicio": dados.get('dataInicio'),
        "conselho_ia": conselho_ia,
        "intervaloHoras": int(dados.get('intervaloHoras', 12)),
        "horarioInicio": dados.get('horarioInicio'),
        "horarioFim": dados.get('horarioFim'),
        "alertaSonoro": int(dados.get('alertaSonoro', 1))
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
    
    data_hora_atual = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT OR REPLACE INTO registros (id_med, data, horario, status, dataHoraTomada)
        VALUES (?, ?, ?, ?, ?)
    ''', (dados['id_med'], dados['data'], dados.get('horario', ''), 
          dados['status'], data_hora_atual))
    
    conn.commit()
    conn.close()
    
    print(f"✓ Registro salvo: Med {dados['id_med']} em {dados['data']} {dados.get('horario', '')} - {dados['status']}")
    return jsonify({"sucesso": True, "status": "verde", "dataHoraTomada": data_hora_atual})

@app.route('/api/alertas', methods=['GET'])
def verificar_alertas():
    """Retorna alertas pendentes que devem tocar agora"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    agora = datetime.now()
    data_hoje = agora.strftime('%Y-%m-%d')
    hora_atual = agora.strftime('%H:%M')
    
    cursor.execute('''
        SELECT m.*, 
               COALESCE(r.status, 'pendente') as status_dose,
               r.dataHoraTomada
        FROM medicamentos m
        LEFT JOIN registros r ON m.id = r.id_med AND r.data = ?
        WHERE m.alertaSonoro = 1
    ''', (data_hoje,))
    
    medicamentos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    alertas_ativos = []
    
    for med in medicamentos:
        if med['status_dose'] == 'tomado':
            continue
            
        if med['horarioInicio'] and med['horarioFim']:
            if med['horarioInicio'] <= hora_atual <= med['horarioFim']:
                hora_inicio_dt = datetime.strptime(med['horarioInicio'], '%H:%M')
                diferenca_minutos = (agora.hour * 60 + agora.minute) - (hora_inicio_dt.hour * 60 + hora_inicio_dt.minute)
                
                if diferenca_minutos >= 0 and diferenca_minutos % 15 == 0 and diferenca_minutos <= 60:
                    alertas_ativos.append({
                        'id': med['id'],
                        'nome': med['nome'],
                        'dosagem': med['dosagem'],
                        'horarioInicio': med['horarioInicio'],
                        'horarioFim': med['horarioFim'],
                        'numeroAlerta': (diferenca_minutos // 15) + 1,
                        'totalAlertas': 5
                    })
    
    return jsonify(alertas_ativos)

@app.route('/api/proximos-horarios/<int:id_med>', methods=['GET'])
def obter_proximos_horarios(id_med):
    """Retorna os próximos horários de tomar o medicamento"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM medicamentos WHERE id = ?', (id_med,))
    med = cursor.fetchone()
    conn.close()
    
    if not med:
        return jsonify({"erro": "Medicamento não encontrado"}), 404
    
    horarios = []
    data_inicio = datetime.fromisoformat(med['dataInicio'].replace('Z', '+00:00'))
    intervalo = med['intervaloHoras']
    
    for dia in range(med['dias']):
        data_dose = data_inicio + timedelta(days=dia)
        
        doses_por_dia = 24 // intervalo
        
        for dose in range(doses_por_dia):
            horario_dose = data_dose + timedelta(hours=intervalo * dose)
            horarios.append({
                'data': horario_dose.strftime('%Y-%m-%d'),
                'horario': horario_dose.strftime('%H:%M'),
                'timestamp': horario_dose.isoformat()
            })
    
    return jsonify(horarios[:20])  

if __name__ == '__main__':
    init_db()
    print("Servidor rodando na porta 5000...")
    app.run(debug=True, port=5000)