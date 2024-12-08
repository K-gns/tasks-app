# app/db.py
from databases import Database

DATABASE_URL = "postgresql+asyncpg://postgres:1159@db/tasks"

# Подключение через databases для асинхронного доступа
database = Database(DATABASE_URL)

async def create_tables():
    create_table_query = """
    CREATE TABLE IF NOT EXISTS task_results (
        task_id SERIAL PRIMARY KEY,
        status VARCHAR(50),
        result TEXT
    );
    """
    # Выполняем запрос для создания таблицы
    await database.execute(create_table_query)