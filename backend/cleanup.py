import psycopg2

DATABASE_URL = "postgresql://postgres.zjcaucxnkysyrhuwaevv:kcxEqsOdtmrrqNTj@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres?sslmode=require"

def cleanup():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("Dropping job_status from all schemas...")
    cur.execute("""
        SELECT n.nspname, t.typname 
        FROM pg_type t 
        JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace 
        WHERE t.typname = 'job_status';
    """)
    types = cur.fetchall()
    for schema, typname in types:
        print(f"Dropping enum {schema}.{typname}")
        cur.execute(f"DROP TYPE IF EXISTS {schema}.{typname} CASCADE;")
        
    print("Dropping alembic_version table just in case...")
    cur.execute("DROP TABLE IF EXISTS alembic_version CASCADE;")

    print("Cleanup complete!")
    cur.close()
    conn.close()

if __name__ == "__main__":
    cleanup()
