import os
import re
import sys
import json
import html
import datetime
import time
import email.utils
import xml.etree.ElementTree as ET
import httpx
import requests
from google import genai
from google.genai import errors as genai_errors


def carregar_env():
    """Carrega o .env ao lado do script, sem sobrescrever variáveis já definidas no ambiente"""
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


carregar_env()

HISTORICO_FILE = "historico_bitcoin.json"
FICHEIRO_MEMORIA = "ultimo_preco.txt"
MODELO_GEMINI = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# Horário de Brasília (sem horário de verão desde 2019), independente do fuso do servidor
FUSO_BRT = datetime.timezone(datetime.timedelta(hours=-3))

# Códigos HTTP do Gemini que valem nova tentativa (limite de uso / servidor ocupado)
CODIGOS_TEMPORARIOS = (429, 500, 502, 503, 504)

CABECALHOS = {"User-Agent": "Mozilla/5.0 (bot-previsao-bitcoin)"}

# Fontes RSS da pesquisa da manhã (substituem o Google Search, indisponível no plano gratuito do Gemini 3.x)
FONTES_NOTICIAS = [
    ("Google News", "https://news.google.com/rss/search?q=bitcoin+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("Google News", "https://news.google.com/rss/search?q=(%22Federal+Reserve%22+OR+inflation+OR+%22interest+rates%22+OR+tariffs)+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
]
MAX_NOTICIAS_POR_FONTE = 15

SCHEMA_PREVISAO = {
    "type": "object",
    "properties": {
        "noticias": {"type": "string", "description": "Resumo, em português, das notícias mais relevantes para o BTC"},
        "direcao_prevista": {"type": "string", "enum": ["SUBIR", "CAIR"]},
        "justificativa": {"type": "string", "description": "Porquê, em português"},
    },
    "required": ["noticias", "direcao_prevista", "justificativa"],
}


def agora():
    return datetime.datetime.now(FUSO_BRT)


def pedir(url, tentativas=3):
    """GET com timeout e novas tentativas; devolve a resposta ou None"""
    for tentativa in range(tentativas):
        try:
            response = requests.get(url, headers=CABECALHOS, timeout=20)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"Erro ao aceder {url[:70]} (tentativa {tentativa + 1}/{tentativas}): {e}")
            if tentativa < tentativas - 1:
                time.sleep(10)
    return None


def obter_preco_bitcoin():
    """Procura o preço atual do BTC através da API pública do CoinGecko"""
    response = pedir("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
    try:
        return float(response.json()["bitcoin"]["usd"]) if response else None
    except (ValueError, KeyError) as e:
        print(f"Resposta inesperada do CoinGecko: {e}")
        return None


def obter_mercado():
    """Preço e contexto de mercado (CoinGecko) mais o índice Fear & Greed (alternative.me)"""
    response = pedir("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin&price_change_percentage=24h,7d")
    try:
        d = response.json()[0]
        mercado = {
            "preco": float(d["current_price"]),
            "var_24h": d.get("price_change_percentage_24h_in_currency"),
            "var_7d": d.get("price_change_percentage_7d_in_currency"),
            "max_24h": d.get("high_24h"),
            "min_24h": d.get("low_24h"),
            "volume_24h": d.get("total_volume"),
            "fear_greed": None,
        }
    except (AttributeError, ValueError, KeyError, IndexError, TypeError) as e:
        print(f"Não foi possível obter os dados de mercado: {e}")
        return None

    # O índice é só contexto extra: se falhar, a previsão segue sem ele
    response = pedir("https://api.alternative.me/fng/?limit=1", tentativas=1)
    try:
        fg = response.json()["data"][0]
        mercado["fear_greed"] = f"{fg['value']} ({fg['value_classification']})"
    except (AttributeError, ValueError, KeyError, IndexError) as e:
        print(f"Índice Fear & Greed indisponível: {e}")
    return mercado


def obter_noticias(horas=24):
    """Recolhe as manchetes recentes das FONTES_NOTICIAS; uma fonte que falhe é ignorada"""
    limite = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=horas)
    noticias, vistos = [], set()
    for fonte, url in FONTES_NOTICIAS:
        response = pedir(url, tentativas=2)
        if not response:
            continue
        try:
            raiz = ET.fromstring(response.content)
        except ET.ParseError as e:
            print(f"RSS inválido de {fonte}: {e}")
            continue

        itens = []
        for item in raiz.iter("item"):
            titulo = " ".join((item.findtext("title") or "").split())
            fonte_item = item.findtext("source") or fonte
            if titulo.endswith(f" - {fonte_item}"):
                titulo = titulo[:-len(f" - {fonte_item}")]  # O Google News acrescenta " - Fonte" ao título
            try:
                data = email.utils.parsedate_to_datetime(item.findtext("pubDate") or "")
            except (TypeError, ValueError):
                continue
            if data.tzinfo is None:
                data = data.replace(tzinfo=datetime.timezone.utc)
            data = data.astimezone(datetime.timezone.utc)
            if not titulo or data < limite or titulo.lower() in vistos:
                continue
            vistos.add(titulo.lower())

            resumo = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", item.findtext("description") or "")).split())
            if resumo.lower().startswith(titulo.lower()[:40]):
                resumo = ""  # O Google News repete o título na descrição
            itens.append({
                "fonte": fonte_item,
                "titulo": titulo,
                "resumo": resumo[:250],
                "data": data,
            })

        itens.sort(key=lambda n: n["data"], reverse=True)
        noticias.extend(itens[:MAX_NOTICIAS_POR_FONTE])
    return noticias


