import os
import re
import sys
import json
import html
import datetime
import time
import math
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
FAIXA_NEUTRA = 0.003

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
        "probabilidade_subir": {"type": "integer", "description": "Probabilidade do preço subir (0 a 100). >50 implica SUBIR, <50 implica CAIR."},
        "justificativa": {"type": "string", "description": "Porquê, em português"},
    },
    "required": ["noticias", "direcao_prevista", "probabilidade_subir", "justificativa"],
}


def classificar_movimento(preco_inicio, preco_fim):
    """Classifica o movimento de preço como SUBIR, CAIR ou FICAR ESTÁVEL, respeitando a faixa neutra."""
    if preco_inicio == 0:
        return "FICAR ESTÁVEL"
    var = (preco_fim - preco_inicio) / preco_inicio
    if round(abs(var), 10) < FAIXA_NEUTRA:
        return "FICAR ESTÁVEL"
    elif var > 0:
        return "SUBIR"
    else:
        return "CAIR"


def agregar_amostras(amostras):
    """Calcula a média, resolve empates e define a convicção a partir de múltiplas chamadas ao modelo."""
    if not amostras:
        raise ValueError("Nenhuma amostra para agregar")
    
    media = sum(a["probabilidade_subir"] for a in amostras) / len(amostras)
    
    if media > 50:
        direcao = "SUBIR"
    elif media < 50:
        direcao = "CAIR"
    else:
        contagem = {"SUBIR": 0, "CAIR": 0}
        for a in amostras:
            contagem[a["direcao_prevista"]] += 1
        if contagem["SUBIR"] > contagem["CAIR"]:
            direcao = "SUBIR"
        elif contagem["CAIR"] > contagem["SUBIR"]:
            direcao = "CAIR"
        else:
            direcao = amostras[0]["direcao_prevista"]
            
    probabilidade_subir = round(media)
    sem_conviccao = 45 <= probabilidade_subir <= 55
    
    amostra_vencedora = next((a for a in amostras if a["direcao_prevista"] == direcao), amostras[0])
    
    return {
        "probabilidade_subir": probabilidade_subir,
        "direcao": direcao,
        "sem_conviccao": sem_conviccao,
        "noticias": amostra_vencedora["noticias"],
        "justificativa": amostra_vencedora["justificativa"]
    }


def calcular_indicadores(fechos):
    """Calcula retornos, RSI e volatilidade a partir das velas horárias sem depender de bibliotecas externas."""
    ind = {
        "ret_1h": None, "ret_4h": None, "ret_8h": None, "ret_24h": None, "ret_72h": None,
        "rsi_14": None, "vol_24h": None, "pos_faixa_24h": None
    }
    if not fechos:
        return ind
        
    ultimo = fechos[-1]
    
    def calc_ret(n):
        if len(fechos) > n:
            return (ultimo - fechos[-(n+1)]) / fechos[-(n+1)] * 100
        return None
        
    ind["ret_1h"] = calc_ret(1)
    ind["ret_4h"] = calc_ret(4)
    ind["ret_8h"] = calc_ret(8)
    ind["ret_24h"] = calc_ret(24)
    ind["ret_72h"] = calc_ret(72)
    
    if len(fechos) > 14:
        gains = 0.0
        losses = 0.0
        for i in range(1, 15):
            change = fechos[i] - fechos[i-1]
            if change > 0: gains += change
            else: losses -= change
        avg_gain = gains / 14
        avg_loss = losses / 14
        
        for i in range(15, len(fechos)):
            change = fechos[i] - fechos[i-1]
            gain = change if change > 0 else 0.0
            loss = -change if change < 0 else 0.0
            avg_gain = (avg_gain * 13 + gain) / 14
            avg_loss = (avg_loss * 13 + loss) / 14
            
        if avg_loss == 0:
            ind["rsi_14"] = 100.0
        else:
            rs = avg_gain / avg_loss
            ind["rsi_14"] = 100.0 - (100.0 / (1.0 + rs))
            
    if len(fechos) >= 25:
        rets = []
        for i in range(len(fechos)-24, len(fechos)):
            rets.append((fechos[i] - fechos[i-1]) / fechos[i-1] * 100)
        mean_ret = sum(rets) / len(rets)
        var = sum((r - mean_ret)**2 for r in rets) / len(rets)
        ind["vol_24h"] = math.sqrt(var)
        
        ultimos_24 = fechos[-24:]
        min_24 = min(ultimos_24)
        max_24 = max(ultimos_24)
        if max_24 > min_24:
            ind["pos_faixa_24h"] = (ultimo - min_24) / (max_24 - min_24) * 100
        else:
            ind["pos_faixa_24h"] = 50.0
            
    return ind


