"""
Generation job repository implementation.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import GenerationJob
from app.repositories.base import BaseRepository


class GenerationJobRepository(BaseRepository[GenerationJob]):
    """Repository for generation job data access."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(GenerationJob, db)
    
    async def get_pending_jobs(
        self,
        limit: int = 10,
    ) -> List[GenerationJob]:
        """
        Get pending jobs ordered by priority and queue time.
        
        Args:
            limit: Maximum jobs to return
            
        Returns:
            List of pending jobs
        """
        stmt = (
            select(GenerationJob)
            .where(
                and_(
                    GenerationJob.status == 'pending',
                    GenerationJob.deleted_at.is_(None)
                )
            )
            .order_by(
                GenerationJob.priority.desc(),
                GenerationJob.queued_at
            )
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars())
    
    async def get_user_jobs(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[GenerationJob], int]:
        """
        Get jobs for a specific user.
        
        Args:
            user_id: User ID
            status: Filter by status
            limit: Maximum results
            offset: Results offset
            
        Returns:
            Tuple of (jobs, total_count)
        """
        conditions = [
            GenerationJob.user_id == user_id,
            GenerationJob.deleted_at.is_(None)
        ]
        
        if status:
            conditions.append(GenerationJob.status == status)
        
        base_stmt = select(GenerationJob).where(and_(*conditions))
        
        # Count total
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total_count = total_result.scalar() or 0
        
        # Get results
        stmt = (
            base_stmt
            .order_by(GenerationJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(stmt)
        jobs = list(result.scalars())
        
        return jobs, total_count
    
    async def start_job(
        self,
        job_id: UUID,
    ) -> Optional[GenerationJob]:
        """
        Mark job as started.
        
        Args:
            job_id: Job ID
            
        Returns:
            Updated job or None
        """
        return await self.update(
            job_id,
            {
                'status': 'processing',
                'started_at': datetime.now(timezone.utc)
            }
        )
    
    async def complete_job(
        self,
        job_id: UUID,
        result_data: Dict[str, Any],
        presentation_id: Optional[UUID] = None,
    ) -> Optional[GenerationJob]:
        """
        Mark job as completed.
        
        Args:
            job_id: Job ID
            result_data: Result data
            presentation_id: Created presentation ID
            
        Returns:
            Updated job or None
        """
        job = await self.get(job_id)
        if not job:
            return None
        
        completed_at = datetime.now(timezone.utc)
        duration = None
        
        if job.started_at:
            duration = (completed_at - job.started_at).total_seconds()
        
        return await self.update(
            job_id,
            {
                'status': 'completed',
                'completed_at': completed_at,
                'duration_seconds': duration,
                'result_data': result_data,
                'presentation_id': presentation_id
            }
        )
    
    async def fail_job(
        self,
        job_id: UUID,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[GenerationJob]:
        """
        Mark job as failed.
        
        Args:
            job_id: Job ID
            error_message: Error message
            error_details: Additional error details
            
        Returns:
            Updated job or None
        """
        return await self.update(
            job_id,
            {
                'status': 'failed',
                'completed_at': datetime.now(timezone.utc),
                'error_message': error_message,
                'error_details': error_details or {}
            }
        )
    
    async def update_progress(
        self,
        job_id: UUID,
        step: str,
        progress: float,
        step_status: str = 'processing',
    ) -> None:
        """
        Update job processing progress.
        
        Args:
            job_id: Job ID
            step: Current step name
            progress: Progress (0.0 to 1.0)
            step_status: Step status
        """
        job = await self.get(job_id)
        if not job:
            return
        
        # Update processing steps
        steps = job.processing_steps or []
        
        # Find or create step
        step_found = False
        for s in steps:
            if s['step'] == step:
                s['status'] = step_status
                s['progress'] = progress
                if step_status == 'completed':
                    s['duration_ms'] = s.get('duration_ms', 0)
                step_found = True
                break
        
        if not step_found:
            steps.append({
                'step': step,
                'status': step_status,
                'progress': progress,
                'started_at': datetime.now(timezone.utc).isoformat()
            })
        
        await self.update(
            job_id,
            {'processing_steps': steps}
        )
    
    async def get_job_statistics(
        self,
        user_id: Optional[UUID] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get job statistics.
        
        Args:
            user_id: Filter by user
            days: Number of days to look back
            
        Returns:
            Statistics dictionary
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        conditions = [
            GenerationJob.created_at >= cutoff_date,
            GenerationJob.deleted_at.is_(None)
        ]
        
        if user_id:
            conditions.append(GenerationJob.user_id == user_id)
        
        # Status counts
        status_query = (
            select(
                GenerationJob.status,
                func.count(GenerationJob.id).label('count')
            )
            .where(and_(*conditions))
            .group_by(GenerationJob.status)
        )
        
        status_result = await self.db.execute(status_query)
        status_counts = {row.status: row.count for row in status_result}
        
        # Average processing time
        time_query = (
            select(
                func.avg(GenerationJob.duration_seconds).label('avg_duration'),
                func.min(GenerationJob.duration_seconds).label('min_duration'),
                func.max(GenerationJob.duration_seconds).label('max_duration'),
            )
            .where(
                and_(
                    *conditions,
                    GenerationJob.status == 'completed',
                    GenerationJob.duration_seconds.isnot(None)
                )
            )
        )
        
        time_result = await self.db.execute(time_query)
        time_row = time_result.one()
        
        # Model usage
        model_query = (
            select(
                GenerationJob.ai_model_used,
                func.count(GenerationJob.id).label('count')
            )
            .where(
                and_(
                    *conditions,
                    GenerationJob.ai_model_used.isnot(None)
                )
            )
            .group_by(GenerationJob.ai_model_used)
        )
        
        model_result = await self.db.execute(model_query)
        model_usage = {row.ai_model_used: row.count for row in model_result}
        
        return {
            'total_jobs': sum(status_counts.values()),
            'status_counts': status_counts,
            'success_rate': (
                status_counts.get('completed', 0) / 
                max(sum(status_counts.values()), 1) * 100
            ),
            'average_duration_seconds': time_row.avg_duration,
            'min_duration_seconds': time_row.min_duration,
            'max_duration_seconds': time_row.max_duration,
            'model_usage': model_usage,
            'period_days': days,
        }
    
    async def cleanup_old_jobs(
        self,
        days: int = 90,
    ) -> int:
        """
        Clean up old completed/failed jobs.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of jobs cleaned up
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Count jobs to delete
        count_query = (
            select(func.count(GenerationJob.id))
            .where(
                and_(
                    GenerationJob.status.in_(['completed', 'failed']),
                    GenerationJob.created_at < cutoff_date,
                    GenerationJob.deleted_at.is_(None)
                )
            )
        )
        
        result = await self.db.execute(count_query)
        count = result.scalar() or 0
        
        if count > 0:
            # Soft delete old jobs
            update_stmt = (
                update(GenerationJob)
                .where(
                    and_(
                        GenerationJob.status.in_(['completed', 'failed']),
                        GenerationJob.created_at < cutoff_date,
                        GenerationJob.deleted_at.is_(None)
                    )
                )
                .values(deleted_at=datetime.now(timezone.utc))
            )
            
            await self.db.execute(update_stmt)
        
        return count


# Import additional required modules
from datetime import timedelta
from sqlalchemy import update