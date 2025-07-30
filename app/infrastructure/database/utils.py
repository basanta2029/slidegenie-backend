"""
Database utilities for performance monitoring and soft delete.
"""
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type, TypeVar

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query
from sqlalchemy.pool import Pool

from app.core.logging import get_logger
from app.infrastructure.database.base import AsyncSessionLocal, engine
from app.infrastructure.database.models import TimestampMixin

logger = get_logger(__name__)

T = TypeVar("T", bound=TimestampMixin)


class QueryLogger:
    """Log slow queries for performance monitoring."""
    
    def __init__(self, slow_query_threshold_ms: float = 100):
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.query_count = 0
        self.total_time_ms = 0.0
    
    def log_query(self, query: str, duration_ms: float, params: Optional[Dict[str, Any]] = None):
        """Log query execution details."""
        self.query_count += 1
        self.total_time_ms += duration_ms
        
        if duration_ms > self.slow_query_threshold_ms:
            logger.warning(
                "Slow query detected",
                query=query[:500],  # Truncate long queries
                duration_ms=round(duration_ms, 2),
                params=params,
            )
        else:
            logger.debug(
                "Query executed",
                query=query[:200],
                duration_ms=round(duration_ms, 2),
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics."""
        return {
            "query_count": self.query_count,
            "total_time_ms": round(self.total_time_ms, 2),
            "average_time_ms": round(self.total_time_ms / max(self.query_count, 1), 2),
        }


# Global query logger instance
query_logger = QueryLogger()


# SQLAlchemy event listeners for query logging
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Store query start time."""
    conn.info.setdefault("query_start_time", []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log query execution time."""
    total = time.time() - conn.info["query_start_time"].pop(-1)
    duration_ms = total * 1000
    query_logger.log_query(statement, duration_ms, parameters)


# Connection pool event listeners
@event.listens_for(Pool, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set connection pragmas."""
    logger.info("New database connection established")


@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout from pool."""
    logger.debug("Connection checked out from pool")


class SoftDeleteMixin:
    """Mixin to add soft delete functionality to models."""
    
    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.deleted_at = datetime.now(timezone.utc)
    
    def restore(self) -> None:
        """Restore soft deleted record."""
        self.deleted_at = None
    
    @classmethod
    def filter_active(cls, query: Query) -> Query:
        """Filter out soft deleted records."""
        return query.filter(cls.deleted_at.is_(None))


class DatabaseTransaction:
    """Context manager for database transactions with automatic rollback."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._transaction = None
    
    async def __aenter__(self):
        """Begin transaction."""
        self._transaction = await self.session.begin()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Commit or rollback transaction."""
        if exc_type is not None:
            await self._transaction.rollback()
            logger.error(
                "Transaction rolled back",
                exc_type=exc_type.__name__,
                exc_val=str(exc_val),
            )
        else:
            try:
                await self._transaction.commit()
            except Exception as e:
                await self._transaction.rollback()
                logger.error(f"Transaction commit failed: {e}")
                raise


@asynccontextmanager
async def get_db_transaction():
    """
    Get database session with transaction context.
    
    Usage:
        async with get_db_transaction() as db:
            # All operations in transaction
            user = await db.get(User, user_id)
            user.name = "New Name"
            # Automatically committed on exit
    """
    async with AsyncSessionLocal() as session:
        async with DatabaseTransaction(session):
            yield session


async def bulk_insert(
    session: AsyncSession,
    model: Type[T],
    data: list[dict],
    batch_size: int = 1000,
) -> list[T]:
    """
    Bulk insert records efficiently.
    
    Args:
        session: Database session
        model: Model class
        data: List of dictionaries with record data
        batch_size: Number of records per batch
        
    Returns:
        List of created records
    """
    records = []
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        batch_records = [model(**item) for item in batch]
        
        session.add_all(batch_records)
        await session.flush()
        
        records.extend(batch_records)
        
        logger.info(
            f"Bulk inserted {len(batch_records)} {model.__name__} records",
            batch_number=i // batch_size + 1,
            total_batches=(len(data) + batch_size - 1) // batch_size,
        )
    
    return records


async def vacuum_deleted_records(
    session: AsyncSession,
    model: Type[T],
    days_old: int = 30,
) -> int:
    """
    Permanently delete soft-deleted records older than specified days.
    
    Args:
        session: Database session
        model: Model class with soft delete
        days_old: Age threshold in days
        
    Returns:
        Number of records deleted
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
    
    # Count records to delete
    count_query = text(
        f"SELECT COUNT(*) FROM {model.__tablename__} "
        f"WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff_date"
    )
    result = await session.execute(count_query, {"cutoff_date": cutoff_date})
    count = result.scalar()
    
    if count > 0:
        # Delete records
        delete_query = text(
            f"DELETE FROM {model.__tablename__} "
            f"WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff_date"
        )
        await session.execute(delete_query, {"cutoff_date": cutoff_date})
        
        logger.info(
            f"Vacuumed {count} soft-deleted {model.__name__} records",
            days_old=days_old,
            cutoff_date=cutoff_date.isoformat(),
        )
    
    return count


async def analyze_tables(session: AsyncSession) -> None:
    """
    Run ANALYZE on all tables to update PostgreSQL statistics.
    
    Args:
        session: Database session
    """
    # Get all table names
    tables_query = text(
        "SELECT tablename FROM pg_tables "
        "WHERE schemaname = 'public'"
    )
    result = await session.execute(tables_query)
    tables = [row[0] for row in result]
    
    # Analyze each table
    for table in tables:
        await session.execute(text(f"ANALYZE {table}"))
        logger.info(f"Analyzed table: {table}")


async def get_table_stats(session: AsyncSession) -> Dict[str, Dict[str, Any]]:
    """
    Get statistics for all tables.
    
    Args:
        session: Database session
        
    Returns:
        Dictionary of table statistics
    """
    stats_query = text("""
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            n_live_tup AS row_count,
            n_dead_tup AS dead_rows,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
    """)
    
    result = await session.execute(stats_query)
    
    stats = {}
    for row in result:
        stats[row.tablename] = {
            "size": row.size,
            "row_count": row.row_count,
            "dead_rows": row.dead_rows,
            "last_vacuum": row.last_vacuum,
            "last_autovacuum": row.last_autovacuum,
            "last_analyze": row.last_analyze,
            "last_autoanalyze": row.last_autoanalyze,
        }
    
    return stats


async def check_indexes_usage(session: AsyncSession) -> Dict[str, Dict[str, Any]]:
    """
    Check index usage statistics.
    
    Args:
        session: Database session
        
    Returns:
        Dictionary of index usage statistics
    """
    index_query = text("""
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_scan AS index_scans,
            idx_tup_read AS tuples_read,
            idx_tup_fetch AS tuples_fetched,
            pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        ORDER BY idx_scan ASC
    """)
    
    result = await session.execute(index_query)
    
    indexes = {}
    for row in result:
        key = f"{row.tablename}.{row.indexname}"
        indexes[key] = {
            "scans": row.index_scans,
            "tuples_read": row.tuples_read,
            "tuples_fetched": row.tuples_fetched,
            "size": row.index_size,
            "unused": row.index_scans == 0,
        }
    
    return indexes


# Import timedelta for vacuum function
from datetime import timedelta