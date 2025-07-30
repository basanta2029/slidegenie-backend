"""
Unit of Work pattern implementation for transactional operations.
"""
from typing import Type, TypeVar, Generic

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.base import AsyncSessionLocal
from app.repositories.base import BaseRepository
from app.repositories.user import UserRepository
from app.repositories.presentation import PresentationRepository
from app.repositories.slide import SlideRepository
from app.repositories.reference import ReferenceRepository
from app.repositories.template import TemplateRepository
from app.repositories.generation_job import GenerationJobRepository

T = TypeVar("T")


class UnitOfWork:
    """
    Unit of Work pattern for managing database transactions.
    
    Ensures all repository operations within a unit are committed together
    or rolled back on failure.
    """
    
    def __init__(self):
        self._session: AsyncSession | None = None
        
        # Repository instances
        self._users: UserRepository | None = None
        self._presentations: PresentationRepository | None = None
        self._slides: SlideRepository | None = None
        self._references: ReferenceRepository | None = None
        self._templates: TemplateRepository | None = None
        self._generation_jobs: GenerationJobRepository | None = None
    
    async def __aenter__(self):
        """Enter the context manager."""
        self._session = AsyncSessionLocal()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        await self._session.close()
    
    async def commit(self):
        """Commit the transaction."""
        if self._session:
            await self._session.commit()
    
    async def rollback(self):
        """Rollback the transaction."""
        if self._session:
            await self._session.rollback()
    
    async def refresh(self, instance):
        """Refresh an instance from the database."""
        if self._session:
            await self._session.refresh(instance)
    
    @property
    def session(self) -> AsyncSession:
        """Get the current session."""
        if not self._session:
            raise RuntimeError("UnitOfWork must be used within a context manager")
        return self._session
    
    @property
    def users(self) -> UserRepository:
        """Get user repository."""
        if not self._users:
            self._users = UserRepository(self.session)
        return self._users
    
    @property
    def presentations(self) -> PresentationRepository:
        """Get presentation repository."""
        if not self._presentations:
            self._presentations = PresentationRepository(self.session)
        return self._presentations
    
    @property
    def slides(self) -> SlideRepository:
        """Get slide repository."""
        if not self._slides:
            self._slides = SlideRepository(self.session)
        return self._slides
    
    @property
    def references(self) -> ReferenceRepository:
        """Get reference repository."""
        if not self._references:
            self._references = ReferenceRepository(self.session)
        return self._references
    
    @property
    def templates(self) -> TemplateRepository:
        """Get template repository."""
        if not self._templates:
            self._templates = TemplateRepository(self.session)
        return self._templates
    
    @property
    def generation_jobs(self) -> GenerationJobRepository:
        """Get generation job repository."""
        if not self._generation_jobs:
            self._generation_jobs = GenerationJobRepository(self.session)
        return self._generation_jobs
    
    def repository(self, repo_class: Type[BaseRepository[T]]) -> BaseRepository[T]:
        """
        Get a custom repository instance.
        
        Args:
            repo_class: Repository class
            
        Returns:
            Repository instance
        """
        return repo_class(self.session)


class ReadOnlyUnitOfWork(UnitOfWork):
    """
    Read-only Unit of Work for query operations.
    
    Automatically rolls back any changes to prevent accidental writes.
    """
    
    async def commit(self):
        """Override commit to always rollback."""
        await self.rollback()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Always rollback on exit."""
        await self.rollback()
        await self._session.close()


async def get_unit_of_work() -> UnitOfWork:
    """
    Dependency to get a Unit of Work instance.
    
    Usage in FastAPI:
        @app.post("/presentations")
        async def create_presentation(
            data: PresentationCreate,
            uow: UnitOfWork = Depends(get_unit_of_work)
        ):
            async with uow:
                presentation = await uow.presentations.create(data.dict())
                # Other operations...
                # Automatically committed on success
                return presentation
    """
    return UnitOfWork()


async def get_read_only_uow() -> ReadOnlyUnitOfWork:
    """
    Dependency to get a read-only Unit of Work instance.
    
    Usage in FastAPI:
        @app.get("/presentations")
        async def list_presentations(
            uow: ReadOnlyUnitOfWork = Depends(get_read_only_uow)
        ):
            async with uow:
                presentations = await uow.presentations.get_multi()
                return presentations
    """
    return ReadOnlyUnitOfWork()