def pct(valor):
    return f"{valor:+.2f}%" if isinstance(valor, (int, float)) else "n/d"


def enviar_telegram(mensagem):
    """Envia a mensagem em HTML. Todo o texto variável deve passar por esc() antes."""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não definidos.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"},
            timeout=15,
        )
        if response.status_code != 200:
            print(f"⚠️ ERRO DO TELEGRAM: {response.text}")
            return False
        print("✅ Mensagem entregue ao Telegram com sucesso!")
        return True
    except Exception as e:
        print(f"Erro de conexão com o Telegram: {e}")
        return False


def esc(texto, limite=1500):
    """Corta textos longos da IA (limite do Telegram: 4096) e escapa-os para HTML"""
    texto = str(texto)
    if len(texto) > limite:
        texto = texto[:limite].rstrip() + "…"
    return html.escape(texto, quote=False)


def manipular_historico(acao, dados=None):
    if acao == "ler":
        if os.path.exists(HISTORICO_FILE):
            with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    elif acao == "salvar":
        with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)


def extrair_json(texto):
    """Extrai o objeto JSON da resposta, mesmo que venha com Markdown ou texto à volta"""
    if not texto:
        raise ValueError("Resposta vazia do Gemini")
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio == -1 or fim <= inicio:
        raise ValueError(f"Resposta sem JSON: {texto[:200]}")
    return json.loads(texto[inicio:fim + 1])


def gerar_json(prompt, config, validar, max_tentativas=5):
    """Chama o Gemini com novas tentativas em erros temporários ou respostas inválidas"""
    client = genai.Client()
    for tentativa in range(1, max_tentativas + 1):
        try:
            response = client.models.generate_content(
                model=MODELO_GEMINI,
                contents=prompt,
                config=config,
            )
            dados = extrair_json(response.text)
            validar(dados)
            return dados
        except genai_errors.APIError as e:
            if e.code not in CODIGOS_TEMPORARIOS or tentativa == max_tentativas:
                raise
            espera = 20 * tentativa
            print(f"Gemini indisponível ({e.code}). A aguardar {espera}s... (Tentativa {tentativa}/{max_tentativas})")
            time.sleep(espera)
        except httpx.TransportError as e:
            # Falhas de rede (ligação recusada/cortada, timeout) também são temporárias
            if tentativa == max_tentativas:
                raise
            espera = 20 * tentativa
            print(f"Falha de rede com o Gemini ({type(e).__name__}). A aguardar {espera}s... (Tentativa {tentativa}/{max_tentativas})")
            time.sleep(espera)
        except (ValueError, KeyError) as e:
            # json.JSONDecodeError é subclasse de ValueError
            if tentativa == max_tentativas:
                raise
            print(f"Resposta inválida do Gemini: {e}. A tentar de novo... (Tentativa {tentativa}/{max_tentativas})")
            time.sleep(5)


def estatisticas(historico):
    avaliados = [h for h in historico if h.get("resultado") in ("✅ ACERTOU", "❌ ERROU")]
    acertos = sum(1 for h in avaliados if h["resultado"] == "✅ ACERTOU")
    return acertos, len(avaliados)


