#Testes do analisador da programação das TVs do Garage Burger

import csv
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from garage import (
    Avaliacao,
    Indicadores,
    Recomendacao,
    ResumoConteudo,
    calcular_indicadores,
    exportar_relatorio,
    filtrar_avaliacoes,
    gerar_recomendacao,
    importar_avaliacoes,
)


# Cabeçalhos escritos de novo aqui, para o teste não depender das constantes do garage.py.
CABECALHO_ENTRADA = (
    "id_resposta", "data_hora", "mesa", "tv_id",
    "conteudo_exibido", "nota_conteudo", "preferencia",
)
CABECALHO_SAIDA = (
    "posicao", "conteudo", "qtd_avaliacoes", "nota_media",
    "taxa_aceitacao", "votos_preferencia",
)


def avaliacao(
    identificador="SIM-01",
    data="2026-10-30T19:00:00",
    conteudo="rock",
    nota=5,
    preferencia=None,
    tv_id="TV1",
):
    """Cria uma resposta inventada, já no formato importado, para usar nos testes."""
    return Avaliacao(
        id_resposta=identificador,
        data_hora=datetime.fromisoformat(data),
        mesa="23",
        tv_id=tv_id,
        conteudo_exibido=conteudo,
        nota_conteudo=nota,
        preferencia=preferencia,
    )


class ArquivosTemporarios(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporario.cleanup)
        self.pasta = Path(self.temporario.name)

    def escrever_csv(self, linhas, cabecalho=CABECALHO_ENTRADA):
        caminho = self.pasta / "entrada.csv"
        with caminho.open("w", encoding="utf-8", newline="") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";")
            escritor.writerow(cabecalho)
            escritor.writerows(linhas)
        return caminho


class TestHU01Importacao(ArquivosTemporarios):
    def test_hu01_ca01_importa_e_normaliza_csv_valido(self):
        """HU01-CA01: converte os tipos, normaliza os textos e mantém os campos opcionais."""
        caminho = self.escrever_csv([
            ["SIM-01", "2026-10-30T19:00:00", " 023 ", " TV1 ", " ROCK ", "4", " POP "],
            ["SIM-02", "2026-10-30T20:00:00", "", "TV2", "pop", "5", ""],
        ])
        resultado = importar_avaliacoes(caminho)
        self.assertEqual(resultado.erros, [])
        self.assertEqual(len(resultado.avaliacoes), 2)
        primeira, segunda = resultado.avaliacoes
        self.assertEqual(primeira.data_hora, datetime(2026, 10, 30, 19))
        self.assertIs(type(primeira.nota_conteudo), int)
        self.assertEqual(primeira.nota_conteudo, 4)
        self.assertEqual(primeira.mesa, "023")
        self.assertEqual(primeira.tv_id, "TV1")
        self.assertEqual(primeira.conteudo_exibido, "rock")
        self.assertEqual(primeira.preferencia, "pop")
        self.assertIsNone(segunda.mesa)
        self.assertIsNone(segunda.preferencia)

    def test_hu01_ca02_rejeita_arquivo_com_cabecalho_incompleto(self):
        """HU01-CA02: cada coluna obrigatória ausente impede a importação."""
        for campo in CABECALHO_ENTRADA:
            with self.subTest(campo=campo):
                cabecalho = tuple(c for c in CABECALHO_ENTRADA if c != campo)
                caminho = self.escrever_csv([], cabecalho)
                with self.assertRaisesRegex(ValueError, campo):
                    importar_avaliacoes(caminho)

    def test_hu01_ca03_informa_linha_invalida_e_preserva_as_validas(self):
        """HU01-CA03: rejeita a linha inválida, informando a linha e o campo."""
        casos = [
            ("id_resposta", ""), ("data_hora", "30/99/2026 19:00"),
            ("tv_id", ""), ("conteudo_exibido", "desconhecido"),
            ("nota_conteudo", ""), ("nota_conteudo", "0"),
            ("nota_conteudo", "6"), ("nota_conteudo", "4.5"),
            ("preferencia", "desconhecida"),
        ]
        for campo, valor in casos:
            with self.subTest(campo=campo, valor=valor):
                invalida = ["SIM-01", "2026-10-30T19:00:00", "23", "TV1", "rock", "4", "pop"]
                invalida[CABECALHO_ENTRADA.index(campo)] = valor
                valida = ["SIM-02", "2026-10-30T20:00:00", "23", "TV1", "pop", "5", ""]
                resultado = importar_avaliacoes(self.escrever_csv([invalida, valida]))
                self.assertEqual([a.id_resposta for a in resultado.avaliacoes], ["SIM-02"])
                self.assertEqual(len(resultado.erros), 1)
                self.assertEqual(resultado.erros[0].linha, 2)
                self.assertIn(campo, resultado.erros[0].motivo)

    def test_hu01_ca04_rejeita_id_repetido_sem_sobrescrever_primeiro(self):
        """HU01-CA04: mantém a primeira ocorrência válida de cada ID."""
        caminho = self.escrever_csv([
            ["SIM-01", "2026-10-30T19:00:00", "23", "TV1", "rock", "5", "pop"],
            ["SIM-01", "2026-10-30T20:00:00", "23", "TV1", "rock", "1", "pop"],
        ])
        resultado = importar_avaliacoes(caminho)
        self.assertEqual(len(resultado.avaliacoes), 1)
        self.assertEqual(resultado.avaliacoes[0].nota_conteudo, 5)
        self.assertEqual(len(resultado.erros), 1)
        self.assertEqual(resultado.erros[0].linha, 3)
        self.assertIn("id_resposta", resultado.erros[0].motivo)
        caminho = self.escrever_csv([
            ["SIM-02", "2026-10-30T19:00:00", "23", "TV1", "rock", "0", "pop"],
            ["SIM-02", "2026-10-30T20:00:00", "23", "TV1", "rock", "5", "pop"],
        ])
        resultado = importar_avaliacoes(caminho)
        self.assertEqual([a.id_resposta for a in resultado.avaliacoes], ["SIM-02"])
        self.assertEqual(resultado.avaliacoes[0].nota_conteudo, 5)
        self.assertEqual(len(resultado.erros), 1)
        self.assertEqual(resultado.erros[0].linha, 2)
        self.assertIn("nota_conteudo", resultado.erros[0].motivo)


