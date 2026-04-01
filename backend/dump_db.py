import sqlite3
import os

db_path = 'finance.db'

if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

dump_content = "-- SQLite Database Dump\n"
dump_content += "-- Generated from finance.db\n\n"

# Получить все таблицы
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

for (table_name,) in tables:
    dump_content += f"\n-- Table: {table_name}\n"
    
    # Получить CREATE TABLE
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    create_sql = cursor.fetchone()
    if create_sql:
        dump_content += create_sql[0] + ";\n\n"
    
    # Получить данные
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if rows:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        col_names = ', '.join(columns)
        dump_content += f"-- Data ({len(rows)} rows):\n"
        for row in rows:
            values = ', '.join([f"'{v}'" if isinstance(v, str) else str(v) if v is not None else 'NULL' for v in row])
            dump_content += f"INSERT INTO {table_name} ({col_names}) VALUES ({values});\n"
    else:
        dump_content += "-- (no data)\n"
    
    dump_content += "\n"

# Записать в файл
output_file = 'dump.sql'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(dump_content)

print(f"✓ Dump created: {output_file}")
print(f"✓ Tables: {len(tables)}")

conn.close()
