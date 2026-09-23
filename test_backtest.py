import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import json
import datetime
import io
import sys
import backtest

class TestBacktest(unittest.TestCase):

    def test_calc_drawdown_e_operacao_simulada_numeros_exatos(self):
        """a. Operação simulada com números exatos (acumulado e max dd)."""
        retornos = [0.018, 0.018, -0.012]
        # Acumulado = 1.018 * 1.018 * 0.988 - 1 = +2.3888%
        acum = 1.0
        for r in retornos:
            acum *= (1 + r)
        self.assertAlmostEqual(acum - 1, 0.02388812)
        
        # Drawdown = (1.0238881 - 1.036324) / 1.036324 = -0.012
        dd = backtest.calc_drawdown(retornos)
        self.assertAlmostEqual(dd, -0.012)
        
    def test_acerto_de_equilibrio(self):
        """b. Acerto de equilíbrio."""
        sim_rules = {
            'Regra Teste': {
                'ret_liquido': [0.008, 0.008, -0.012],
                'ret_bruto': [0.01, 0.01, 0.01]
            }
        }
        
        captured = io.StringIO()
        sys.stdout = captured
        backtest.print_sim_table(sim_rules, taxa=0.1)
        sys.stdout = sys.__stdout__
        out = captured.getvalue()
        
        # Equilíbrio = 0.5 + 0.002 / (2 * 0.01) = 0.5 + 0.1 = 0.6 = 60.0%
        self.assertRegex(out, r"Regra Teste\s+.*\s+60\.0%")

    @patch('robot_bitcoin.pedir')
    def test_baixar_velas_paginacao_e_falha(self, mock_pedir):
        """f. A paginação falhando no meio -> RuntimeError; o main com falha -> SystemExit com código 1."""
        class MockResponse:
            def __init__(self, json_data): self.json_data = json_data
            def json(self): return self.json_data

        start_ot = 1000000 * 3600000
        page1 = [[start_ot + i*3600000, "1", "1", "1", "1", "1", start_ot + i*3600000 + 3599999] for i in range(1000)]
        
        mock_pedir.side_effect = [MockResponse(page1), None]
        
        with patch('backtest.datetime') as mock_dt:
            mock_now = MagicMock()
            mock_now.timestamp.return_value = (start_ot + 2000 * 3600000) / 1000.0
            mock_dt.datetime.now.return_value = mock_now
            mock_dt.timezone = datetime.timezone
            
            with self.assertRaisesRegex(RuntimeError, "Falha na rede"):
                backtest.baixar_velas(50)
                
        with patch('sys.argv', ['backtest.py', 'historico']):
            with self.assertRaises(SystemExit) as cm:
                backtest.main()
            self.assertEqual(cm.exception.code, 1)

    @patch('backtest.baixar_velas')
    def test_processar_mercado_janela_e_sem_sinal(self, mock_baixar):
        """
        d. Janela: velas sintéticas onde só 11:00 e 01:00 definem resultado. 10:00, 12:00 etc não influenciam.
        e. Um dia sem sinal para uma regra não entra no n dela.
        """
        base_dt = datetime.datetime(2026, 9, 5, 11, 0, tzinfo=datetime.timezone.utc)
        ot_11 = int(base_dt.timestamp() * 1000)
        
        velas = []
        for i in range(100, 0, -1):
            ot = ot_11 - i * 3600000
            price = 1000.0 + i
            velas.append([ot, "1000", "1000", "1000", str(price), "0", ot + 3599999])
            
        velas.append([ot_11, "10000", "10000", "10000", "10000", "0", ot_11 + 3599999])
        velas.append([ot_11 + 3600000, "99999", "99999", "99999", "99999", "0", ot_11 + 3600000 + 3599999])
        
        for i in range(2, 14):
            ot = ot_11 + i * 3600000
            velas.append([ot, "1000", "1000", "1000", "1000", "0", ot + 3599999])
            
        velas.append([ot_11 + 13*3600000, "1", "1", "1", "1", "0", ot_11 + 13*3600000 + 3599999])
        
        ot_noite = ot_11 + 14 * 3600000
        velas.append([ot_noite, "10500", "10500", "10500", "10500", "0", ot_noite + 3599999])
        
        # vela das 02h -> valor igual a 1000 para que ret_8h seja 0 (pois 10h também é 1000)
        velas.append([ot_noite + 3600000, "1000", "1000", "1000", "1000", "0", ot_noite + 3600000 + 3599999])

        ot_11_2 = ot_11 + 24 * 3600000
        for i in range(16, 24):
            ot = ot_11 + i * 3600000
            velas.append([ot, "1000", "1000", "1000", "1000", "0", ot + 3599999])
            
        velas.append([ot_11_2, "10000", "10000", "10000", "10000", "0", ot_11_2 + 3599999])
        for i in range(1, 14):
            ot = ot_11_2 + i * 3600000
            velas.append([ot, "1000", "1000", "1000", "1000", "0", ot + 3599999])
            
        ot_noite_2 = ot_11_2 + 14 * 3600000
        velas.append([ot_noite_2, "10500", "10000", "10000", "10000", "0", ot_noite_2 + 3599999]) 

        mock_baixar.return_value = velas
        
        captured = io.StringIO()
        sys.stdout = captured
        backtest.processar_mercado(5, 0.1)
        sys.stdout = sys.__stdout__
        
        out = captured.getvalue()
        
        self.assertRegex(out, r"Altas\s*\(em dias não neutros\):\s*2")
        self.assertRegex(out, r"REVERSAO_RSI\s+100\.0%\s+1\s+±98\.0%")
        self.assertRegex(out, r"momentum_8h\s+0\.0%\s+1\s+±98\.0%")

    def test_processar_historico_mesmos_dias_e_filtros(self):
        """
        g. Modo historico "mesmos dias": histórico antigo real + 2 entradas completas (1 com momentum_8h None).
        c. Filtro >= 55%
        a. Operacao simulada com números exatos (verificar retorno do historico).
        """
        hist = [
            {"data":"2026-06-16","preco_8h":65734.0,"direcao":"CAIR"},
            {"data":"2026-06-16","preco_8h":65709.0,"direcao":"SUBIR","preco_noite":64751.0,"resultado":"❌ ERROU","aprendizado":"x"},
            {"data":"2026-06-17","preco_8h":64754.0,"direcao":"CAIR","preco_noite":63836.0,"resultado":"✅ ACERTOU","aprendizado":"y"},
            # Day 4: prob 55 -> conf 55 (entra no filtro)
            {"data":"2026-06-18","preco_8h":10000.0,"preco_noite":10200.0,"direcao":"SUBIR","resultado":"✅ ACERTOU","probabilidade_subir":55,"brier":0.16,"baselines":{"sempre_subir":"SUBIR","momentum_8h":"CAIR"},"resultados_baselines":{"sempre_subir":"✅ ACERTOU","momentum_8h":"❌ ERROU"}},
            # Day 5: prob 30, direcao CAIR -> conf 70 (entra no filtro). Operação vendida com queda.
            {"data":"2026-06-19","preco_8h":10000.0,"preco_noite":9800.0,"direcao":"CAIR","resultado":"✅ ACERTOU","probabilidade_subir":30,"brier":0.1225,"baselines":{"sempre_subir":"SUBIR","momentum_8h":None},"resultados_baselines":{"sempre_subir":"❌ ERROU"}},
            # Day 6: prob 54, direcao SUBIR -> conf 54 (fica fora). Operação comprada.
            {"data":"2026-06-20","preco_8h":10000.0,"preco_noite":10100.0,"direcao":"SUBIR","resultado":"✅ ACERTOU","probabilidade_subir":54,"brier":0.23,"baselines":{"sempre_subir":"SUBIR"},"resultados_baselines":{"sempre_subir":"✅ ACERTOU"}}
        ]
        
        with tempfile.NamedTemporaryFile('w', delete=False) as f:
            json.dump(hist, f)
            caminho = f.name
            
        captured = io.StringIO()
        sys.stdout = captured
        backtest.processar_historico(caminho, 0.1)
        sys.stdout = sys.__stdout__
        
        os.unlink(caminho)
        
        out = captured.getvalue()
        
        # Placar Geral (Todas): 5 avaliadas -> 4 ACERTOU, 1 ERROU -> 80.0%
        self.assertRegex(out, r"Gemini \(todas\)\s+80\.0%\s+5")
        
        # Mesmos dias: n=3 -> 3 ACERTOU -> 100.0%
        self.assertRegex(out, r"MESMOS DIAS \(n=3\)")
        self.assertRegex(out, r"Gemini\s+100\.0%\s+3")
        
        # Baselines: 
        # sempre_subir: n=3, 2 ACERTOU -> 66.7%
        self.assertRegex(out, r"sempre_subir\s+66\.7%\s+3")
        # momentum_8h: n=1, 0 ACERTOU -> 0.0%
        self.assertRegex(out, r"momentum_8h\s+0\.0%\s+1")
        
        # Simulacao "Gemini >= 55% (mesmos dias)" -> n=2 (Day 4 e 5). Retornos = +1.80%, +1.80%
        self.assertRegex(out, r"Gemini >= 55% \(mesmos dias\)\s*\+1\.80%\s*\+3\.63%")
        
        # Simulacao "Gemini (mesmos dias)" -> n=3 (Day 4, 5, 6). Retornos = +1.80%, +1.80%, +0.80%
        # Ret.Médio = (1.8 + 1.8 + 0.8) / 3 = 1.466... = 1.47%
        # Acumulado = 1.018 * 1.018 * 1.008 - 1 = +4.46%
        self.assertRegex(out, r"Gemini \(mesmos dias\)\s*\+1\.47%\s*\+4\.46%")

if __name__ == '__main__':
    unittest.main()