class TestHU02Filtros(unittest.TestCase):
    def test_hu02_ca01_periodo_inclui_inicio_e_exclui_fim(self):
        """HU02-CA01: o início entra, o fim não, e a lista original não muda."""
        dados = [
            avaliacao("antes", "2026-10-23T23:59:59"),
            avaliacao("inicio", "2026-10-24T00:00:00"),
            avaliacao("dentro", "2026-10-24T23:59:59"),
            avaliacao("fim", "2026-10-25T00:00:00"),
        ]
        original = list(dados)
        saida = filtrar_avaliacoes(dados, inicio=datetime(2026, 10, 24), fim=datetime(2026, 10, 25))
        self.assertEqual([a.id_resposta for a in saida], ["inicio", "dentro"])
        self.assertEqual(dados, original)
        self.assertEqual(filtrar_avaliacoes(dados), dados)
        self.assertEqual(
            [a.id_resposta for a in filtrar_avaliacoes(dados, inicio=datetime(2026, 10, 24))],
            ["inicio", "dentro", "fim"],
        )
        self.assertEqual(
            [a.id_resposta for a in filtrar_avaliacoes(dados, fim=datetime(2026, 10, 25))],
            ["antes", "inicio", "dentro"],
        )

    def test_hu02_ca02_filtra_dia_da_semana_em_datas_diferentes(self):
        """HU02-CA02: sábado=5 seleciona sábados de semanas distintas."""
        dados = [
            avaliacao("sabado1", "2026-10-24T19:00:00"),
            avaliacao("sexta", "2026-10-30T19:00:00"),
            avaliacao("sabado2", "2026-10-31T19:00:00"),
        ]
        saida = filtrar_avaliacoes(dados, dia_semana=5)
        self.assertEqual([a.id_resposta for a in saida], ["sabado1", "sabado2"])

    def test_hu02_ca03_combina_periodo_dia_horario_e_tv(self):
        """HU02-CA03: combina todos os filtros, e o limite de cima fica de fora."""
        dados = [
            avaliacao("antes_hora", "2026-10-30T18:59:59"),
            avaliacao("aceita", "2026-10-30T19:00:00"),
            avaliacao("outra_tv", "2026-10-30T19:30:00", tv_id="TV2"),
            avaliacao("fim_hora", "2026-10-30T20:00:00"),
            avaliacao("outro_dia", "2026-10-31T19:00:00"),
            avaliacao("fora_periodo", "2026-11-06T19:00:00"),
        ]
        saida = filtrar_avaliacoes(
            dados, inicio=datetime(2026, 10, 30), fim=datetime(2026, 11, 1),
            dia_semana=4, hora_inicio=19, hora_fim=20, tv_id="TV1",
        )
        self.assertEqual([a.id_resposta for a in saida], ["aceita"])

    def test_hu02_ca04_trata_vazio_e_rejeita_parametros_invalidos(self):
        """HU02-CA04: vazio é válido, mas parâmetros inválidos geram ValueError."""
        self.assertEqual(filtrar_avaliacoes([], tv_id="TV1"), [])
        self.assertEqual(filtrar_avaliacoes([avaliacao()], tv_id="TV9"), [])
        casos = [
            {"inicio": datetime(2026, 10, 31), "fim": datetime(2026, 10, 30)},
            {"inicio": datetime(2026, 10, 30), "fim": datetime(2026, 10, 30)},
            {"dia_semana": 7}, {"dia_semana": -1},
            {"hora_inicio": -1}, {"hora_fim": 25},
            {"hora_inicio": 20, "hora_fim": 19},
            {"hora_inicio": 20, "hora_fim": 20},
            {"hora_inicio": 19.5},
        ]
        for parametros in casos:
            with self.subTest(parametros=parametros), self.assertRaises(ValueError):
                filtrar_avaliacoes([], **parametros)


