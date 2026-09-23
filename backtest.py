import argparse
import sys
import datetime
import math
import json
import robot_bitcoin

def calc_drawdown(retornos):
    """Calcula a maior queda percentual (max drawdown) a partir do pico cumulativo."""
    acumulado = 1.0
    picos = 1.0
    max_dd = 0.0
    for r in retornos:
        acumulado *= (1 + r)
        if acumulado > picos:
            picos = acumulado
        dd = (acumulado - picos) / picos
        if dd < max_dd:
            max_dd = dd
    return max_dd

def print_sim_table(sim_rules, taxa):
    """Imprime a tabela de simulação de operação (retorno, acumulado, drawdown e equilíbrio)."""
    print(f"--- SIMULAÇÃO DE OPERAÇÃO (Taxa: {taxa:.2f}% por lado) ---")
    print("Aviso: simulação sem slippage. Todos os dias com sinal são operados.")
    print(f"{'Regra':<30} {'Ret.Médio':<10} {'Acumulado':<10} {'Max DD':<10} {'Acerto Mín.':<10}")
    print("-" * 75)
    
    tx_total = 2 * (taxa / 100.0)
    for name in sorted(sim_rules.keys()):
        data = sim_rules[name]
        rets = data['ret_liquido']
        brutos = data['ret_bruto']
        if not rets:
            print(f"{name:<30} {'n/d':<10} {'n/d':<10} {'n/d':<10} {'n/d':<10}")
            continue
            
        media_ret = sum(rets) / len(rets)
        
        acum = 1.0
        for r in rets:
            acum *= (1 + r)
        acum_pct = (acum - 1.0)
        
        dd = calc_drawdown(rets)
        
        if brutos:
            media_b = sum(brutos) / len(brutos)
        else:
            media_b = 0
            
        if media_b > 0:
            eq = (0.5 + tx_total / (2 * media_b))
        else:
            eq = float('nan')
            
        if not math.isnan(eq):
            eq_str = f"{eq*100:>8.1f}%"
        else:
            eq_str = "n/d"
            
        print(f"{name:<30} {media_ret*100:>+8.2f}% {acum_pct*100:>+8.2f}% {dd*100:>+8.2f}% {eq_str}")

def baixar_velas(dias):
    """Baixa velas da Binance com paginação por startTime até atingir o tempo atual."""
    agora_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    horas_totais = dias * 24 + 150
    current_start = agora_ms - horas_totais * 3600 * 1000

    velas_dict = {}
    while True:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1000&startTime={current_start}"
        resp = robot_bitcoin.pedir(url)
        if not resp:
            raise RuntimeError("Falha na rede ao baixar velas da Binance.")
            
        data = resp.json()
        if not data:
            break
            
        for v in data:
            velas_dict[v[0]] = v
            
        ultima_abertura = data[-1][0]
        current_start = ultima_abertura + 3600000
        
        if len(data) < 1000 or ultima_abertura >= agora_ms:
            break
            
    return [velas_dict[k] for k in sorted(velas_dict.keys())]

