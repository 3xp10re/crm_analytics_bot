import sqlglot

from sqlglot import exp

FORBIDDEN_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Command,
)


def validate_sql(sql: str) -> str:
    if not sql or not sql.strip():
        raise ValueError("SQL-запрос пустой.")

    try:
        statements = sqlglot.parse(sql, read="postgres",)

    except sqlglot.errors.ParseError as error:
        raise ValueError(
            "Модель вернула синтаксически некорректный SQL."
        ) from error

    if len(statements) != 1:
        raise ValueError(
            "Разрешён только один SQL-запрос."
        )

    statement = statements[0]

    if not isinstance(statement, exp.Query):
        raise ValueError(
            "Разрешены только SELECT-запросы."
        )

    for forbidden_type in FORBIDDEN_TYPES:
        if statement.find(forbidden_type):
            raise ValueError(f"Запрещённая SQL-операция: "
                             f"{forbidden_type.__name__}")

    return sql.strip()