class TestHU03Indicadores(unittest.TestCase):
    def test_hu03_ca01_calcula_quantidade_e_media_por_conteudo(self):
        """HU03-CA01: usa todas as notas de cada conteúdo, sem misturar conteúdos."""
        dados = [
            avaliacao("1", conteudo="rock", nota=5),
            avaliacao("2", conteudo="pop", nota=2),
            avaliacao("3", conteudo="rock", nota=4),
            avaliacao("4", conteudo="rock", nota=4),
        ]
        resultado = calcular_indicadores(dados)
        grupos = {g.conteudo: g for g in resultado.conteudos}
        self.assertEqual(resultado.total_avaliacoes, 4)
        self.assertEqual(set(grupos), {"rock", "pop"})
        self.assertEqual(grupos["rock"].qtd_avaliacoes, 3)
        self.assertAlmostEqual(grupos["rock"].nota_media, 13 / 3)
        self.assertEqual(grupos["pop"].qtd_avaliacoes, 1)
        self.assertAlmostEqual(grupos["pop"].nota_media, 2.0)

    def test_hu03_ca02_aceitacao_considera_apenas_notas_quatro_e_cinco(self):
        """HU03-CA02: duas notas aceitas entre cinco correspondem a 40%."""
        dados = [avaliacao(str(nota), nota=nota) for nota in range(1, 6)]
        resultado = calcular_indicadores(dados)
        self.assertEqual(len(resultado.conteudos), 1)
        self.assertAlmostEqual(resultado.conteudos[0].taxa_aceitacao, 40.0)

    def test_hu03_ca03_conta_preferencias_separadamente_das_notas(self):
        """HU03-CA03: preferência por conteúdo não exibido também é contada."""
        dados = [
            avaliacao("1", nota=1, preferencia="pop"),
            avaliacao("2", nota=5, preferencia="pop"),
            avaliacao("3", nota=3, preferencia="sertanejo"),
            avaliacao("4", nota=3, preferencia=None),
        ]
        resultado = calcular_indicadores(dados)
        self.assertEqual(resultado.preferencias, {"pop": 2, "sertanejo": 1})
        self.assertEqual([g.conteudo for g in resultado.conteudos], ["rock"])
        self.assertAlmostEqual(resultado.conteudos[0].nota_media, 3.0)

    def test_hu03_ca04_sem_avaliacoes_nao_inventa_notas_ou_grupos(self):
        """HU03-CA04: sem avaliações, devolve tudo vazio e não divide por zero."""
        resultado = calcular_indicadores([])
        self.assertEqual(resultado.total_avaliacoes, 0)
        self.assertEqual(resultado.conteudos, [])
        self.assertEqual(resultado.preferencias, {})


