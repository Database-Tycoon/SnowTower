import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv('/Users/ssciortino/Projects/snowtower-workspace/snowtower-cli/.env')

# Test if INFORMATION_SCHEMA works in Python/stored procedure context
conn = snowflake.connector.connect(
    account=os.getenv('SNOWFLAKE_ACCOUNT'),
    user=os.getenv('SNOWFLAKE_USER'),
    password=os.getenv('SNOWFLAKE_PASSWORD'),
    role='ACCOUNTADMIN',
    warehouse='ADMIN'
)

cursor = conn.cursor()

# Test queries
queries = [
    "SELECT CURRENT_USER()",
    "SELECT COUNT(*) FROM SNOWFLAKE.INFORMATION_SCHEMA.DATABASES",
    "SELECT COUNT(*) FROM SNOWFLAKE.INFORMATION_SCHEMA.APPLICABLE_ROLES"
]

for query in queries:
    try:
        cursor.execute(query)
        result = cursor.fetchone()
        print(f"✅ {query[:50]}... -> Result: {result}")
    except Exception as e:
        print(f"❌ {query[:50]}... -> Error: {e}")

cursor.close()
conn.close()
