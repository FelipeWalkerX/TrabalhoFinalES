#Analisador da programação das TVs do Garage Burger

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
    raise NotImplementedError("HU01: implementação prevista para a Sprint 3")


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
    raise NotImplementedError("HU02: implementação prevista para a Sprint 3")


def calcular_indicadores(avaliacoes: list[Avaliacao]) -> Indicadores:
    """HU03: agrupa as avaliações por conteúdo e conta as preferências separado.

    Aceitação = 100 * (notas 4 ou 5) / avaliações do conteúdo.
    A preferência não muda a nota do conteúdo que estava passando.
    """
    raise NotImplementedError("HU03: implementação prevista para a Sprint 3")


def gerar_recomendacao(
    indicadores: Indicadores, *, min_avaliacoes: int = 5
) -> Recomendacao:
    """HU04: recomenda só conteúdos que atingiram o mínimo de avaliações.

    Ordem: maior aceitação, depois mais preferências, depois nome em ordem
    alfabética. Se ninguém atingir o mínimo, o status é 'dados_insuficientes',
    sem conteúdo e com ranking vazio.
    """
    raise NotImplementedError("HU04: implementação prevista para a Sprint 3")


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
    raise NotImplementedError("HU05: implementação prevista para a Sprint 3")