class TestHU04Recomendacao(unittest.TestCase):
    def test_hu04_ca01_exige_amostra_minima_inclusiva(self):
        """HU04-CA01: quatro avaliações não bastam e cinco já são elegíveis."""
        indicadores = Indicadores(9, [
            ResumoConteudo("rock", 4, 5.0, 100.0),
            ResumoConteudo("pop", 5, 4.0, 80.0),
        ], {"rock": 8, "pop": 1})
        resultado = gerar_recomendacao(indicadores)
        self.assertEqual(resultado.status, "recomendado")
        self.assertEqual(resultado.min_avaliacoes, 5)
        self.assertEqual(resultado.conteudo, "pop")
        self.assertEqual([g.conteudo for g in resultado.ranking], ["pop"])

    def test_hu04_ca02_ordena_por_aceitacao_preferencia_e_nome(self):
        """HU04-CA02: desempata sempre do mesmo jeito: aceitação, preferências e nome."""
        indicadores = Indicadores(30, [
            ResumoConteudo("rock", 10, 4.0, 80.0),
            ResumoConteudo("sertanejo", 10, 4.0, 80.0),
            ResumoConteudo("pop", 5, 4.0, 80.0),
            ResumoConteudo("futebol", 5, 5.0, 100.0),
        ], {"rock": 2, "sertanejo": 3, "pop": 3})
        resultado = gerar_recomendacao(indicadores)
        self.assertEqual(resultado.conteudo, "futebol")
        self.assertEqual(
            [g.conteudo for g in resultado.ranking],
            ["futebol", "pop", "sertanejo", "rock"],
        )

    def test_hu04_ca03_informa_dados_insuficientes_sem_escolha(self):
        """HU04-CA03: sem conteúdo elegível, não recomenda nada."""
        casos = [
            Indicadores(0, [], {}),
            Indicadores(4, [ResumoConteudo("rock", 4, 5.0, 100.0)], {"pop": 4}),
        ]
        for indicadores in casos:
            with self.subTest(total=indicadores.total_avaliacoes):
                resultado = gerar_recomendacao(indicadores)
                self.assertEqual(resultado.status, "dados_insuficientes")
                self.assertIsNone(resultado.conteudo)
                self.assertEqual(resultado.ranking, [])
                self.assertEqual(resultado.min_avaliacoes, 5)

    def test_hu04_ca04_minimo_configuravel_deve_ser_inteiro_positivo(self):
        """HU04-CA04: aceita outro mínimo e recusa valores inválidos."""
        indicadores = Indicadores(3, [ResumoConteudo("rock", 3, 5.0, 100.0)], {})
        resultado = gerar_recomendacao(indicadores, min_avaliacoes=3)
        self.assertEqual(resultado.conteudo, "rock")
        self.assertEqual(resultado.min_avaliacoes, 3)
        for minimo in [0, -1, 2.5, "5", False]:
            with self.subTest(minimo=minimo), self.assertRaises(ValueError):
                gerar_recomendacao(indicadores, min_avaliacoes=minimo)


