# PI-6 — IA SQL BD

Sistema de consulta a banco de dados em linguagem natural usando IA local via Ollama.

## 🛠️ Pré-requisitos

- [Python 3.11.6](https://www.python.org/downloads/release/python-3116/)
- [Ollama](https://ollama.com/download)

## 🤖 Modelos necessários

Com o Ollama instalado, baixe os dois modelos:

```bash
ollama pull prem-research/prem-1b-sql-fp16
ollama pull llama3.2
```

## ⚙️ Instalação

**1. Clone o repositório ou copie a pasta do projeto**

**2. Crie o ambiente virtual**
```bash
py -3.11 -m venv .venv
```

**3. Ative o ambiente virtual**
```bash
.venv\Scripts\activate
```

**4. Atualize o pip**
```bash
pip install --upgrade pip
```

**5. Instale as dependências**
```bash
pip install -r requirements.txt
```

## ▶️ Como usar

Com o ambiente virtual ativado, execute:

```bash
python IA.py
```