def calcular_baselines(indicadores):
    """Gera previsões simples de referência (sempre subir e momentum de 8h) baseadas nos indicadores."""
    bases = {"sempre_subir": "SUBIR", "momentum_8h": None}
    r8 = indicadores.get("ret_8h")
    if r8 is not None and r8 != 0:
        bases["momentum_8h"] = "SUBIR" if r8 > 0 else "CAIR"
    return bases


def obter_velas():
    """Obtém os últimos 100 preços de fecho horário do Bitcoin na Binance."""
    resp = pedir("https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=101")
    if resp:
        try:
            fechos = []
            now_ms = time.time() * 1000
            for vela in resp.json():
                close_time = int(vela[6])
                if close_time < now_ms:
                    fechos.append(float(vela[4]))
            return fechos[-100:] if fechos else []
        except (ValueError, TypeError, KeyError, IndexError) as e:
            print(f"Erro ao processar velas: {e}")
    return []


def obter_derivativos():
    """Obtém o funding rate, a variação de open interest e o rácio long/short da Binance Futures."""
    deriv = {"funding": None, "oi_var_24h": None, "ls_ratio": None}
    
    resp = pedir("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT", tentativas=1)
    if resp:
        try:
            deriv["funding"] = float(resp.json()["lastFundingRate"]) * 100
        except (ValueError, KeyError, TypeError) as e:
            print(f"Erro no funding rate: {e}")
        
    resp = pedir("https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=1h&limit=25", tentativas=1)
    if resp:
        try:
            data = resp.json()
            if len(data) >= 2:
                first = float(data[0]["sumOpenInterest"])
                last = float(data[-1]["sumOpenInterest"])
                if first > 0:
                    deriv["oi_var_24h"] = (last - first) / first * 100
        except (ValueError, KeyError, TypeError, IndexError) as e:
            print(f"Erro no open interest: {e}")
        
    resp = pedir("https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1h&limit=1", tentativas=1)
    if resp:
        try:
            deriv["ls_ratio"] = float(resp.json()[0]["longShortRatio"])
        except (ValueError, KeyError, TypeError, IndexError) as e:
            print(f"Erro no long/short ratio: {e}")
        
    return deriv


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
        raise ValueError(f"direcao_prevista inválida: {dados.get('direcao_prevista')!r}")
    dados["direcao_prevista"] = direcao
    
    prob_val = dados.get("probabilidade_subir")
    if isinstance(prob_val, bool) or not isinstance(prob_val, (int, float)):
        raise ValueError(f"probabilidade_subir inválida: {prob_val}")
    if math.isinf(prob_val) or math.isnan(prob_val) or prob_val != int(prob_val):
        raise ValueError(f"probabilidade_subir inválida: {prob_val}")
    prob = int(prob_val)
        
    if not (0 <= prob <= 100):
        raise ValueError(f"probabilidade_subir fora de 0-100: {prob}")
        
    if prob > 50 and direcao != "SUBIR":
        raise ValueError("probabilidade_subir > 50 exige direcao_prevista SUBIR")
    if prob < 50 and direcao != "CAIR":
        raise ValueError("probabilidade_subir < 50 exige direcao_prevista CAIR")
        
    dados["probabilidade_subir"] = prob

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

    fechos = obter_velas()
    indicadores = calcular_indicadores(fechos)
    derivativos = obter_derivativos()

    momento = agora()
    hoje = str(momento.date())
    historico = manipular_historico("ler")

    contexto_aprendizado = ""
    ultima_avaliacao = next((h for h in reversed(historico) if "aprendizado" in h), None)
    if ultima_avaliacao:
        contexto_aprendizado = f"Lição de ontem: {ultima_avaliacao['aprendizado']}"

    def fmt_usd(valor):
        return f"${valor:,.0f}" if isinstance(valor, (int, float)) else "n/d"
        
    def fmt_pct_ind(val, prec=2, sinal=True):
        return f"{val:{'+' if sinal else ''}.{prec}f}%" if val is not None else "n/d"
        
    def fmt_val_ind(val, prec=2):
        return f"{val:.{prec}f}" if val is not None else "n/d"

    linhas_noticias = "\n".join(
        f"- [{n['data']:%d/%m %H:%M} UTC] {n['titulo']} ({n['fonte']})"
        + (f": {n['resumo']}" if n["resumo"] else "")
        for n in noticias
    )
    
    avaliados = [h for h in historico if "resultado" in h]
    linhas_historico = []
    for h in avaliados[-10:]:
        data_h = h.get("data", "n/d")
        dir_h = h.get("direcao", "n/d")
        prob_h = f"{h['probabilidade_subir']}%" if "probabilidade_subir" in h else "n/d"
        if "variacao_pct" in h:
            var_real = f"{h['variacao_pct']:+.2f}%"
        elif "preco_8h" in h and "preco_noite" in h:
            var = (h["preco_noite"] - h["preco_8h"]) / h["preco_8h"] * 100
            var_real = f"{var:+.2f}%"
        else:
            var_real = "n/d"
        res_h = h.get("resultado", "n/d")
        linhas_historico.append(f"{data_h}: {dir_h} (prob. subir {prob_h}), var: {var_real}, res: {res_h}")
    texto_historico = "\n".join(linhas_historico) if linhas_historico else "Sem histórico recente avaliado."

    texto_indicadores = (
        f"- Retornos: 1h: {fmt_pct_ind(indicadores['ret_1h'])} | 4h: {fmt_pct_ind(indicadores['ret_4h'])} | "
        f"8h: {fmt_pct_ind(indicadores['ret_8h'])} | 24h: {fmt_pct_ind(indicadores['ret_24h'])} | 72h: {fmt_pct_ind(indicadores['ret_72h'])}\n"
        f"- RSI(14): {fmt_val_ind(indicadores['rsi_14'])} | Volatilidade 24h: {fmt_pct_ind(indicadores['vol_24h'], sinal=False)} | "
        f"Posição na Faixa 24h: {fmt_val_ind(indicadores['pos_faixa_24h'])}/100"
    )
    
    texto_derivativos = (
        f"- Funding Rate: {fmt_pct_ind(derivativos['funding'], 4)}\n"
        f"- Variação Open Interest (24h): {fmt_pct_ind(derivativos['oi_var_24h'])}\n"
        f"- Long/Short Ratio: {fmt_val_ind(derivativos['ls_ratio'])}"
    )

    prompt = f"""
    Atuas como Analista Sénior de Criptomoedas. Agora: {hoje} {momento:%H:%M} (horário de Brasília).

    DADOS DE MERCADO DO BTC (CoinGecko):
    - Preço atual: ${preco_atual:,.2f}
    - Variação 24h: {pct(mercado['var_24h'])} | Variação 7 dias: {pct(mercado['var_7d'])}
    - Máxima / mínima 24h: {fmt_usd(mercado['max_24h'])} / {fmt_usd(mercado['min_24h'])}
    - Volume 24h: {fmt_usd(mercado['volume_24h'])}
    - Índice Fear & Greed: {mercado['fear_greed'] or 'n/d'}
    
    INDICADORES TÉCNICOS (Binance):
    {texto_indicadores}
    
    DERIVATIVOS (Binance Futures):
    {texto_derivativos}

    HISTÓRICO RECENTE DAS TUAS PREVISÕES:
    {texto_historico}

    {contexto_aprendizado}

    NOTÍCIAS DAS ÚLTIMAS 24H ({len(noticias)} manchetes recolhidas de feeds RSS):
    {linhas_noticias}

    TAREFA: Com base apenas nos dados e notícias acima, prevê se o preço do Bitcoin vai SUBIR ou CAIR
    entre agora e as 22h de hoje (horário de Brasília). Ignora manchetes irrelevantes para o BTC.
    A `probabilidade_subir` é a probabilidade calibrada de o preço às 22h estar ACIMA do atual; 50 significa nenhuma vantagem; valores longe de 50 só com evidência forte, porque o BTC nesse horizonte é quase aleatório.
    Responde em português, com JSON puro:
    {{
        "noticias": "Resumo das notícias mais relevantes...",
        "direcao_prevista": "SUBIR ou CAIR",
        "probabilidade_subir": "inteiro de 0 a 100",
        "justificativa": "Porquê..."
    }}
    """

    config = {"response_mime_type": "application/json", "response_json_schema": SCHEMA_PREVISAO}
    
    amostras = []
    ultima_excecao = None
    for i in range(3):
        try:
            dados = gerar_json(prompt, config, validar_previsao)
            amostras.append(dados)
        except Exception as e:
            print(f"Falha na amostra {i+1}: {e}")
            ultima_excecao = e
            
    if not amostras:
        if ultima_excecao:
            raise ultima_excecao
        raise RuntimeError("Nenhuma amostra válida foi gerada")
        
    resultado_agregado = agregar_amostras(amostras)
    baselines = calcular_baselines(indicadores)

    nova_entrada = {
        "data": hoje,
        "hora_previsao": momento.strftime('%H:%M'),
        "preco_8h": preco_atual,
        "direcao": resultado_agregado["direcao"],
        "probabilidade_subir": resultado_agregado["probabilidade_subir"],
        "sem_conviccao": resultado_agregado["sem_conviccao"],
        "justificativa": resultado_agregado["justificativa"],
        "baselines": baselines,
        "indicadores": {k: round(v, 2) if v is not None else None for k, v in indicadores.items()}
    }
    
    # Se a previsão de hoje já existe e ainda não foi avaliada (ex.: execução repetida), substitui-a
    if historico and historico[-1].get("data") == hoje and "resultado" not in historico[-1]:
        historico[-1] = nova_entrada
    else:
        historico.append(nova_entrada)
    manipular_historico("salvar", historico)
    
    prob_p = resultado_agregado["probabilidade_subir"]
    if resultado_agregado["direcao"] == "CAIR":
        prob_p = 100 - prob_p
    
    aviso_conviccao = " ⚠️ <b>sem convicção</b>" if resultado_agregado["sem_conviccao"] else ""

    msg = (
        f"🌅 <b>PREVISÃO DIÁRIA BTC ({momento.strftime('%H:%M')})</b>\n"
        f"💰 Preço: ${preco_atual:,.2f}\n"
        f"📊 24h: {pct(mercado['var_24h'])} | 7d: {pct(mercado['var_7d'])} | Fear &amp; Greed: {esc(mercado['fear_greed'] or 'n/d')}\n"
        f"🔮 Previsão: <b>{resultado_agregado['direcao']}</b> ({prob_p}% de probabilidade){aviso_conviccao}\n"
        f"🗞️ {len(noticias)} notícias analisadas\n"
        f"📰 Notícias: {esc(resultado_agregado['noticias'])}\n"
        f"💡 Motivo: {esc(resultado_agregado['justificativa'])}"
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

    resultado_real = classificar_movimento(preco_manha, preco_atual)

    if resultado_real == "FICAR ESTÁVEL":
        status = "⚪ SEM VARIAÇÃO"
    elif direcao_prevista == resultado_real:
        status = "✅ ACERTOU"
    else:
        status = "❌ ERROU"

    variacao_pct = round((preco_atual - preco_manha) / preco_manha * 100, 2)
    hoje["variacao_pct"] = variacao_pct

    # Brier Score
    brier = None
    if "probabilidade_subir" in hoje and resultado_real != "FICAR ESTÁVEL":
        prob = hoje["probabilidade_subir"] / 100.0
        y = 1.0 if resultado_real == "SUBIR" else 0.0
        brier = (prob - y) ** 2
        hoje["brier"] = round(brier, 4)

    # Baselines
    resultados_baselines = {}
    if "baselines" in hoje:
        for nome, direcao_base in hoje["baselines"].items():
            if direcao_base is not None:
                if resultado_real == "FICAR ESTÁVEL":
                    res_base = "⚪ SEM VARIAÇÃO"
                elif direcao_base == resultado_real:
                    res_base = "✅ ACERTOU"
                else:
                    res_base = "❌ ERROU"
                resultados_baselines[nome] = res_base
        hoje["resultados_baselines"] = resultados_baselines

    prompt = f"""
    Hoje o BTC estava ${preco_manha:,.2f} no momento da previsão e previste que ia {direcao_prevista}.
    """
    if "probabilidade_subir" in hoje:
        prompt += f"A tua probabilidade de subir foi de {hoje['probabilidade_subir']}%. "
    if "justificativa" in hoje:
        prompt += f"A tua justificativa foi: '{hoje['justificativa']}'. "

    prompt += f"""
    Agora está ${preco_atual:,.2f} (variação real de {variacao_pct:+.2f}%). O mercado tendeu a {resultado_real}.
    Logo, tu {status}.
    TAREFA: Analisa brevemente o teu raciocínio inicial face à variação real para melhorares amanhã.
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

    avaliados = [h for h in historico if h.get("resultado") in ("✅ ACERTOU", "❌ ERROU")]
    acertos, total = estatisticas(historico)
    placar = f"\n📊 Placar Gemini: {acertos}/{total} ({acertos / total * 100:.0f}%)" if total else ""
    
    mesmos_dias = [h for h in avaliados if "resultados_baselines" in h]
    if mesmos_dias:
        gemini_acertos = sum(1 for h in mesmos_dias if h["resultado"] == "✅ ACERTOU")
        gemini_total = len(mesmos_dias)
        
        briers = [h["brier"] for h in mesmos_dias if "brier" in h]
        brier_str = f" | Brier médio {sum(briers)/len(briers):.4f}" if briers else ""
        
        baselines_nomes = set()
        for h in mesmos_dias:
            baselines_nomes.update(h["resultados_baselines"].keys())
            
        partes_base = []
        for nome in sorted(baselines_nomes):
            acertos_b = sum(1 for h in mesmos_dias if h["resultados_baselines"].get(nome) == "✅ ACERTOU")
            total_b = sum(1 for h in mesmos_dias if h["resultados_baselines"].get(nome) in ("✅ ACERTOU", "❌ ERROU"))
            if total_b > 0:
                partes_base.append(f"{nome} {acertos_b}/{total_b}")
                
        base_str = " | " + " | ".join(partes_base) if partes_base else ""
        placar += f"\n⚖️ Mesmos dias (n={gemini_total}): Gemini {gemini_acertos}/{gemini_total}{brier_str}{base_str}"

    msg = (
        f"🌙 <b>FECHAMENTO DO DIA BTC</b>\n"
        f"📉 De: ${preco_manha:,.2f} -> Para: ${preco_atual:,.2f} ({variacao_pct:+.2f}%)\n"
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