def processar_mercado(dias, taxa):
    """Executa o backtest no mercado atual baixando o número de dias especificado."""
    print("Baixando velas da Binance...")
    velas = baixar_velas(dias)
    if not velas:
        raise RuntimeError("Nenhuma vela foi obtida.")
        
    velas_por_hora = {v[0]: v for v in velas}
    open_times = sorted(velas_por_hora.keys())
    
    n_total = 0
    n_neutros = 0
    n_altas = 0
    
    regras_stats = {
        'sempre_subir': {'acertos': 0, 'n': 0},
        'momentum_8h': {'acertos': 0, 'n': 0},
        'REVERSAO_RSI': {'acertos': 0, 'n': 0},
        'MOMENTUM_24H': {'acertos': 0, 'n': 0},
        'REVERSAO_24H': {'acertos': 0, 'n': 0},
        'REVERSAO_FAIXA': {'acertos': 0, 'n': 0}
    }
    
    sim_rules = {k: {'ret_liquido': [], 'ret_bruto': []} for k in regras_stats}
    
    for ot in open_times:
        dt = datetime.datetime.fromtimestamp(ot / 1000, tz=datetime.timezone.utc)
        if dt.hour == 11:
            ot_noite = ot + 14 * 3600000
            if ot_noite not in velas_por_hora:
                continue
                
            valid = True
            fechos_100 = []
            for h in range(100, 0, -1):
                prev_ot = ot - h * 3600000
                if prev_ot not in velas_por_hora:
                    valid = False
                    break
                fechos_100.append(float(velas_por_hora[prev_ot][4]))
                
            if not valid:
                continue
                
            n_total += 1
            preco_8h = float(velas_por_hora[ot][1])
            preco_noite = float(velas_por_hora[ot_noite][1])
            
            movimento = robot_bitcoin.classificar_movimento(preco_8h, preco_noite)
            
            if movimento == "FICAR ESTÁVEL":
                n_neutros += 1
            elif movimento == "SUBIR":
                n_altas += 1
                
            indicadores = robot_bitcoin.calcular_indicadores(fechos_100)
            baselines = robot_bitcoin.calcular_baselines(indicadores)
            
            regras_dia = {}
            regras_dia["sempre_subir"] = baselines.get("sempre_subir")
            regras_dia["momentum_8h"] = baselines.get("momentum_8h")
            
            rsi = indicadores.get("rsi_14")
            if rsi is not None:
                if rsi > 70:
                    regras_dia["REVERSAO_RSI"] = "CAIR"
                elif rsi < 30:
                    regras_dia["REVERSAO_RSI"] = "SUBIR"
                else:
                    regras_dia["REVERSAO_RSI"] = None
            else:
                regras_dia["REVERSAO_RSI"] = None
            
            ret_24 = indicadores.get("ret_24h")
            if ret_24 is not None:
                if ret_24 > 0:
                    regras_dia["MOMENTUM_24H"] = "SUBIR"
                elif ret_24 < 0:
                    regras_dia["MOMENTUM_24H"] = "CAIR"
                else:
                    regras_dia["MOMENTUM_24H"] = None
                
                if ret_24 > 0:
                    regras_dia["REVERSAO_24H"] = "CAIR"
                elif ret_24 < 0:
                    regras_dia["REVERSAO_24H"] = "SUBIR"
                else:
                    regras_dia["REVERSAO_24H"] = None
            else: 
                regras_dia["MOMENTUM_24H"] = None
                regras_dia["REVERSAO_24H"] = None
                
            faixa = indicadores.get("pos_faixa_24h")
            if faixa is not None:
                if faixa > 80:
                    regras_dia["REVERSAO_FAIXA"] = "CAIR"
                elif faixa < 20:
                    regras_dia["REVERSAO_FAIXA"] = "SUBIR"
                else:
                    regras_dia["REVERSAO_FAIXA"] = None
            else:
                regras_dia["REVERSAO_FAIXA"] = None
            
            ret_bruto = (preco_noite - preco_8h) / preco_8h
            
            for nome_regra, dir_regra in regras_dia.items():
                if dir_regra in ("SUBIR", "CAIR"):
                    if movimento != "FICAR ESTÁVEL":
                        regras_stats[nome_regra]['n'] += 1
                        if dir_regra == movimento:
                            regras_stats[nome_regra]['acertos'] += 1
                            
                    if dir_regra == "SUBIR":
                        op = ret_bruto
                    else:
                        op = -ret_bruto
                        
                    liq = op - 2 * (taxa / 100.0)
                    sim_rules[nome_regra]['ret_liquido'].append(liq)
                    sim_rules[nome_regra]['ret_bruto'].append(abs(ret_bruto))

    print("=" * 65)
    print(f"BACKTEST MODO MERCADO ({dias} dias)")
    print("=" * 65)
    print(f"Total de dias avaliados: {n_total}")
    if n_total:
        pct_neutros = (n_neutros / n_total * 100)
    else:
        pct_neutros = 0
    print(f"Dias neutros: {n_neutros} ({pct_neutros:.1f}%)")
    
    nao_neutros = n_total - n_neutros
    if nao_neutros:
        pct_altas = (n_altas / nao_neutros * 100)
    else:
        pct_altas = 0
    print(f"Altas (em dias não neutros): {n_altas} ({pct_altas:.1f}%)")
    print()
    print("--- RESULTADOS DE ACERTO (dias não neutros) ---")
    print(f"{'Regra':<30} {'Acerto':<10} {'n':<6} {'IC95':<10}")
    print("-" * 65)
    for r in ['sempre_subir', 'momentum_8h', 'REVERSAO_RSI', 'MOMENTUM_24H', 'REVERSAO_24H', 'REVERSAO_FAIXA']:
        st = regras_stats[r]
        if st['n'] > 0:
            pct_acerto = st['acertos'] / st['n'] * 100
            ic = 1.96 * math.sqrt(0.25 / st['n']) * 100
            print(f"{r:<30} {pct_acerto:>5.1f}%     {st['n']:<6} ±{ic:.1f}%")
        else:
            print(f"{r:<30} {'n/d':<10} {'0':<6} {'n/d':<10}")
            
    print()
    print_sim_table(sim_rules, taxa)

