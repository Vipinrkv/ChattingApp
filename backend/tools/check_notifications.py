import asyncio
import configparser
import asyncpg

async def main():
    cfg = configparser.ConfigParser()
    cfg.read('alembic.ini')
    url = cfg['alembic']['sqlalchemy.url']
    # alembic.ini uses postgresql+asyncpg:// — asyncpg accepts postgresql://
    conn_str = url.replace('postgresql+asyncpg://', 'postgresql://')
    try:
        conn = await asyncpg.connect(conn_str)
    except Exception as e:
        print('connect_error:', e)
        return
    try:
        row = await conn.fetchval("SELECT to_regclass('public.notifications')")
        print('notifications_table_exists:', bool(row))
    except Exception as e:
        print('query_error:', e)
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
