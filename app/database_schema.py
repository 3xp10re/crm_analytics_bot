from app.database import get_connection

def get_database_schema() -> str:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
        SELECT
            c.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable
        FROM information_schema.columns AS c
        WHERE c.table_schema = 'pechi'
          AND c.table_name LIKE 'amocrm_%'
        ORDER BY
            c.table_name,
            c.ordinal_position"""
            )

            columns = cursor.fetchall()
            print("Количество колонок:", len(columns))

        tables: dict[str, list[str]] = {}

        for column in columns:
            table_name = column["table_name"]

            column_description = (
            f"- {column['column_name']}: "
            f"{column['data_type']}, "
            f"nullable={column['is_nullable']}"
        )

            tables.setdefault(table_name, []).append(column_description)

    schema_parts = []

    for table_name, table_columns in tables.items():
        schema_parts.append(
            f"Table: {table_name}\n"
            + "\n".join(table_columns)
        )

    relationships = """
Relationships:
- amocrm_leads.status_id -> amocrm_statuses.id
- amocrm_leads.pipeline_id -> amocrm_pipelines.id
- amocrm_statuses.pipeline_id -> amocrm_pipelines.id
- amocrm_leads.responsible_user_id -> amocrm_users.id
"""

    return "\n\n".join(schema_parts) + "\n\n" + relationships