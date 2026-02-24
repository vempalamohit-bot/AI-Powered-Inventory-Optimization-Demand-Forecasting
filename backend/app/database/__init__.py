from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# SQLite database - much faster than MySQL for this POC
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'inventory.db')
SQLALCHEMY_DATABASE_URL = DATABASE_URL = f"sqlite:///{db_path}"

# OPTIMIZED: SQLite connection with performance tuning
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # Needed for SQLite
        "timeout": 30  # Increase timeout for large transactions
    },
    pool_size=20,  # Increased pool size for concurrent operations
    max_overflow=40,
    pool_pre_ping=True,
    echo=False  # Disable SQL logging for performance
)

# OPTIMIZED: SQLite performance pragmas for bulk inserts
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for maximum write performance"""
    cursor = dbapi_conn.cursor()
    # CRITICAL: WAL mode for concurrent reads/writes
    cursor.execute("PRAGMA journal_mode=WAL")
    # Faster synchronization (still safe with WAL)
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Larger cache size (64MB) for better performance
    cursor.execute("PRAGMA cache_size=-64000")
    # Larger page size for bulk operations
    cursor.execute("PRAGMA page_size=8192")
    # Enable memory-mapped I/O for faster reads
    cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
    # Temp store in memory
    cursor.execute("PRAGMA temp_store=MEMORY")
    # Larger locking timeout
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