# ==========================================
# TAREFA 1: ATUALIZAÇÃO A CADA 2 HORAS
# ==========================================
def relatorio_duas_horas():
    preco_atual = obter_preco_bitcoin()
    if not preco_atual:
        # Uma falha pontual aqui não merece alerta; a próxima execução compara com o último preço guardado
        return

    mensagem_extra = ""
    preco_anterior = None

    # 1. Tenta ler o preço da última notificação
    if os.path.exists(FICHEIRO_MEMORIA):
        try:
            with open(FICHEIRO_MEMORIA, "r") as f:
                preco_anterior = float(f.read().strip())
        except Exception:
            pass

    # 2. Calcula a diferença e a porcentagem se houver um preço anterior
    if preco_anterior:
        diferenca = preco_atual - preco_anterior
        porcentagem = (diferenca / preco_anterior) * 100

        # Formatação de sinais e emojis
        sinal = "+" if diferenca > 0 else ""
        emoji = "🟢" if diferenca > 0 else ("🔴" if diferenca < 0 else "⚪")

        mensagem_extra = f"\n\n{emoji} <b>Variação:</b> {sinal}{porcentagem:.2f}%\n⏮️ <b>Preço anterior:</b> $ {preco_anterior:,.2f}"

    # 3. Guarda o preço atual para ser o "anterior" na próxima vez
    with open(FICHEIRO_MEMORIA, "w") as f:
        f.write(str(preco_atual))

    # 4. Envia a notificação
    hora_atual = agora().strftime('%H:%M')
    msg = f"⏱️ <b>Atualização BTC ({hora_atual} BRT)</b>\n💰 <b>Preço atual:</b> $ {preco_atual:,.2f}{mensagem_extra}"
    enviar_telegram(msg)


# ==========================================
# TAREFA 2: PREVISÃO DA MANHÃ
# ==========================================
def validar_previsao(dados):
    direcao = str(dados["direcao_prevista"]).strip().upper()
    if direcao not in ("SUBIR", "CAIR"):
        raise ValueError(f"direcao_prevista inválida: {dados['direcao_prevista']!r}")
    dados["direcao_prevista"] = direcao
    for campo in ("noticias", "justificativa"):
        if not str(dados.get(campo, "")).strip():
            raise ValueError(f"campo '{campo}' em falta")


def previsao_manha():
    mercado = obter_mercado()
    if not mercado:
        raise RuntimeError("Não foi possível obter os dados de mercado do BTC no CoinGecko")
    preco_atual = mercado["preco"]

    noticias = obter_noticias()
    if not noticias:
        raise RuntimeError("Nenhuma notícia obtida das fontes RSS")

    momento = agora()
    hoje = str(momento.date())
    historico = manipular_historico("ler")

    contexto_aprendizado = ""
    ultima_avaliacao = next((h for h in reversed(historico) if "aprendizado" in h), None)
    if ultima_avaliacao:
        contexto_aprendizado = f"Lição de ontem: {ultima_avaliacao['aprendizado']}"

    def fmt_usd(valor):
        return f"${valor:,.0f}" if isinstance(valor, (int, float)) else "n/d"

    linhas_noticias = "\n".join(
        f"- [{n['data']:%d/%m %H:%M} UTC] {n['titulo']} ({n['fonte']})"
        + (f": {n['resumo']}" if n["resumo"] else "")
        for n in noticias
    )

    prompt = f"""
    Atuas como Analista Sénior de Criptomoedas. Agora: {hoje} {momento:%H:%M} (horário de Brasília).

    DADOS DE MERCADO DO BTC (CoinGecko):
    - Preço atual: ${preco_atual:,.2f}
    - Variação 24h: {pct(mercado['var_24h'])} | Variação 7 dias: {pct(mercado['var_7d'])}
    - Máxima / mínima 24h: {fmt_usd(mercado['max_24h'])} / {fmt_usd(mercado['min_24h'])}
    - Volume 24h: {fmt_usd(mercado['volume_24h'])}
    - Índice Fear & Greed: {mercado['fear_greed'] or 'n/d'}

    {contexto_aprendizado}

    NOTÍCIAS DAS ÚLTIMAS 24H ({len(noticias)} manchetes recolhidas de feeds RSS):
    {linhas_noticias}

    TAREFA: Com base apenas nos dados e notícias acima, prevê se o preço do Bitcoin vai SUBIR ou CAIR
    entre agora e as 22h de hoje (horário de Brasília). Ignora manchetes irrelevantes para o BTC.
    Responde em português, com JSON puro:
    {{
        "noticias": "Resumo das notícias mais relevantes...",
        "direcao_prevista": "SUBIR ou CAIR",
        "justificativa": "Porquê..."
    }}
    """

    config = {"response_mime_type": "application/json", "response_json_schema": SCHEMA_PREVISAO}
    dados = gerar_json(prompt, config, validar_previsao)

    nova_entrada = {
        "data": hoje,
        "hora_previsao": momento.strftime('%H:%M'),
        "preco_8h": preco_atual,
        "direcao": dados["direcao_prevista"]
    }
    # Se a previsão de hoje já existe e ainda não foi avaliada (ex.: execução repetida), substitui-a
    if historico and historico[-1].get("data") == hoje and "resultado" not in historico[-1]:
        historico[-1] = nova_entrada
    else:
        historico.append(nova_entrada)
    manipular_historico("salvar", historico)

    msg = (
        f"🌅 <b>PREVISÃO DIÁRIA BTC ({momento.strftime('%H:%M')})</b>\n"
        f"💰 Preço: ${preco_atual:,.2f}\n"
        f"📊 24h: {pct(mercado['var_24h'])} | 7d: {pct(mercado['var_7d'])} | Fear &amp; Greed: {esc(mercado['fear_greed'] or 'n/d')}\n"
        f"🔮 Previsão: <b>{dados['direcao_prevista']}</b>\n"
        f"🗞️ {len(noticias)} notícias analisadas\n"
        f"📰 Notícias: {esc(dados['noticias'])}\n"
        f"💡 Motivo: {esc(dados['justificativa'])}"
    )
    enviar_telegram(msg)


