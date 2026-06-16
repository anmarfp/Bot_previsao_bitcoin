import os
import sys
import json
import datetime
import requests
from google import genai

client_gemini = genai.Client()
HISTORICO_FILE = "historico_bitcoin.json"

def obter_preco_bitcoin():
    """Procura o preço atual do BTC através da API pública do CoinGecko (compatível com GitHub Actions)"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        response = requests.get(url)
        return float(response.json()["bitcoin"]["usd"])
    except Exception as e:
        print(f"Erro na API de preço: {e}")
        return None

def enviar_telegram(mensagem):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        # Removemos o parse_mode para o Telegram não bloquear caracteres especiais gerados pela IA
        response = requests.post(url, json={"chat_id": chat_id, "text": mensagem})
        
        # Força o Python a mostrar-nos se o Telegram rejeitou a entrega
        if response.status_code != 200:
            print(f"⚠️ ERRO DO TELEGRAM: {response.text}")
        else:
            print("✅ Mensagem entregue ao Telegram com sucesso!")
    except Exception as e:
        print(f"Erro de conexão com o Telegram: {e}")

def manipular_historico(acao, dados=None):
    if acao == "ler":
        if os.path.exists(HISTORICO_FILE):
            with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    elif acao == "salvar":
        with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)

# ==========================================
# TAREFA 1: ATUALIZAÇÃO A CADA 2 HORAS
# ==========================================
def relatorio_duas_horas():
    preco = obter_preco_bitcoin()
    if preco:
        hora_atual = datetime.datetime.now().strftime('%H:%M')
        msg = f"⏱️ *Atualização BTC ({hora_atual})*\nO preço atual do Bitcoin na Binance é: *$ {preco:,.2f}*"
        enviar_telegram(msg)

# ==========================================
# TAREFA 2: PREVISÃO ÀS 8H DA MANHÃ
# ==========================================
def previsao_manha():
    preco_atual = obter_preco_bitcoin()
    historico = manipular_historico("ler")
    
    contexto_aprendizado = ""
    if historico and "aprendizado" in historico[-1]:
        contexto_aprendizado = f"Lição de ontem: {historico[-1]['aprendizado']}"

    prompt = f"""
    Atuas como Analista Sénior de Criptomoedas. Data: {datetime.date.today()}. Preço BTC: ${preco_atual:,.2f}.
    {contexto_aprendizado}
    TAREFA: Analisa as notícias políticas/económicas das últimas 24h e prevê se o Bitcoin vai SUBIR ou CAIR hoje.
    Responde em JSON puro:
    {{
        "noticias": "Resumo...",
        "direcao_prevista": "SUBIR ou CAIR",
        "justificativa": "Porquê..."
    }}
    """
    
    response = client_gemini.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={
            "tools": [{"google_search": {}}]
        }
    )
    
    # Limpeza do texto caso o Gemini adicione aspas ou blocos de código Markdown
    texto_resposta = response.text.replace("```json", "").replace("```", "").strip()
    dados = json.loads(texto_resposta)
    
    # Salva a previsão de hoje
    nova_entrada = {
        "data": str(datetime.date.today()),
        "preco_8h": preco_atual,
        "direcao": dados["direcao_prevista"]
    }
    historico.append(nova_entrada)
    manipular_historico("salvar", historico)
    
    msg = f"🌅 *PREVISÃO DIÁRIA BTC (08:00)*\n💰 Preço: ${preco_atual:,.2f}\n🔮 Previsão: **{dados['direcao_prevista']}**\n📰 Notícias: {dados['noticias']}\n💡 Motivo: {dados['justificativa']}"
    enviar_telegram(msg)

# ==========================================
# TAREFA 3: VERIFICAÇÃO AO FIM DO DIA
# ==========================================
def verificacao_noite():
    preco_atual = obter_preco_bitcoin()
    historico = manipular_historico("ler")
    
    if not historico:
        return
    
    hoje = historico[-1]
    preco_manha = hoje["preco_8h"]
    direcao_prevista = hoje["direcao"]
    
    subiu = preco_atual > preco_manha
    resultado_real = "SUBIR" if subiu else "CAIR"
    acertou = direcao_prevista == resultado_real
    status = "✅ ACERTOU" if acertou else "❌ ERROU"
    
    prompt = f"""
    Hoje às 8h o BTC estava ${preco_manha:,.2f} e previste que ia {direcao_prevista}.
    Agora está ${preco_atual:,.2f}. O mercado tendeu a {resultado_real}. Logo, tu {status}.
    TAREFA: Analisa brevemente o teu erro ou acerto para não o repetires.
    Responde em JSON puro:
    {{
        "aprendizado": "O que deves ajustar no teu raciocínio para amanhã..."
    }}
    """
    
    response = client_gemini.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={"response_mime_type": "application/json"}
    )
    
    dados = json.loads(response.text)
    hoje["preco_noite"] = preco_atual
    hoje["resultado"] = status
    hoje["aprendizado"] = dados["aprendizado"]
    manipular_historico("salvar", historico)
    
    msg = f"🌙 *FECHAMENTO DO DIA BTC*\n📉 De: ${preco_manha:,.2f} -> Para: ${preco_atual:,.2f}\n🎯 Resultado: {status}\n🧠 Aprendizado guardado para amanhã: {dados['aprendizado']}"
    enviar_telegram(msg)

# ==========================================
# ROTEADOR DE COMANDOS
# ==========================================
if __name__ == "__main__":
    tarefa = sys.argv[1] if len(sys.argv) > 1 else "preco"
    if tarefa == "manha":
        previsao_manha()
    elif tarefa == "noite":
        verificacao_noite()
    else:
        relatorio_duas_horas()
