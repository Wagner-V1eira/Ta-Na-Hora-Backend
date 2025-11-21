# Tá na Hora - Backend

Sistema de gerenciamento de medicamentos para idosos com assistente de IA.

## 🚀 Configuração

### 1. Clone o repositório
```bash
git clone <seu-repositorio>
cd backend
```

### 2. Crie um ambiente virtual
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
# ou
source .venv/bin/activate   # Linux/Mac
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
Copie o arquivo `.env.example` para `.env`:
```bash
copy .env.example .env  # Windows
# ou
cp .env.example .env    # Linux/Mac
```

Edite o arquivo `.env` e adicione sua chave da API do Google Gemini:
```
GEMINI_API_KEY=sua_chave_api_aqui
```

**Como obter a chave da API:**
1. Acesse: https://aistudio.google.com/app/apikey
2. Crie uma nova chave API
3. Cole no arquivo `.env`

### 5. Execute o servidor
```bash
python app.py
```

O servidor estará rodando em: `http://localhost:5000`

## 📦 Funcionalidades

- ✅ Cadastro de medicamentos com dosagem e período
- ✅ Dicas personalizadas geradas por IA (Gemini)
- ✅ Registro de doses tomadas
- ✅ Histórico de medicamentos
- ✅ Persistência em banco de dados SQLite

## 🔒 Segurança

- As chaves de API são armazenadas em variáveis de ambiente
- O arquivo `.env` está no `.gitignore` e **nunca** deve ser commitado
- Use `.env.example` como modelo para outros desenvolvedores

## 📚 API Endpoints

- `POST /api/medicamentos` - Adicionar medicamento
- `GET /api/medicamentos` - Listar medicamentos
- `DELETE /api/medicamentos/<id>` - Excluir medicamento
- `GET /api/historico` - Listar histórico
- `POST /api/registro` - Registrar dose tomada

## 🛠️ Tecnologias

- Flask
- SQLite
- Google Gemini AI
- Agno (framework de agentes)