# ==========================================
# TAREFA 3: VERIFICAÇÃO AO FIM DO DIA
# ==========================================
def validar_aprendizado(dados):
    if not str(dados["aprendizado"]).strip():
        raise ValueError("aprendizado vazio")


def verificacao_noite():
    historico = manipular_historico("ler")
    if not historico:
        print("Histórico vazio: nada para avaliar.")
        return

    hoje = historico[-1]
    if "resultado" in hoje:
        print(f"A previsão de {hoje['data']} já foi avaliada: nada para fazer.")
        return

    # Aceita a previsão de hoje ou de ontem (caso a avaliação corra depois da meia-noite)
    data_limite = agora().date() - datetime.timedelta(days=1)
    if datetime.date.fromisoformat(hoje["data"]) < data_limite:
        raise RuntimeError(f"Não há previsão recente para avaliar (última: {hoje['data']}). A previsão da manhã falhou?")

    preco_atual = obter_preco_bitcoin()
    if not preco_atual:
        raise RuntimeError("Não foi possível obter o preço do BTC no CoinGecko")

    preco_manha = hoje["preco_8h"]
    direcao_prevista = hoje["direcao"]

    if preco_atual > preco_manha:
        resultado_real = "SUBIR"
    elif preco_atual < preco_manha:
        resultado_real = "CAIR"
    else:
        resultado_real = "FICAR ESTÁVEL"

    if resultado_real == "FICAR ESTÁVEL":
        status = "⚪ SEM VARIAÇÃO"
    elif direcao_prevista == resultado_real:
        status = "✅ ACERTOU"
    else:
        status = "❌ ERROU"

    prompt = f"""
    Hoje o BTC estava ${preco_manha:,.2f} no momento da previsão e previste que ia {direcao_prevista}.
    Agora está ${preco_atual:,.2f}. O mercado tendeu a {resultado_real}. Logo, tu {status}.
    TAREFA: Analisa brevemente o teu erro ou acerto para não o repetires.
    Responde em JSON puro:
    {{
        "aprendizado": "O que deves ajustar no teu raciocínio para amanhã..."
    }}
    """

    dados = gerar_json(prompt, {"response_mime_type": "application/json"}, validar_aprendizado)

    hoje["preco_noite"] = preco_atual
    hoje["resultado"] = status
    hoje["aprendizado"] = dados["aprendizado"]
    manipular_historico("salvar", historico)

    variacao = (preco_atual - preco_manha) / preco_manha * 100
    acertos, total = estatisticas(historico)
    placar = f"\n📊 Placar geral: {acertos}/{total} ({acertos / total * 100:.0f}%)" if total else ""

    msg = (
        f"🌙 <b>FECHAMENTO DO DIA BTC</b>\n"
        f"📉 De: ${preco_manha:,.2f} -> Para: ${preco_atual:,.2f} ({variacao:+.2f}%)\n"
        f"🎯 Resultado: {status}{placar}\n"
        f"🧠 Aprendizado guardado para amanhã: {esc(dados['aprendizado'])}"
    )
    enviar_telegram(msg)


# ==========================================
# ROTEADOR DE COMANDOS
# ==========================================
if __name__ == "__main__":
    tarefa = sys.argv[1] if len(sys.argv) > 1 else "preco"
    try:
        if tarefa == "manha":
            previsao_manha()
        elif tarefa == "noite":
            verificacao_noite()
        else:
            relatorio_duas_horas()
    except Exception as e:
        # Avisa no Telegram em vez de falhar em silêncio, e mantém o código de saída de erro
        enviar_telegram(f"⚠️ <b>Falha na tarefa '{esc(tarefa)}'</b>\n{esc(type(e).__name__)}: {esc(e, limite=500)}")
        raise