class TestHU05Exportacao(ArquivosTemporarios):
    def preparar_resultados(self):
        pop = ResumoConteudo("pop", 5, 4.2, 80.0)
        rock = ResumoConteudo("rock", 5, 3.6, 60.0)
        basquete = ResumoConteudo("basquete", 1, 5.0, 100.0)
        indicadores = Indicadores(11, [pop, rock, basquete], {"pop": 7, "rock": 4})
        recomendacao = Recomendacao("recomendado", "pop", 5, [pop, rock])
        return indicadores, recomendacao

    def test_hu05_ca01_exporta_json_com_indicadores_e_recomendacao(self):
        """HU05-CA01: o JSON guarda os números como números, os conteúdos e a recomendação."""
        indicadores, recomendacao = self.preparar_resultados()
        destino_json = self.pasta / "relatorio.json"
        destino_csv = self.pasta / "ranking.csv"
        exportar_relatorio(indicadores, recomendacao, destino_json, destino_csv)
        documento = json.loads(destino_json.read_text(encoding="utf-8"))
        self.assertEqual(documento["total_avaliacoes"], 11)
        self.assertEqual(documento["preferencias"], {"pop": 7, "rock": 4})
        grupos = {g["conteudo"]: g for g in documento["conteudos"]}
        self.assertEqual(set(grupos), {"pop", "rock", "basquete"})
        self.assertEqual(grupos["pop"]["qtd_avaliacoes"], 5)
        self.assertAlmostEqual(grupos["pop"]["nota_media"], 4.2)
        self.assertAlmostEqual(grupos["pop"]["taxa_aceitacao"], 80.0)
        self.assertEqual(documento["recomendacao"]["status"], "recomendado")
        self.assertEqual(documento["recomendacao"]["conteudo"], "pop")
        self.assertEqual(documento["recomendacao"]["min_avaliacoes"], 5)
        self.assertEqual(documento["ranking"], ["pop", "rock"])

    def test_hu05_ca02_exporta_csv_na_ordem_do_ranking(self):
        """HU05-CA02: CSV usa ';', seis colunas e apenas conteúdos elegíveis."""
        indicadores, recomendacao = self.preparar_resultados()
        destino_json = self.pasta / "relatorio.json"
        destino_csv = self.pasta / "ranking.csv"
        exportar_relatorio(indicadores, recomendacao, destino_json, destino_csv)
        with destino_csv.open(encoding="utf-8", newline="") as arquivo:
            leitor = csv.DictReader(arquivo, delimiter=";")
            self.assertEqual(tuple(leitor.fieldnames), CABECALHO_SAIDA)
            linhas = list(leitor)
        self.assertEqual([r["conteudo"] for r in linhas], ["pop", "rock"])
        self.assertEqual([r["posicao"] for r in linhas], ["1", "2"])
        self.assertEqual(linhas[0]["qtd_avaliacoes"], "5")
        self.assertAlmostEqual(float(linhas[0]["nota_media"]), 4.2)
        self.assertAlmostEqual(float(linhas[0]["taxa_aceitacao"]), 80.0)
        self.assertEqual(linhas[0]["votos_preferencia"], "7")

    def test_hu05_ca03_nao_sobrescreve_destinos_existentes(self):
        """HU05-CA03: confere os dois destinos antes de escrever qualquer arquivo."""
        indicadores, recomendacao = self.preparar_resultados()
        for extensao in ["json", "csv"]:
            with self.subTest(existente=extensao):
                destino_json = self.pasta / f"relatorio_{extensao}.json"
                destino_csv = self.pasta / f"ranking_{extensao}.csv"
                existente = destino_json if extensao == "json" else destino_csv
                outro = destino_csv if extensao == "json" else destino_json
                existente.write_text("CONTEUDO ANTERIOR", encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    exportar_relatorio(indicadores, recomendacao, destino_json, destino_csv)
                self.assertEqual(existente.read_text(encoding="utf-8"), "CONTEUDO ANTERIOR")
                self.assertFalse(outro.exists())

    def test_hu05_ca04_exporta_resultado_vazio_sem_inventar_ranking(self):
        """HU05-CA04: JSON válido e CSV só com cabeçalho quando não há dados."""
        destino_json = self.pasta / "vazio.json"
        destino_csv = self.pasta / "vazio.csv"
        exportar_relatorio(
            Indicadores(0, [], {}),
            Recomendacao("dados_insuficientes", None, 5, []),
            destino_json, destino_csv,
        )
        documento = json.loads(destino_json.read_text(encoding="utf-8"))
        self.assertEqual(documento["total_avaliacoes"], 0)
        self.assertEqual(documento["conteudos"], [])
        self.assertEqual(documento["preferencias"], {})
        self.assertEqual(documento["recomendacao"]["status"], "dados_insuficientes")
        self.assertIsNone(documento["recomendacao"]["conteudo"])
        self.assertEqual(documento["recomendacao"]["min_avaliacoes"], 5)
        self.assertEqual(documento["ranking"], [])
        with destino_csv.open(encoding="utf-8", newline="") as arquivo:
            linhas = list(csv.reader(arquivo, delimiter=";"))
        self.assertEqual(linhas, [list(CABECALHO_SAIDA)])


if __name__ == "__main__":
    unittest.main(verbosity=2)