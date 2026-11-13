#Analisador da programação das TVs do Garage Burger

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


CAMPOS_CSV = (
    "id_resposta",
    "data_hora",
    "mesa",
    "tv_id",
    "conteudo_exibido",
    "nota_conteudo",
    "preferencia",
)

CONTEUDOS_VALIDOS = frozenset(
    {"rock", "pop", "sertanejo", "futebol", "basquete"}
)

CAMPOS_RANKING_CSV = (
    "posicao",
    "conteudo",
    "qtd_avaliacoes",
    "nota_media",
    "taxa_aceitacao",
    "votos_preferencia",
)


@dataclass(frozen=True)
class Avaliacao:
    id_resposta: str
    data_hora: datetime
    mesa: str | None
    tv_id: str
    conteudo_exibido: str
    nota_conteudo: int
    preferencia: str | None = None


@dataclass(frozen=True)
class ErroImportacao:
    linha: int
    motivo: str


@dataclass
class ResultadoImportacao:
    avaliacoes: list[Avaliacao]
    erros: list[ErroImportacao]


@dataclass(frozen=True)
class ResumoConteudo:
    conteudo: str
    qtd_avaliacoes: int
    nota_media: float
    taxa_aceitacao: float


@dataclass
class Indicadores:
    total_avaliacoes: int
    conteudos: list[ResumoConteudo]
    preferencias: dict[str, int]


@dataclass
class Recomendacao:
    status: str
    conteudo: str | None
    min_avaliacoes: int
    ranking: list[ResumoConteudo]


