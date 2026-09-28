import sqlite3
import asyncio
from datetime import datetime
from database.engine import async_session_factory, init_db
from database.models import User, Payment, DailyStat

def parse_date(date_str):
    if not date_str:
        return None
    try:
        # SQLite stores dates as text, convert them to a format PostgreSQL understands
        return datetime.fromisoformat(date_str.replace(" ", "T"))
    except Exception:
        return datetime.now()

async def migrate():
    # 1. Create empty tables in the new PostgreSQL database
    print("[INFO] Creating tables in PostgreSQL...")
    await init_db()

    # 2. Connect to the old SQLite database
    print("[INFO] Connecting to local SQLite database (bot.db)...")
    conn = sqlite3.connect("bot.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    async with async_session_factory() as session:
        # Migrate users
        print("[INFO] Migrating users...")
        cursor.execute("SELECT * FROM users")
        users_count = 0
        for row in cursor.fetchall():
            row_dict = dict(row)
            del row_dict['id'] # Remove old ID so Postgres generates new ones correctly
            row_dict.pop('free_analyses', None)
            row_dict['created_at'] = parse_date(row_dict.get('created_at'))
            row_dict['updated_at'] = parse_date(row_dict.get('updated_at'))
            session.add(User(**row_dict))
            users_count += 1
        print(f"[OK] Queued {users_count} users for migration.")

        # Migrate payments
        print("[INFO] Migrating payments...")
        cursor.execute("SELECT * FROM payments")
        payments_count = 0
        for row in cursor.fetchall():
            row_dict = dict(row)
            del row_dict['id']
            row_dict['created_at'] = parse_date(row_dict.get('created_at'))
            session.add(Payment(**row_dict))
            payments_count += 1
        print(f"[OK] Queued {payments_count} payments for migration.")

        # Migrate daily stats
        print("[INFO] Migrating daily statistics...")
        cursor.execute("SELECT * FROM daily_stats")
        stats_count = 0
        for row in cursor.fetchall():
            session.add(DailyStat(**dict(row)))
            stats_count += 1
        print(f"[OK] Queued {stats_count} daily stat records for migration.")

        # Save all data to the new database
        print("[INFO] Committing changes to PostgreSQL. Please wait...")
        await session.commit()
    
    print("[SUCCESS] All data has been successfully migrated!")
    conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())