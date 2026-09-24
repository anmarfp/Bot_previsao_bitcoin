import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import json
import datetime

import robot_bitcoin


class TestRobotBitcoin(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        
        # Reset histórico path
        robot_bitcoin.HISTORICO_FILE = "historico_bitcoin.json"
        robot_bitcoin.MODELOS_ESGOTADOS.clear()
        
    def tearDown(self):
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    def test_classificar_movimento_limites(self):
        # 0.29% (neutro)
        self.assertEqual(robot_bitcoin.classificar_movimento(10000, 10029), "FICAR ESTÁVEL")
        self.assertEqual(robot_bitcoin.classificar_movimento(10000, 9971), "FICAR ESTÁVEL")
        # 0.30% (conta)
        self.assertEqual(robot_bitcoin.classificar_movimento(10000, 10030), "SUBIR")
        self.assertEqual(robot_bitcoin.classificar_movimento(10000, 9970), "CAIR")
        
        # Testar float issue
        self.assertEqual(robot_bitcoin.classificar_movimento(65709, 65709 * 1.003), "SUBIR")
        
    def test_validar_previsao_probabilidade(self):
        # Validos
        valido = {"noticias": "ok", "justificativa": "ok", "direcao_prevista": "SUBIR", "probabilidade_subir": 60}
        robot_bitcoin.validar_previsao(valido) # Não deve lançar
        
        valido_float = {"noticias": "ok", "justificativa": "ok", "direcao_prevista": "SUBIR", "probabilidade_subir": 62.0}
        robot_bitcoin.validar_previsao(valido_float)
        
        # Tipos e valores estritos
        for inv_prob in [50.7, "62.5", float('inf'), float('nan'), True, False]:
            with self.assertRaises(ValueError):
                robot_bitcoin.validar_previsao({"noticias": "ok", "justificativa": "ok", "direcao_prevista": "SUBIR", "probabilidade_subir": inv_prob})
                
        # Fora do range
        invalido_range = {"noticias": "ok", "justificativa": "ok", "direcao_prevista": "SUBIR", "probabilidade_subir": 105}
        with self.assertRaises(ValueError):
            robot_bitcoin.validar_previsao(invalido_range)
            
        invalido_range_neg = {"noticias": "ok", "justificativa": "ok", "direcao_prevista": "SUBIR", "probabilidade_subir": -1}
        with self.assertRaises(ValueError):
            robot_bitcoin.validar_previsao(invalido_range_neg)
            
        # Incoerentes
        incoerente_subir = {"noticias": "ok", "justificativa": "ok", "direcao_prevista": "CAIR", "probabilidade_subir": 60}
        with self.assertRaises(ValueError):
            robot_bitcoin.validar_previsao(incoerente_subir)
            
        incoerente_cair = {"noticias": "ok", "justificativa": "ok", "direcao_prevista": "SUBIR", "probabilidade_subir": 40}
        with self.assertRaises(ValueError):
            robot_bitcoin.validar_previsao(incoerente_cair)

    def test_agregar_amostras(self):
        a1 = [{"direcao_prevista": "CAIR", "probabilidade_subir": 50, "noticias": "n1", "justificativa": "j1"},
              {"direcao_prevista": "SUBIR", "probabilidade_subir": 51, "noticias": "n2", "justificativa": "j2"}]
        res1 = robot_bitcoin.agregar_amostras(a1)
        self.assertEqual(res1["direcao"], "SUBIR")
        
        a2 = [{"direcao_prevista": "SUBIR", "probabilidade_subir": 50, "noticias": "n1", "justificativa": "j1"},
              {"direcao_prevista": "CAIR", "probabilidade_subir": 49, "noticias": "n2", "justificativa": "j2"}]
        res2 = robot_bitcoin.agregar_amostras(a2)
        self.assertEqual(res2["direcao"], "CAIR")
        
        a3 = [{"direcao_prevista": "CAIR", "probabilidade_subir": 40, "noticias": "n1", "justificativa": "j1"},
              {"direcao_prevista": "SUBIR", "probabilidade_subir": 60, "noticias": "n2", "justificativa": "j2"}]
        res3 = robot_bitcoin.agregar_amostras(a3)
        self.assertEqual(res3["direcao"], "CAIR") # a primeira da lista no empate exato de votos e média 50

        # limites sem_conviccao (45 e 55)
        a_45 = [{"direcao_prevista": "CAIR", "probabilidade_subir": 45, "noticias": "n1", "justificativa": "j1"}]
        self.assertTrue(robot_bitcoin.agregar_amostras(a_45)["sem_conviccao"])
        
        a_55 = [{"direcao_prevista": "SUBIR", "probabilidade_subir": 55, "noticias": "n1", "justificativa": "j1"}]
        self.assertTrue(robot_bitcoin.agregar_amostras(a_55)["sem_conviccao"])
        
        a_44 = [{"direcao_prevista": "CAIR", "probabilidade_subir": 44, "noticias": "n1", "justificativa": "j1"}]
        self.assertFalse(robot_bitcoin.agregar_amostras(a_44)["sem_conviccao"])
        
        a_56 = [{"direcao_prevista": "SUBIR", "probabilidade_subir": 56, "noticias": "n1", "justificativa": "j1"}]
        self.assertFalse(robot_bitcoin.agregar_amostras(a_56)["sem_conviccao"])
        
        # Empate na probabilidade (50)
        empate = [
            {"direcao_prevista": "CAIR", "probabilidade_subir": 40, "noticias": "n1", "justificativa": "j1"},
            {"direcao_prevista": "CAIR", "probabilidade_subir": 40, "noticias": "n2", "justificativa": "j2"},
            {"direcao_prevista": "SUBIR", "probabilidade_subir": 70, "noticias": "n3", "justificativa": "j3"}
        ]
        res_empate = robot_bitcoin.agregar_amostras(empate)
        self.assertEqual(res_empate["probabilidade_subir"], 50)
        self.assertEqual(res_empate["direcao"], "CAIR") # maioria
        self.assertEqual(res_empate["justificativa"], "j1")

    @patch('robot_bitcoin.obter_mercado')
    @patch('robot_bitcoin.obter_noticias')
    @patch('robot_bitcoin.obter_velas')
    @patch('robot_bitcoin.obter_derivativos')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    @patch('robot_bitcoin.enviar_telegram')
    def test_previsao_manha_pont_a_ponta(self, mock_enviar, mock_agora, mock_gerar_json, mock_derivativos, mock_velas, mock_noticias, mock_mercado):
        historico_antigo = [
            {"data":"2026-06-16","preco_8h":65734.0,"direcao":"CAIR"},
            {"data":"2026-06-16","preco_8h":65709.0,"direcao":"SUBIR","preco_noite":64751.0,"resultado":"❌ ERROU","aprendizado":"x"},
            {"data":"2026-06-17","preco_8h":64754.0,"direcao":"CAIR","preco_noite":63836.0,"resultado":"✅ ACERTOU","aprendizado":"y"},
            {"data":"2026-09-22","hora_previsao":"18:19","preco_8h":86242.0,"direcao":"CAIR"}
        ]
        with open("historico_bitcoin.json", "w") as f:
            json.dump(historico_antigo, f)
            
        mock_mercado.return_value = {
            "preco": 60000.0, "var_24h": 1.0, "var_7d": 2.0,
            "max_24h": 61000.0, "min_24h": 59000.0, "volume_24h": 1e9, "fear_greed": "Greed"
        }
        mock_noticias.return_value = [{"fonte": "f", "titulo": "t", "resumo": "r", "data": datetime.datetime.now(datetime.timezone.utc)}]
        
        # Simulando dados presentes para testar o prompt
        mock_velas.return_value = [float(i) for i in range(100, 200)]
        mock_derivativos.return_value = {"funding": 0.01, "oi_var_24h": 2.5, "ls_ratio": 1.2}
        
        now = datetime.datetime(2026, 9, 22, 8, 0, tzinfo=robot_bitcoin.FUSO_BRT)
        mock_agora.return_value = now
        
        mock_gerar_json.side_effect = [
            {"direcao_prevista": "SUBIR", "probabilidade_subir": 51, "noticias": "n1", "justificativa": "j1"},
            Exception("Simulando falha"),
            {"direcao_prevista": "SUBIR", "probabilidade_subir": 53, "noticias": "n3", "justificativa": "j3"}
        ]
        
        robot_bitcoin.previsao_manha()
        
        # b. Verificar prompt da manhã
        prompt = mock_gerar_json.call_args_list[0][0][0]
        self.assertIn("RSI(14)", prompt)
        self.assertIn("Funding Rate: +0.0100%", prompt)
        self.assertIn("Variação Open Interest (24h): +2.50%", prompt)
        self.assertIn("Long/Short Ratio: 1.20", prompt)
        self.assertIn("-1.46%", prompt) # Variação calculada: (64751 - 65709) / 65709
        self.assertIn("Lição de ontem: y", prompt)
        self.assertNotIn('"probabilidade_subir": 60', prompt) # Certifica que o exemplo de JSON no prompt não tem "60"
        self.assertIn("inteiro de 0 a 100", prompt)
        
        hist = robot_bitcoin.manipular_historico("ler")
        self.assertEqual(len(hist), 4) # 4 antigos, mas o último é do mesmo dia e não avaliado, então substitui
        self.assertEqual(hist[-1]["probabilidade_subir"], 52)
        self.assertEqual(hist[-1]["sem_conviccao"], True)
        
        msg = mock_enviar.call_args[0][0]
        self.assertIn("🔮 Previsão: <b>SUBIR</b> (52% de probabilidade)", msg)
        self.assertIn("⚠️ <b>sem convicção</b>", msg)

    @patch('robot_bitcoin.obter_mercado')
    @patch('robot_bitcoin.obter_noticias')
    @patch('robot_bitcoin.obter_velas')
    @patch('robot_bitcoin.obter_derivativos')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    @patch('robot_bitcoin.enviar_telegram')
    def test_previsao_manha_cair(self, mock_enviar, mock_agora, mock_gerar_json, mock_derivativos, mock_velas, mock_noticias, mock_mercado):
        mock_mercado.return_value = {"preco": 60000.0, "var_24h": 1.0, "var_7d": 2.0, "max_24h": 61000.0, "min_24h": 59000.0, "volume_24h": 1e9, "fear_greed": "Greed"}
        mock_noticias.return_value = [{"fonte": "f", "titulo": "t", "resumo": "r", "data": datetime.datetime.now(datetime.timezone.utc)}]
        mock_velas.return_value = []
        mock_derivativos.return_value = {"funding": None, "oi_var_24h": None, "ls_ratio": None}
        mock_agora.return_value = datetime.datetime(2026, 9, 22, 8, 0, tzinfo=robot_bitcoin.FUSO_BRT)
        
        mock_gerar_json.return_value = {"direcao_prevista": "CAIR", "probabilidade_subir": 38, "noticias": "n", "justificativa": "j"}
        
        robot_bitcoin.previsao_manha()
        
        # b. Prompt com dados AUSENTES mostra "n/d"
        prompt = mock_gerar_json.call_args_list[0][0][0]
        self.assertIn("RSI(14): n/d", prompt)
        self.assertIn("Funding Rate: n/d", prompt)
        
        # c. Mensagem para CAIR
        msg = mock_enviar.call_args[0][0]
        self.assertIn("<b>CAIR</b> (62% de probabilidade)", msg)
        self.assertNotIn("sem convicção", msg)

    @patch('robot_bitcoin.obter_mercado')
    @patch('robot_bitcoin.obter_noticias')
    @patch('robot_bitcoin.obter_velas')
    @patch('robot_bitcoin.obter_derivativos')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    def test_previsao_manha_todas_falham(self, mock_agora, mock_gerar_json, mock_derivativos, mock_velas, mock_noticias, mock_mercado):
        mock_mercado.return_value = {"preco": 60000.0, "var_24h": 1.0, "var_7d": 2.0, "max_24h": 61000.0, "min_24h": 59000.0, "volume_24h": 1e9, "fear_greed": "Greed"}
        mock_noticias.return_value = [{"fonte": "f", "titulo": "t", "resumo": "r", "data": datetime.datetime.now(datetime.timezone.utc)}]
        mock_velas.return_value = []
        mock_derivativos.return_value = {"funding": None, "oi_var_24h": None, "ls_ratio": None}
        mock_agora.return_value = datetime.datetime(2026, 9, 22, 8, 0, tzinfo=robot_bitcoin.FUSO_BRT)
        
        # a. As 3 amostras falham
        mock_gerar_json.side_effect = Exception("Erro da API")
        
        with self.assertRaises(Exception) as context:
            robot_bitcoin.previsao_manha()
            
        self.assertEqual(str(context.exception), "Erro da API")
        
        # Histórico não gravado (continua vazio)
        hist = robot_bitcoin.manipular_historico("ler")
        self.assertEqual(len(hist), 0)

    @patch('robot_bitcoin.obter_preco_bitcoin')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    @patch('robot_bitcoin.enviar_telegram')
    def test_verificacao_noite_historico_antigo(self, mock_enviar, mock_agora, mock_gerar_json, mock_obter_preco):
        historico_antigo = [
            {"data":"2026-06-16","preco_8h":65734.0,"direcao":"CAIR"},
            {"data":"2026-06-16","preco_8h":65709.0,"direcao":"SUBIR","preco_noite":64751.0,"resultado":"❌ ERROU","aprendizado":"x"},
            {"data":"2026-06-17","preco_8h":64754.0,"direcao":"CAIR","preco_noite":63836.0,"resultado":"✅ ACERTOU","aprendizado":"y"},
            {"data":"2026-09-22","hora_previsao":"18:19","preco_8h":86242.0,"direcao":"CAIR"}
        ]
        
        hoje = datetime.date(2026, 9, 23)
        mock_agora.return_value = datetime.datetime.combine(hoje, datetime.time(22, 0)).replace(tzinfo=robot_bitcoin.FUSO_BRT)
        
        entrada_nova = {
            "data": "2026-09-23",
            "preco_8h": 10000.0,
            "direcao": "SUBIR",
            "probabilidade_subir": 60,
            "justificativa": "motivo forte",
            "baselines": {"sempre_subir": "SUBIR", "momentum_8h": "CAIR"}
        }
        entrada_nova2 = {
            "data": "2026-09-24",
            "preco_8h": 10000.0,
            "direcao": "SUBIR",
            "probabilidade_subir": 60,
            "justificativa": "motivo forte",
            "resultado": "✅ ACERTOU",
            "brier": 0.16,
            "resultados_baselines": {"sempre_subir": "✅ ACERTOU"} # momentum_8h = None neste dia
        }
        historico_antigo.append(entrada_nova2)
        historico_antigo.append(entrada_nova)
        
        with open("historico_bitcoin.json", "w") as f:
            json.dump(historico_antigo, f)
            
        mock_obter_preco.return_value = 10100.0 # Subiu 1%
        mock_gerar_json.return_value = {"aprendizado": "teste aprendizado"}
        
        robot_bitcoin.verificacao_noite()
        
        msg = mock_enviar.call_args[0][0]
        self.assertIn("Mesmos dias (n=2): Gemini 2/2 | Brier médio 0.1600 | momentum_8h 0/1 | sempre_subir 2/2", msg)

    @patch('robot_bitcoin.obter_preco_bitcoin')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    @patch('robot_bitcoin.enviar_telegram')
    def test_verificacao_noite_faixa_neutra(self, mock_enviar, mock_agora, mock_gerar_json, mock_obter_preco):
        # e. Noite com variação abaixo de 0,3% -> SEM VARIAÇÃO, sem brier
        mock_agora.return_value = datetime.datetime(2026, 9, 23, 22, 0, tzinfo=robot_bitcoin.FUSO_BRT)
        
        entrada_nova = {
            "data": "2026-09-23",
            "preco_8h": 10000.0,
            "direcao": "SUBIR",
            "probabilidade_subir": 60,
        }
        with open("historico_bitcoin.json", "w") as f:
            json.dump([entrada_nova], f)
            
        mock_obter_preco.return_value = 10029.0 # Subiu 0.29%
        mock_gerar_json.return_value = {"aprendizado": "x"}
        
        robot_bitcoin.verificacao_noite()
        
        hist = robot_bitcoin.manipular_historico("ler")
        self.assertEqual(hist[-1]["resultado"], "⚪ SEM VARIAÇÃO")
        self.assertNotIn("brier", hist[-1]) # sem brier
        
        msg = mock_enviar.call_args[0][0]
        self.assertIn("⚪ SEM VARIAÇÃO", msg)
        self.assertNotIn("Placar Gemini", msg)  # dia neutro não entra no placar

    @patch('robot_bitcoin.obter_preco_bitcoin')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    @patch('robot_bitcoin.enviar_telegram')
    def test_verificacao_noite_brier_medio(self, mock_enviar, mock_agora, mock_gerar_json, mock_obter_preco):
        mock_agora.return_value = datetime.datetime(2026, 9, 23, 22, 0, tzinfo=robot_bitcoin.FUSO_BRT)
        historico = [
            {"data": "2026-09-22", "preco_8h": 10000.0, "direcao": "CAIR", "probabilidade_subir": 30,
             "preco_noite": 9900.0, "resultado": "✅ ACERTOU", "brier": 0.09, "aprendizado": "a", "resultados_baselines": {"sempre_subir": "✅ ACERTOU"}},
            {"data": "2026-09-23", "preco_8h": 10000.0, "direcao": "SUBIR", "probabilidade_subir": 60, "baselines": {"sempre_subir": "SUBIR"}},
        ]
        with open("historico_bitcoin.json", "w") as f:
            json.dump(historico, f)

        mock_obter_preco.return_value = 10100.0  # +1% -> brier (0,6 - 1)^2 = 0,16
        mock_gerar_json.return_value = {"aprendizado": "x"}

        robot_bitcoin.verificacao_noite()

        msg = mock_enviar.call_args[0][0]
        self.assertIn("Placar Gemini: 2/2 (100%)", msg)
        self.assertIn("Brier médio 0.1250", msg)

    @patch('robot_bitcoin.obter_preco_bitcoin')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    @patch('robot_bitcoin.enviar_telegram')
    def test_verificacao_noite_entrada_antiga(self, mock_enviar, mock_agora, mock_gerar_json, mock_obter_preco):
        # f. Entrada antiga sem probabilidade não ganha brier e não quebra
        mock_agora.return_value = datetime.datetime(2026, 9, 23, 22, 0, tzinfo=robot_bitcoin.FUSO_BRT)
        
        entrada_nova = {
            "data": "2026-09-23",
            "preco_8h": 10000.0,
            "direcao": "SUBIR",
        }
        with open("historico_bitcoin.json", "w") as f:
            json.dump([entrada_nova], f)
            
        mock_obter_preco.return_value = 11000.0
        mock_gerar_json.return_value = {"aprendizado": "x"}
        
        robot_bitcoin.verificacao_noite() # Nao deve quebrar
        
        hist = robot_bitcoin.manipular_historico("ler")
        self.assertNotIn("brier", hist[-1])

        msg = mock_enviar.call_args[0][0]
        self.assertIn("Placar Gemini: 1/1", msg)
        self.assertNotIn("Mesmos dias", msg)  # sem dias com baselines, a comparação não aparece

    @patch('robot_bitcoin.pedir')
    @patch('time.sleep')
    def test_obter_velas_e_derivativos(self, mock_sleep, mock_pedir):
        # g. obter_velas e obter_derivativos
        class MockResponse:
            def __init__(self, json_data):
                self.json_data = json_data
            def json(self):
                return self.json_data

        # Sucesso
        def side_effect_sucesso(url, *args, **kwargs):
            if "klines" in url:
                return MockResponse([["t", "o", "h", "l", "60000.0", "v", "0"]])
            if "premiumIndex" in url:
                return MockResponse({"lastFundingRate": "0.0001"})
            if "openInterestHist" in url:
                return MockResponse([{"sumOpenInterest": "1000"}, {"sumOpenInterest": "1050"}])
            if "globalLongShortAccountRatio" in url:
                return MockResponse([{"longShortRatio": "1.2"}])
            return None
            
        mock_pedir.side_effect = side_effect_sucesso
        
        velas = robot_bitcoin.obter_velas()
        self.assertEqual(velas, [60000.0])
        
        derivs = robot_bitcoin.obter_derivativos()
        self.assertAlmostEqual(derivs["funding"], 0.01) # 0.0001 * 100
        self.assertAlmostEqual(derivs["oi_var_24h"], 5.0) # (1050-1000)/1000 * 100
        self.assertAlmostEqual(derivs["ls_ratio"], 1.2)
        
        # Falha (lista vazia / None)
        mock_pedir.side_effect = lambda url, *args, **kwargs: None
        
        velas_falha = robot_bitcoin.obter_velas()
        self.assertEqual(velas_falha, [])
        
        derivs_falha = robot_bitcoin.obter_derivativos()
        self.assertIsNone(derivs_falha["funding"])
        self.assertIsNone(derivs_falha["oi_var_24h"])
        self.assertIsNone(derivs_falha["ls_ratio"])

    def test_calcular_indicadores_rsi(self):
        fechos = [float(i) for i in range(100, 130)]
        ind = robot_bitcoin.calcular_indicadores(fechos)
        self.assertAlmostEqual(ind["rsi_14"], 100.0)
        self.assertIsNotNone(ind["vol_24h"])
        self.assertAlmostEqual(ind["pos_faixa_24h"], 100.0)

    @patch('robot_bitcoin.pedir')
    @patch('robot_bitcoin.time.time')
    def test_obter_velas_descarta_vela_em_curso(self, mock_time, mock_pedir):
        class MockResponse:
            def __init__(self, json_data): self.json_data = json_data
            def json(self): return self.json_data

        velas_api = [
            ["t1", "o", "h", "l", "60000.0", "v", "1000"],
            ["t2", "o", "h", "l", "61000.0", "v", "3000"],  # close_time no futuro: vela em curso
        ]
        mock_pedir.return_value = MockResponse(velas_api)
        mock_time.return_value = 2.0  # 2000 ms
        self.assertEqual(robot_bitcoin.obter_velas(), [60000.0])

        mock_time.return_value = 5.0  # todas fechadas: mantém a lista inteira
        self.assertEqual(robot_bitcoin.obter_velas(), [60000.0, 61000.0])




    @patch('robot_bitcoin.time.sleep')
    @patch('robot_bitcoin.genai.Client')
    def test_gerar_json_regressao_429_diario(self, mock_client_class, mock_sleep):
        # a. 429 diário e depois sucesso no segundo modelo
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        from google.genai.errors import ClientError
        err_diario = ClientError(429, {"error": {"code": 429, "message": "Quota exceeded ... quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier", "status": "RESOURCE_EXHAUSTED"}})
        
        mock_response = MagicMock()
        mock_response.text = '{"chave": "valor"}'
        
        mock_client.models.generate_content.side_effect = [err_diario, mock_response]
        
        def validar_mock(d): pass
        
        dados = robot_bitcoin.gerar_json("prompt", {}, validar_mock)
        
        # Sucesso sem sleep
        mock_sleep.assert_not_called()
        self.assertEqual(dados["chave"], "valor")
        
        # model= da segunda chamada deve ser o 2o da lista
        self.assertEqual(mock_client.models.generate_content.call_count, 2)
        args_1 = mock_client.models.generate_content.call_args_list[0][1]
        args_2 = mock_client.models.generate_content.call_args_list[1][1]
        
        self.assertEqual(args_1["model"], robot_bitcoin.MODELOS_GEMINI[0])
        self.assertEqual(args_2["model"], robot_bitcoin.MODELOS_GEMINI[1])
        self.assertEqual(dados["modelo"], robot_bitcoin.MODELOS_GEMINI[1])
        
        # Uma segunda chamada no mesmo processo deve começar direto pelo 2o modelo
        mock_response2 = MagicMock()
        mock_response2.text = '{"chave": "valor2"}'
        mock_client.models.generate_content.side_effect = [mock_response2]
        
        dados2 = robot_bitcoin.gerar_json("prompt", {}, validar_mock)
        self.assertEqual(dados2["chave"], "valor2")
        self.assertEqual(dados2["modelo"], robot_bitcoin.MODELOS_GEMINI[1])
        args_3 = mock_client.models.generate_content.call_args_list[2][1]
        self.assertEqual(args_3["model"], robot_bitcoin.MODELOS_GEMINI[1])

    @patch('robot_bitcoin.time.sleep')
    @patch('robot_bitcoin.genai.Client')
    def test_gerar_json_404_e_429_por_minuto(self, mock_client_class, mock_sleep):
        # Modelo retirado (404) é pulado sem espera; 429 por minuto espera e não marca o modelo como esgotado
        from google.genai.errors import ClientError
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        err_404 = ClientError(404, {"error": {"code": 404, "message": "model not found", "status": "NOT_FOUND"}})
        err_minuto = ClientError(429, {"error": {"code": 429, "message": "Too many requests per minute", "status": "RESOURCE_EXHAUSTED"}})
        resposta = MagicMock()
        resposta.text = '{"ok": 1}'
        mock_client.models.generate_content.side_effect = [err_404, err_minuto, resposta]

        dados = robot_bitcoin.gerar_json("prompt", {}, lambda d: None)

        modelos = [c.kwargs["model"] for c in mock_client.models.generate_content.call_args_list]
        self.assertEqual(modelos, [robot_bitcoin.MODELOS_GEMINI[0], robot_bitcoin.MODELOS_GEMINI[1], robot_bitcoin.MODELOS_GEMINI[1]])
        self.assertEqual(robot_bitcoin.MODELOS_ESGOTADOS, {robot_bitcoin.MODELOS_GEMINI[0]})
        mock_sleep.assert_called_once_with(20)  # só o 429 por minuto espera
        self.assertEqual(dados["modelo"], robot_bitcoin.MODELOS_GEMINI[1])

    @patch('robot_bitcoin.time.sleep')
    @patch('robot_bitcoin.genai.Client')
    def test_gerar_json_503_frequente(self, mock_client_class, mock_sleep):
        # b. 503 em FALHAS_ANTES_DE_TROCAR tentativas seguidas -> troca de modelo; ciclo volta.
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        from google.genai.errors import ServerError
        err_503 = ServerError(503, {"error": {"code": 503, "message": "x", "status": "UNAVAILABLE"}})
        
        mock_response = MagicMock()
        mock_response.text = '{"chave": "valor"}'
        
        num_modelos = len(robot_bitcoin.MODELOS_GEMINI)
        # Falha (FALHAS_ANTES_DE_TROCAR) vezes em CADA modelo para forçar o ciclo completo.
        # Depois falha mais 1 vez no modelo 1 (para provar que voltou) e aí o modelo 1 responde.
        side_effects = [err_503] * (num_modelos * robot_bitcoin.FALHAS_ANTES_DE_TROCAR + 1)
        side_effects.append(mock_response)
        
        mock_client.models.generate_content.side_effect = side_effects
        def validar_mock(d): pass
        
        dados = robot_bitcoin.gerar_json("prompt", {}, validar_mock)
        self.assertEqual(dados["chave"], "valor")
        
        # Verifica as esperas crescentes e limitadas.
        esperas = [c[0][0] for c in mock_sleep.call_args_list]
        self.assertEqual(len(esperas), len(side_effects) - 1)
        self.assertTrue(all(e <= robot_bitcoin.ESPERA_MAXIMA for e in esperas))
        
        # Verifica a troca de modelos.
        calls = mock_client.models.generate_content.call_args_list
        modelos_chamados = [c[1]["model"] for c in calls]
        
        esperado_modelos = []
        for i in range(num_modelos):
            esperado_modelos.extend([robot_bitcoin.MODELOS_GEMINI[i]] * robot_bitcoin.FALHAS_ANTES_DE_TROCAR)
        esperado_modelos.append(robot_bitcoin.MODELOS_GEMINI[0]) # Voltou pro 1o e falhou
        esperado_modelos.append(robot_bitcoin.MODELOS_GEMINI[0]) # Voltou pro 1o e acertou
        
        self.assertEqual(modelos_chamados, esperado_modelos)

    @patch('robot_bitcoin.time.sleep')
    @patch('robot_bitcoin.genai.Client')
    def test_gerar_json_todos_esgotados(self, mock_client_class, mock_sleep):
        # c. Todos os modelos com 429 diário -> sleep(ESPERA_COTA) e recomeça pelo primeiro
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        from google.genai.errors import ClientError
        err_diario = ClientError(429, {"error": {"code": 429, "message": "Quota exceeded ... quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier", "status": "RESOURCE_EXHAUSTED"}})
        
        mock_response = MagicMock()
        mock_response.text = '{"chave": "valor"}'
        
        num_modelos = len(robot_bitcoin.MODELOS_GEMINI)
        side_effects = [err_diario] * num_modelos
        side_effects.append(mock_response)
        
        mock_client.models.generate_content.side_effect = side_effects
        def validar_mock(d): pass
        
        dados = robot_bitcoin.gerar_json("prompt", {}, validar_mock)
        
        mock_sleep.assert_called_once_with(robot_bitcoin.ESPERA_COTA)
        self.assertEqual(dados["modelo"], robot_bitcoin.MODELOS_GEMINI[0])

    def test_montar_modelos(self):
        # d. GEMINI_MODELOS parsing
        self.assertEqual(robot_bitcoin.montar_modelos("a, b,,a", "principal"), ["principal", "a", "b"])

    @patch('robot_bitcoin.obter_mercado')
    @patch('robot_bitcoin.obter_noticias')
    @patch('robot_bitcoin.obter_velas')
    @patch('robot_bitcoin.obter_derivativos')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    @patch('robot_bitcoin.enviar_telegram')
    def test_previsao_manha_modelos_diferentes(self, mock_enviar, mock_agora, mock_gerar_json, mock_derivativos, mock_velas, mock_noticias, mock_mercado):
        # e. previsao_manha com amostras vindas de modelos diferentes
        mock_mercado.return_value = {"preco": 60000.0, "var_24h": 1.0, "var_7d": 2.0, "max_24h": 61000.0, "min_24h": 59000.0, "volume_24h": 1e9, "fear_greed": "Greed"}
        mock_noticias.return_value = [{"fonte": "f", "titulo": "t", "resumo": "r", "data": datetime.datetime.now(datetime.timezone.utc)}]
        mock_velas.return_value = []
        mock_derivativos.return_value = {"funding": None, "oi_var_24h": None, "ls_ratio": None}
        mock_agora.return_value = datetime.datetime(2026, 9, 22, 8, 0, tzinfo=robot_bitcoin.FUSO_BRT)
        
        mock_gerar_json.side_effect = [
            {"direcao_prevista": "SUBIR", "probabilidade_subir": 51, "noticias": "n1", "justificativa": "j1", "modelo": "a"},
            {"direcao_prevista": "SUBIR", "probabilidade_subir": 52, "noticias": "n2", "justificativa": "j2", "modelo": "b"},
            {"direcao_prevista": "SUBIR", "probabilidade_subir": 53, "noticias": "n3", "justificativa": "j3", "modelo": "a"},
        ]
        
        robot_bitcoin.previsao_manha()
        
        hist = robot_bitcoin.manipular_historico("ler")
        self.assertEqual(hist[-1]["modelos"], ["a", "b", "a"])

    @patch('robot_bitcoin.time.sleep')
    @patch('robot_bitcoin.genai.Client')
    def test_gerar_json_erros_fatais_e_invalidos(self, mock_client_class, mock_sleep):
        # f. 400 relançado sem sleep e sem troca de modelo
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        from google.genai.errors import ClientError
        mock_client.models.generate_content.side_effect = ClientError(400, {"error": {"code": 400, "message": "x", "status": "INVALID_ARGUMENT"}})
        
        def validar_mock(d): pass
        
        with self.assertRaises(ClientError):
            robot_bitcoin.gerar_json("prompt", {}, validar_mock)
        self.assertEqual(mock_sleep.call_count, 0)
        
        # JSON inválido 5 vezes
        mock_response = MagicMock()
        mock_response.text = 'nao e json'
        mock_client.models.generate_content.side_effect = [mock_response] * 5
        
        with self.assertRaises(ValueError):
            robot_bitcoin.gerar_json("prompt", {}, validar_mock)
            
        self.assertEqual(mock_sleep.call_count, 4)

    @patch('robot_bitcoin.obter_preco_bitcoin')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    @patch('robot_bitcoin.enviar_telegram')
    def test_concorrencia_noite(self, mock_enviar, mock_agora, mock_gerar_json, mock_obter_preco):
        # d. Concorrência na noite
        mock_agora.return_value = datetime.datetime(2026, 9, 23, 22, 0, tzinfo=robot_bitcoin.FUSO_BRT)
        mock_obter_preco.return_value = 11000.0
        
        entrada_original = {
            "data": "2026-09-23",
            "preco_8h": 10000.0,
            "direcao": "SUBIR"
        }
        with open("historico_bitcoin.json", "w") as f:
            import json
            json.dump([entrada_original], f)
            
        def mock_gerar_json_side_effect(prompt, config, validar):
            # Simula que durante a geracao de JSON da noite, a previsao da manha seguinte rodou
            hist = robot_bitcoin.manipular_historico("ler")
            nova_entrada = {
                "data": "2026-09-24",
                "preco_8h": 11000.0,
                "direcao": "CAIR"
            }
            hist.append(nova_entrada)
            robot_bitcoin.manipular_historico("salvar", hist)
            return {"aprendizado": "x"}
            
        mock_gerar_json.side_effect = mock_gerar_json_side_effect
        
        robot_bitcoin.verificacao_noite()
        
        hist = robot_bitcoin.manipular_historico("ler")
        self.assertEqual(len(hist), 2)
        # Verifica se a entrada original foi avaliada e esta na posicao 0
        self.assertEqual(hist[0]["data"], "2026-09-23")
        self.assertEqual(hist[0]["resultado"], "✅ ACERTOU")
        # Verifica se a nova entrada continuou intacta
        self.assertEqual(hist[1]["data"], "2026-09-24")
        self.assertNotIn("resultado", hist[1])

    @patch('robot_bitcoin.obter_mercado')
    @patch('robot_bitcoin.obter_noticias')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    @patch('robot_bitcoin.obter_velas')
    @patch('robot_bitcoin.obter_derivativos')
    @patch('robot_bitcoin.enviar_telegram')
    def test_concorrencia_manha(self, mock_enviar, mock_derivativos, mock_velas, mock_agora, mock_gerar_json, mock_noticias, mock_mercado):
        # e. Concorrência na manhã (sem rede: mercado e notícias simulados)
        mock_agora.return_value = datetime.datetime(2026, 9, 24, 8, 0, tzinfo=robot_bitcoin.FUSO_BRT)
        mock_mercado.return_value = {
            "preco": 11000.0, "var_24h": 1.0, "var_7d": 2.0,
            "max_24h": 11100.0, "min_24h": 10900.0, "volume_24h": 1e9, "fear_greed": None
        }
        mock_noticias.return_value = [{"fonte": "f", "titulo": "t", "resumo": "", "data": datetime.datetime.now(datetime.timezone.utc)}]
        mock_velas.return_value = [10000.0] * 100
        mock_derivativos.return_value = {"funding": 0, "oi_var_24h": 0, "ls_ratio": 1}
        
        entrada_anterior = {
            "data": "2026-09-23",
            "preco_8h": 10000.0,
            "direcao": "SUBIR"
        }
        with open("historico_bitcoin.json", "w") as f:
            json.dump([entrada_anterior], f)
            
        def mock_gerar_json_side_effect(*args, **kwargs):
            # Simula que durante a geracao de JSON da manha, a avaliacao da noite anterior terminou
            hist = robot_bitcoin.manipular_historico("ler")
            hist[0]["resultado"] = "✅ ACERTOU"
            robot_bitcoin.manipular_historico("salvar", hist)
            
            return {
                "noticias": "x",
                "direcao_prevista": "SUBIR",
                "probabilidade_subir": 60,
                "justificativa": "x"
            }
            
        mock_gerar_json.side_effect = mock_gerar_json_side_effect
        
        
        robot_bitcoin.previsao_manha()
        
        hist = robot_bitcoin.manipular_historico("ler")
        self.assertEqual(len(hist), 2)
        # Avaliacao da entrada anterior foi preservada?
        self.assertEqual(hist[0]["resultado"], "✅ ACERTOU")
        # Nova entrada foi inserida?
        self.assertEqual(hist[1]["data"], "2026-09-24")

    @patch('robot_bitcoin.pedir')
    def test_obter_preco_bitcoin_coingecko_ok(self, mock_pedir):
        class MockResponse:
            def json(self): return {"bitcoin": {"usd": 60000.0}}
        mock_pedir.return_value = MockResponse()
        
        preco = robot_bitcoin.obter_preco_bitcoin()
        
        self.assertEqual(preco, 60000.0)
        mock_pedir.assert_called_once_with("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")

    @patch('robot_bitcoin.pedir')
    def test_obter_preco_bitcoin_coingecko_falha_binance_ok(self, mock_pedir):
        class MockResponseBinance:
            def json(self): return {"price": "61000.0"}
            
        mock_pedir.side_effect = [None, MockResponseBinance()]
        
        preco = robot_bitcoin.obter_preco_bitcoin()
        
        self.assertEqual(preco, 61000.0)
        self.assertEqual(mock_pedir.call_count, 2)
        self.assertEqual(mock_pedir.call_args_list[0][0][0], "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
        self.assertEqual(mock_pedir.call_args_list[1][0][0], "https://data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT")

    @patch('robot_bitcoin.pedir')
    def test_obter_preco_bitcoin_coingecko_json_invalido_binance_ok(self, mock_pedir):
        class MockResponseCoinGeckoInvalido:
            def json(self): return {"erro": "limite"}
            
        class MockResponseBinance:
            def json(self): return {"price": "61000.0"}
            
        mock_pedir.side_effect = [MockResponseCoinGeckoInvalido(), MockResponseBinance()]
        
        preco = robot_bitcoin.obter_preco_bitcoin()
        self.assertEqual(preco, 61000.0)

    @patch('robot_bitcoin.pedir')
    def test_obter_preco_bitcoin_ambos_falham(self, mock_pedir):
        mock_pedir.side_effect = [None, None]
        preco = robot_bitcoin.obter_preco_bitcoin()
        self.assertIsNone(preco)

    @patch('robot_bitcoin.pedir')
    @patch('robot_bitcoin.gerar_json')
    @patch('robot_bitcoin.agora')
    @patch('robot_bitcoin.enviar_telegram')
    def test_verificacao_noite_coingecko_falha_binance_ok(self, mock_enviar, mock_agora, mock_gerar_json, mock_pedir):
        mock_agora.return_value = datetime.datetime(2026, 9, 23, 22, 0, tzinfo=robot_bitcoin.FUSO_BRT)
        
        entrada_nova = {
            "data": "2026-09-23",
            "preco_8h": 10000.0,
            "direcao": "SUBIR"
        }
        with open("historico_bitcoin.json", "w") as f:
            json.dump([entrada_nova], f)
            
        class MockResponseBinance:
            def json(self): return {"price": "11000.0"}
            
        # Simula Coingecko falhando e Binance respondendo (quando obter_preco_bitcoin for chamado)
        mock_pedir.side_effect = [None, MockResponseBinance()]
        mock_gerar_json.return_value = {"aprendizado": "x"}
        
        robot_bitcoin.verificacao_noite()
        
        hist = robot_bitcoin.manipular_historico("ler")
        self.assertEqual(hist[-1]["resultado"], "✅ ACERTOU")
        self.assertEqual(hist[-1]["preco_noite"], 11000.0)

if __name__ == '__main__':
    unittest.main()