def importar_avaliacoes(caminho: str | Path) -> ResultadoImportacao:
    """HU01: lê o CSV (UTF-8, separado por ';'), valida e normaliza cada resposta.

    Se faltar coluna no cabeçalho, dá ValueError. Uma linha com problema vira
    um erro na lista e a importação continua. Se o ID repetir, fica a primeira
    ocorrência válida e a seguinte é rejeitada.
    """
    caminho = Path(caminho)
    avaliacoes = []
    erros = []
    ids_aceitos = set()

    with caminho.open(encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")

        # Confere o cabeçalho antes de ler qualquer linha
        cabecalho = [campo.strip() for campo in (leitor.fieldnames or [])]
        faltando = [campo for campo in CAMPOS_CSV if campo not in cabecalho]
        if faltando:
            raise ValueError("Coluna(s) faltando no cabeçalho: " + ", ".join(faltando))
        leitor.fieldnames = cabecalho

        # O cabeçalho é a linha 1, então os dados começam na linha 2
        for numero_linha, linha in enumerate(leitor, start=2):
            valores = {campo: (linha.get(campo) or "").strip() for campo in CAMPOS_CSV}
            avaliacao, problema = _validar_linha(valores)

            if problema is None and avaliacao.id_resposta in ids_aceitos:
                problema = "id_resposta repetido: " + avaliacao.id_resposta

            if problema is not None:
                erros.append(ErroImportacao(numero_linha, problema))
                continue

            ids_aceitos.add(avaliacao.id_resposta)
            avaliacoes.append(avaliacao)

    return ResultadoImportacao(avaliacoes, erros)


def _validar_linha(valores):
    """Monta uma Avaliacao a partir de uma linha do CSV.

    Devolve (avaliacao, None) se a linha estiver certa, ou (None, motivo)
    com o nome do campo que deu problema.
    """
    if not valores["id_resposta"]:
        return None, "id_resposta vazio"

    try:
        data_hora = datetime.strptime(valores["data_hora"], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None, "data_hora inválida: " + valores["data_hora"]

    if not valores["tv_id"]:
        return None, "tv_id vazio"

    conteudo = valores["conteudo_exibido"].lower()
    if conteudo not in CONTEUDOS_VALIDOS:
        return None, "conteudo_exibido desconhecido: " + valores["conteudo_exibido"]

    try:
        nota = int(valores["nota_conteudo"])
    except ValueError:
        return None, "nota_conteudo inválida: " + valores["nota_conteudo"]
    if nota < 1 or nota > 5:
        return None, "nota_conteudo fora de 1 a 5: " + valores["nota_conteudo"]

    preferencia = valores["preferencia"].lower() or None
    if preferencia is not None and preferencia not in CONTEUDOS_VALIDOS:
        return None, "preferencia desconhecida: " + valores["preferencia"]

    avaliacao = Avaliacao(
        id_resposta=valores["id_resposta"],
        data_hora=data_hora,
        mesa=valores["mesa"] or None,
        tv_id=valores["tv_id"],
        conteudo_exibido=conteudo,
        nota_conteudo=nota,
        preferencia=preferencia,
    )
    return avaliacao, None


def _eh_inteiro(valor):
    # bool também é int em Python, então precisa ser excluído
    return isinstance(valor, int) and not isinstance(valor, bool)


def filtrar_avaliacoes(
    avaliacoes: list[Avaliacao],
    *,
    inicio: datetime | None = None,
    fim: datetime | None = None,
    dia_semana: int | None = None,
    hora_inicio: int = 0,
    hora_fim: int = 24,
    tv_id: str | None = None,
) -> list[Avaliacao]:
    """HU02: aplica os filtros juntos e mantém a ordem das respostas.

    O início entra e o fim não (inicio <= data_hora < fim), e o mesmo vale
    para as horas. Dia da semana: segunda = 0 até domingo = 6. Filtro com
    None é ignorado. Faixa que passa da meia-noite não funciona nesta versão.
    """
    # Valida os parâmetros antes de tudo, mesmo se a lista estiver vazia
    if inicio is not None and fim is not None and inicio >= fim:
        raise ValueError("O início do período precisa ser antes do fim")
    if dia_semana is not None and (not _eh_inteiro(dia_semana) or not 0 <= dia_semana <= 6):
        raise ValueError("dia_semana precisa ser um inteiro de 0 (segunda) a 6 (domingo)")
    if not _eh_inteiro(hora_inicio) or not _eh_inteiro(hora_fim):
        raise ValueError("hora_inicio e hora_fim precisam ser inteiros")
    if not 0 <= hora_inicio < hora_fim <= 24:
        raise ValueError("A faixa de horário precisa seguir 0 <= hora_inicio < hora_fim <= 24")

    selecionadas = []
    for avaliacao in avaliacoes:
        momento = avaliacao.data_hora
        if inicio is not None and momento < inicio:
            continue
        if fim is not None and momento >= fim:
            continue
        if dia_semana is not None and momento.weekday() != dia_semana:
            continue
        if not hora_inicio <= momento.hour < hora_fim:
            continue
        if tv_id is not None and avaliacao.tv_id != tv_id:
            continue
        selecionadas.append(avaliacao)
    return selecionadas


def calcular_indicadores(avaliacoes: list[Avaliacao]) -> Indicadores:
    """HU03: agrupa as avaliações por conteúdo e conta as preferências separado.

    Aceitação = 100 * (notas 4 ou 5) / avaliações do conteúdo.
    A preferência não muda a nota do conteúdo que estava passando.
    """
    notas_por_conteudo = {}   # conteudo -> lista de notas, na ordem em que aparecem
    preferencias = {}

    for avaliacao in avaliacoes:
        notas_por_conteudo.setdefault(avaliacao.conteudo_exibido, []).append(avaliacao.nota_conteudo)
        if avaliacao.preferencia is not None:
            preferencias[avaliacao.preferencia] = preferencias.get(avaliacao.preferencia, 0) + 1

    resumos = []
    for conteudo, notas in notas_por_conteudo.items():
        quantidade = len(notas)
        aceitas = len([nota for nota in notas if nota >= 4])
        resumos.append(ResumoConteudo(
            conteudo=conteudo,
            qtd_avaliacoes=quantidade,
            nota_media=sum(notas) / quantidade,
            taxa_aceitacao=100 * aceitas / quantidade,
        ))

    return Indicadores(len(avaliacoes), resumos, preferencias)


def gerar_recomendacao(
    indicadores: Indicadores, *, min_avaliacoes: int = 5
) -> Recomendacao:
    """HU04: recomenda só conteúdos que atingiram o mínimo de avaliações.

    Ordem: maior aceitação, depois mais preferências, depois nome em ordem
    alfabética. Se ninguém atingir o mínimo, o status é 'dados_insuficientes',
    sem conteúdo e com ranking vazio.
    """
    if not _eh_inteiro(min_avaliacoes) or min_avaliacoes <= 0:
        raise ValueError("min_avaliacoes precisa ser um inteiro positivo")

    elegiveis = [r for r in indicadores.conteudos if r.qtd_avaliacoes >= min_avaliacoes]

    # Maior aceitação primeiro; empate: mais preferências; depois ordem alfabética
    def criterio_ordem(resumo):
        votos = indicadores.preferencias.get(resumo.conteudo, 0)
        return (-resumo.taxa_aceitacao, -votos, resumo.conteudo)

    ranking = sorted(elegiveis, key=criterio_ordem)

    if not ranking:
        return Recomendacao("dados_insuficientes", None, min_avaliacoes, [])
    return Recomendacao("recomendado", ranking[0].conteudo, min_avaliacoes, ranking)


def exportar_relatorio(
    indicadores: Indicadores,
    recomendacao: Recomendacao,
    caminho_json: str | Path,
    caminho_csv: str | Path,
) -> None:
    """HU05: salva os indicadores em JSON e o ranking em CSV.

    Os dois arquivos ficam em UTF-8, e o CSV usa ';' com as colunas de
    CAMPOS_RANKING_CSV. Se algum dos destinos já existir, dá FileExistsError
    antes de escrever qualquer coisa.
    """
    caminho_json = Path(caminho_json)
    caminho_csv = Path(caminho_csv)

    # Confere os dois destinos antes de escrever, para não deixar só um pronto
    for destino in (caminho_json, caminho_csv):
        if destino.exists():
            raise FileExistsError(f"O arquivo {destino} já existe")

    relatorio = {
        "total_avaliacoes": indicadores.total_avaliacoes,
        "conteudos": [
            {
                "conteudo": r.conteudo,
                "qtd_avaliacoes": r.qtd_avaliacoes,
                "nota_media": r.nota_media,
                "taxa_aceitacao": r.taxa_aceitacao,
            }
            for r in indicadores.conteudos
        ],
        "preferencias": indicadores.preferencias,
        "recomendacao": {
            "status": recomendacao.status,
            "conteudo": recomendacao.conteudo,
            "min_avaliacoes": recomendacao.min_avaliacoes,
        },
        "ranking": [r.conteudo for r in recomendacao.ranking],
    }
    with caminho_json.open("w", encoding="utf-8") as arquivo:
        json.dump(relatorio, arquivo, ensure_ascii=False, indent=2)

    with caminho_csv.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(CAMPOS_RANKING_CSV)
        for posicao, r in enumerate(recomendacao.ranking, start=1):
            escritor.writerow([
                posicao,
                r.conteudo,
                r.qtd_avaliacoes,
                r.nota_media,
                r.taxa_aceitacao,
                indicadores.preferencias.get(r.conteudo, 0),
            ])

# ---------------------------------------------------------------------------
# Execução pelo terminal (demonstração das histórias)
# ---------------------------------------------------------------------------

DIAS_DA_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _ler_argumentos():
    parser = argparse.ArgumentParser(
        description="Analisa as avaliações das TVs do Garage Burger e recomenda o que passar."
    )
    parser.add_argument("arquivo", help="CSV com as respostas do formulário")
    parser.add_argument("--inicio", help="data inicial, AAAA-MM-DD (entra no período)")
    parser.add_argument("--fim", help="data final, AAAA-MM-DD (não entra no período)")
    parser.add_argument("--dia", type=int, help="dia da semana: 0=segunda ... 6=domingo")
    parser.add_argument("--hora-inicio", type=int, default=0, help="hora inicial da faixa (padrão 0)")
    parser.add_argument("--hora-fim", type=int, default=24, help="hora final da faixa, sem incluir (padrão 24)")
    parser.add_argument("--tv", help="analisar só uma TV, por exemplo TV1")
    parser.add_argument("--minimo", type=int, default=5, help="mínimo de avaliações para recomendar (padrão 5)")
    parser.add_argument("--saida", help="nome base dos arquivos de saída (gera NOME.json e NOME.csv)")
    return parser.parse_args()


def _descrever_recorte(args):
    partes = []
    if args.inicio or args.fim:
        partes.append(f"período {args.inicio or '...'} até {args.fim or '...'}")
    if args.dia is not None and 0 <= args.dia <= 6:
        partes.append(DIAS_DA_SEMANA[args.dia])
    if args.hora_inicio != 0 or args.hora_fim != 24:
        partes.append(f"das {args.hora_inicio}h às {args.hora_fim}h")
    if args.tv:
        partes.append(args.tv)
    return ", ".join(partes) if partes else "todas as respostas"


def main():
    args = _ler_argumentos()
    print("=== Garage Burger - análise da programação das TVs ===\n")

    try:
        # HU01 - importar e validar
        resultado = importar_avaliacoes(args.arquivo)
        print(f"Arquivo: {args.arquivo}")
        print(f"Respostas aceitas: {len(resultado.avaliacoes)} | linhas recusadas: {len(resultado.erros)}")
        for erro in resultado.erros:
            print(f"  - linha {erro.linha}: {erro.motivo}")

        # HU02 - filtrar o recorte
        inicio = datetime.fromisoformat(args.inicio) if args.inicio else None
        fim = datetime.fromisoformat(args.fim) if args.fim else None
        selecionadas = filtrar_avaliacoes(
            resultado.avaliacoes,
            inicio=inicio,
            fim=fim,
            dia_semana=args.dia,
            hora_inicio=args.hora_inicio,
            hora_fim=args.hora_fim,
            tv_id=args.tv,
        )
        print(f"\nRecorte: {_descrever_recorte(args)}")
        print(f"Respostas no recorte: {len(selecionadas)}\n")

        # HU03 - indicadores
        indicadores = calcular_indicadores(selecionadas)
        if indicadores.conteudos:
            print(f"{'Conteúdo':<12}{'Avaliações':>11}{'Média':>8}{'Aceitação':>11}{'Preferências':>14}")
            for r in indicadores.conteudos:
                votos = indicadores.preferencias.get(r.conteudo, 0)
                print(f"{r.conteudo:<12}{r.qtd_avaliacoes:>11}{r.nota_media:>8.2f}"
                      f"{r.taxa_aceitacao:>10.1f}%{votos:>14}")
        else:
            print("Nenhuma avaliação nesse recorte.")

        # HU04 - recomendação
        recomendacao = gerar_recomendacao(indicadores, min_avaliacoes=args.minimo)
        print(f"\nRecomendação (mínimo de {recomendacao.min_avaliacoes} avaliações): ", end="")
        if recomendacao.status == "recomendado":
            print(recomendacao.conteudo.upper())
            ranking = "  ".join(f"{i}. {r.conteudo}" for i, r in enumerate(recomendacao.ranking, start=1))
            print(f"Ranking: {ranking}")
        else:
            print("dados insuficientes, nenhum conteúdo atingiu o mínimo.")

        # HU05 - exportar
        if args.saida:
            caminho_json = Path(args.saida + ".json")
            caminho_csv = Path(args.saida + ".csv")
            exportar_relatorio(indicadores, recomendacao, caminho_json, caminho_csv)
            print(f"\nRelatório salvo em {caminho_json} e {caminho_csv}")

    except FileNotFoundError:
        print(f"Arquivo não encontrado: {args.arquivo}")
        raise SystemExit(1)
    except (ValueError, FileExistsError) as erro:
        print(f"\nErro: {erro}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()