def processar_historico(caminho, taxa):
    """Executa o backtest em cima do JSON histórico gerado pelo bot."""
    with open(caminho, 'r', encoding='utf-8') as f:
        hist = json.load(f)
        
    validas_todas = []
    validas_mesmos_dias = []
    
    for h in hist:
        if "preco_8h" in h and "preco_noite" in h and "direcao" in h:
            validas_todas.append(h)
            if "baselines" in h:
                validas_mesmos_dias.append(h)
    
    n_total = len(validas_todas)
    
    gemini_todas_avaliadas = [h for h in validas_todas if h.get('resultado') in ('✅ ACERTOU', '❌ ERROU')]
    gemini_todas_acertos = sum(1 for h in gemini_todas_avaliadas if h['resultado'] == '✅ ACERTOU')
    gemini_todas_n = len(gemini_todas_avaliadas)
    
    mesmos_dias_avaliadas = [h for h in validas_mesmos_dias if h.get('resultado') in ('✅ ACERTOU', '❌ ERROU') and "resultados_baselines" in h]
    gemini_mesmos_acertos = sum(1 for h in mesmos_dias_avaliadas if h['resultado'] == '✅ ACERTOU')
    gemini_mesmos_n = len(mesmos_dias_avaliadas)
    
    baselines_stats = {}
    for h in mesmos_dias_avaliadas:
        rb = h.get("resultados_baselines", {})
        for b_name, b_res in rb.items():
            if b_res in ('✅ ACERTOU', '❌ ERROU'):
                if b_name not in baselines_stats:
                    baselines_stats[b_name] = {'acertos': 0, 'n': 0}
                baselines_stats[b_name]['n'] += 1
                if b_res == '✅ ACERTOU':
                    baselines_stats[b_name]['acertos'] += 1
                    
    briers = [h['brier'] for h in mesmos_dias_avaliadas if 'brier' in h]
    if briers:
        brier_medio = sum(briers) / len(briers)
    else:
        brier_medio = float('nan')
    
    faixas = {'50-55': {'acertos': 0, 'n': 0}, '55-65': {'acertos': 0, 'n': 0}, '65+': {'acertos': 0, 'n': 0}, 'n/d': {'acertos': 0, 'n': 0}}
    for h in gemini_todas_avaliadas:
        prob = h.get('probabilidade_subir')
        if prob is None:
            f_key = 'n/d'
        else:
            if h['direcao'] == 'SUBIR':
                conf = prob
            else:
                conf = 100 - prob
                
            if conf < 55:
                f_key = '50-55'
            elif conf < 65:
                f_key = '55-65'
            else:
                f_key = '65+'
                
        faixas[f_key]['n'] += 1
        if h['resultado'] == '✅ ACERTOU':
            faixas[f_key]['acertos'] += 1
            
    sim_rules = {
        'Gemini (todas)': {'ret_liquido': [], 'ret_bruto': []},
        'Gemini (mesmos dias)': {'ret_liquido': [], 'ret_bruto': []},
        'Gemini >= 55% (mesmos dias)': {'ret_liquido': [], 'ret_bruto': []}
    }
    
    for h in validas_todas:
        p8 = float(h['preco_8h'])
        pn = float(h['preco_noite'])
        ret_bruto = (pn - p8) / p8
        
        g_dir = h['direcao']
        if g_dir == 'SUBIR':
            g_op = ret_bruto
        else:
            g_op = -ret_bruto
            
        g_liq = g_op - 2 * (taxa / 100.0)
        sim_rules['Gemini (todas)']['ret_liquido'].append(g_liq)
        sim_rules['Gemini (todas)']['ret_bruto'].append(abs(ret_bruto))
        
        if "baselines" in h:
            sim_rules['Gemini (mesmos dias)']['ret_liquido'].append(g_liq)
            sim_rules['Gemini (mesmos dias)']['ret_bruto'].append(abs(ret_bruto))
            
            prob = h.get('probabilidade_subir')
            if prob is not None:
                if g_dir == 'SUBIR':
                    conf = prob
                else:
                    conf = 100 - prob
                if conf >= 55:
                    sim_rules['Gemini >= 55% (mesmos dias)']['ret_liquido'].append(g_liq)
                    sim_rules['Gemini >= 55% (mesmos dias)']['ret_bruto'].append(abs(ret_bruto))
                    
            bs = h.get('baselines', {})
            for b_name, b_dir in bs.items():
                if b_dir in ("SUBIR", "CAIR"):
                    if b_name not in sim_rules:
                        sim_rules[b_name] = {'ret_liquido': [], 'ret_bruto': []}
                    if b_dir == 'SUBIR':
                        b_op = ret_bruto
                    else:
                        b_op = -ret_bruto
                    b_liq = b_op - 2 * (taxa / 100.0)
                    sim_rules[b_name]['ret_liquido'].append(b_liq)
                    sim_rules[b_name]['ret_bruto'].append(abs(ret_bruto))

    print("=" * 65)
    print("BACKTEST MODO HISTÓRICO")
    print("=" * 65)
    print(f"Total de entradas avaliadas: {n_total}")
    print()
    print("--- PLACAR GERAL (TODAS AS AVALIADAS) ---")
    print(f"{'Regra':<30} {'Acerto':<10} {'n':<6} {'IC95':<10}")
    print("-" * 65)
    if gemini_todas_n > 0:
        pct = gemini_todas_acertos / gemini_todas_n * 100
        ic = 1.96 * math.sqrt(0.25 / gemini_todas_n) * 100
        print(f"{'Gemini (todas)':<30} {pct:>5.1f}%     {gemini_todas_n:<6} ±{ic:.1f}%")
    else:
        print(f"{'Gemini (todas)':<30} {'n/d':<10} {'0':<6} {'n/d':<10}")

    print()
    print(f"--- MESMOS DIAS (n={gemini_mesmos_n}) ---")
    print(f"{'Regra':<30} {'Acerto':<10} {'n':<6} {'IC95':<10}")
    print("-" * 65)
    if gemini_mesmos_n > 0:
        pct = gemini_mesmos_acertos / gemini_mesmos_n * 100
        ic = 1.96 * math.sqrt(0.25 / gemini_mesmos_n) * 100
        print(f"{'Gemini':<30} {pct:>5.1f}%     {gemini_mesmos_n:<6} ±{ic:.1f}%")
    else:
        print(f"{'Gemini':<30} {'n/d':<10} {'0':<6} {'n/d':<10}")
        
    for b_name in sorted(baselines_stats.keys()):
        st = baselines_stats[b_name]
        if st['n'] > 0:
            pct = st['acertos'] / st['n'] * 100
            ic = 1.96 * math.sqrt(0.25 / st['n']) * 100
            print(f"{b_name:<30} {pct:>5.1f}%     {st['n']:<6} ±{ic:.1f}%")
            
    print()
    if not math.isnan(brier_medio):
        print(f"Brier Score Médio (Gemini): {brier_medio:.4f} (vs 0.25 do sempre 50%)")
    else:
        print("Brier Score Médio (Gemini): n/d")
        
    print()
    print("--- ACERTO POR FAIXA DE CONFIANÇA (Gemini - Todas) ---")
    print(f"{'Faixa':<15} {'Acerto':<10} {'n':<6}")
    print("-" * 45)
    for f in ['50-55', '55-65', '65+', 'n/d']:
        st = faixas[f]
        if st['n'] > 0:
            pct = st['acertos'] / st['n'] * 100
            print(f"{f:<15} {pct:>5.1f}%     {st['n']:<6}")
        else:
            print(f"{f:<15} {'n/d':<10} {'0':<6}")
            
    print()
    print_sim_table(sim_rules, taxa)

def main():
    """Ponto de entrada da linha de comando para o script de backtest."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="Ferramenta de backtest offline.")
    parser.add_argument('modo', choices=['mercado', 'historico'])
    parser.add_argument('caminho', nargs='?', help="Caminho do arquivo (apenas para modo historico)")
    parser.add_argument('--dias', type=int, default=1095, help="Dias para baixar (apenas para modo mercado)")
    parser.add_argument('--taxa', type=float, default=0.1, help="Taxa por lado em %% (padrão 0.1)")
    
    args = parser.parse_args()
    
    try:
        if args.modo == 'mercado':
            processar_mercado(args.dias, args.taxa)
        elif args.modo == 'historico':
            if not args.caminho:
                raise ValueError("Modo 'historico' requer o CAMINHO do JSON.")
            processar_historico(args.caminho, args.taxa)
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
