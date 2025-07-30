"""
Search indexer for document processing system.

Provides Elasticsearch integration with full-text search, faceted search,
and advanced querying capabilities for processed documents.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID

from elasticsearch import AsyncElasticsearch, ConnectionError, NotFoundError
from pydantic import BaseModel, Field

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class SearchConfig(BaseModel):
    """Search configuration settings."""
    elasticsearch_host: str = Field(default="localhost")
    elasticsearch_port: int = Field(default=9200)
    elasticsearch_scheme: str = Field(default="http")
    elasticsearch_user: Optional[str] = None
    elasticsearch_password: Optional[str] = None
    
    # Index settings
    index_prefix: str = Field(default="slidegenie")
    document_index: str = Field(default="documents")
    content_index: str = Field(default="content")
    
    # Search settings
    default_size: int = Field(default=20)
    max_size: int = Field(default=100)
    highlight_fragment_size: int = Field(default=150)
    highlight_fragments: int = Field(default=3)
    
    # Performance settings
    refresh_interval: str = Field(default="1s")
    number_of_shards: int = Field(default=1)
    number_of_replicas: int = Field(default=0)
    max_result_window: int = Field(default=10000)


class SearchMetrics(BaseModel):
    """Search system metrics."""
    total_documents: int = 0
    index_size_mb: float = 0.0
    search_count_24h: int = 0
    avg_search_time_ms: float = 0.0
    popular_queries: List[Tuple[str, int]] = Field(default_factory=list)
    index_health: str = "unknown"  # green, yellow, red
    last_optimization: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_documents": self.total_documents,
            "index_size_mb": round(self.index_size_mb, 2),
            "search_count_24h": self.search_count_24h,
            "avg_search_time_ms": round(self.avg_search_time_ms, 2),
            "popular_queries": self.popular_queries[:10],  # Top 10
            "index_health": self.index_health,
            "last_optimization": self.last_optimization.isoformat() if self.last_optimization else None
        }


class DocumentIndex(BaseModel):
    """Document index entry."""
    file_id: str
    user_id: str
    filename: str
    content_type: str
    title: Optional[str] = None
    content: str
    extracted_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    language: str = "en"
    
    # Processed fields
    entities: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)
    
    # Academic fields
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    doi: Optional[str] = None
    publication_year: Optional[int] = None
    journal: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Elasticsearch document."""
        return {
            "file_id": self.file_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "title": self.title,
            "content": self.content,
            "extracted_text": self.extracted_text,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "size_bytes": self.size_bytes,
            "language": self.language,
            "entities": self.entities,
            "keywords": self.keywords,
            "citations": self.citations,
            "sections": self.sections,
            "authors": self.authors,
            "abstract": self.abstract,
            "doi": self.doi,
            "publication_year": self.publication_year,
            "journal": self.journal
        }


class SearchQuery(BaseModel):
    """Search query configuration."""
    query: str
    user_id: Optional[UUID] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    sort: List[Dict[str, str]] = Field(default_factory=list)
    size: int = 20
    from_: int = Field(default=0, alias="from")
    highlight: bool = True
    facets: List[str] = Field(default_factory=list)
    boost_fields: Dict[str, float] = Field(default_factory=dict)
    
    def to_elasticsearch_query(self) -> Dict[str, Any]:
        """Convert to Elasticsearch query DSL."""
        # Build the main query
        if not self.query or self.query.strip() == "*":
            # Match all query
            query_clause = {"match_all": {}}
        else:
            # Multi-match query with field boosting
            fields = ["title^3", "content^2", "extracted_text", "keywords^2", "tags^1.5"]
            
            # Apply custom boosts
            if self.boost_fields:
                for field, boost in self.boost_fields.items():
                    # Update or add field with boost
                    field_with_boost = f"{field}^{boost}"
                    fields = [f if not f.startswith(field) else field_with_boost for f in fields]
                    if not any(f.startswith(field) for f in fields):
                        fields.append(field_with_boost)
            
            query_clause = {
                "multi_match": {
                    "query": self.query,
                    "fields": fields,
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "operator": "or"
                }
            }
        
        # Build filters
        filter_clauses = []
        
        # User access filter
        if self.user_id:
            filter_clauses.append({
                "term": {"user_id": str(self.user_id)}
            })
        
        # Additional filters
        for field, value in self.filters.items():
            if isinstance(value, list):
                filter_clauses.append({
                    "terms": {field: value}
                })
            elif isinstance(value, dict):
                if "range" in value:
                    filter_clauses.append({
                        "range": {field: value["range"]}
                    })
                elif "exists" in value:
                    filter_clauses.append({
                        "exists": {"field": field}
                    })
            else:
                filter_clauses.append({
                    "term": {field: value}
                })
        
        # Combine query and filters
        if filter_clauses:
            query = {
                "bool": {
                    "must": [query_clause],
                    "filter": filter_clauses
                }
            }
        else:
            query = query_clause
        
        # Build full search request
        search_body = {
            "query": query,
            "size": min(self.size, 100),  # Cap at 100
            "from": self.from_,
            "_source": {
                "excludes": ["content", "extracted_text"]  # Exclude large fields by default
            }
        }
        
        # Add sorting
        if self.sort:
            search_body["sort"] = self.sort
        else:
            # Default sort by relevance then date
            search_body["sort"] = [
                "_score",
                {"created_at": {"order": "desc"}}
            ]
        
        # Add highlighting
        if self.highlight:
            search_body["highlight"] = {
                "fields": {
                    "title": {"fragment_size": 150, "number_of_fragments": 1},
                    "content": {"fragment_size": 150, "number_of_fragments": 3},
                    "extracted_text": {"fragment_size": 150, "number_of_fragments": 3}
                },
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"]
            }
        
        # Add aggregations for facets
        if self.facets:
            aggregations = {}
            for facet in self.facets:
                if facet == "content_type":
                    aggregations["content_types"] = {
                        "terms": {"field": "content_type.keyword", "size": 10}
                    }
                elif facet == "tags":
                    aggregations["tags"] = {
                        "terms": {"field": "tags", "size": 20}
                    }
                elif facet == "authors":
                    aggregations["authors"] = {
                        "terms": {"field": "authors.keyword", "size": 10}
                    }
                elif facet == "publication_year":
                    aggregations["publication_years"] = {
                        "date_histogram": {
                            "field": "publication_year",
                            "calendar_interval": "year",
                            "format": "yyyy"
                        }
                    }
                elif facet == "date_range":
                    aggregations["date_ranges"] = {
                        "date_range": {
                            "field": "created_at",
                            "ranges": [
                                {"key": "last_7_days", "from": "now-7d"},
                                {"key": "last_30_days", "from": "now-30d"},
                                {"key": "last_year", "from": "now-1y"},
                                {"key": "older", "to": "now-1y"}
                            ]
                        }
                    }
            
            if aggregations:
                search_body["aggs"] = aggregations
        
        return search_body


class SearchIndexer:
    """
    Elasticsearch-based search indexer for documents.
    
    Features:
    - Full-text search with ranking
    - Faceted search and filtering
    - Academic document support
    - Auto-completion and suggestions
    - Search analytics and monitoring
    - Index optimization and maintenance
    """
    
    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self.es_client: Optional[AsyncElasticsearch] = None
        self.metrics = SearchMetrics()
        self._search_queries: List[Tuple[datetime, str, float]] = []  # (timestamp, query, duration)
        self._query_counts: Dict[str, int] = {}
        
        # Index names
        self.document_index = f"{self.config.index_prefix}_{self.config.document_index}"
        self.content_index = f"{self.config.index_prefix}_{self.config.content_index}"
        
        logger.info("SearchIndexer initialized")
    
    async def initialize(self) -> None:
        """Initialize Elasticsearch connection and indices."""
        try:
            # Create Elasticsearch client
            self.es_client = AsyncElasticsearch(
                hosts=[{
                    "host": self.config.elasticsearch_host,
                    "port": self.config.elasticsearch_port,
                    "scheme": self.config.elasticsearch_scheme
                }],
                http_auth=(
                    (self.config.elasticsearch_user, self.config.elasticsearch_password)
                    if self.config.elasticsearch_user else None
                ),
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            await self.es_client.ping()
            
            # Create indices if they don't exist
            await self._create_indices()
            
            # Update metrics
            await self._update_metrics()
            
            logger.info("Search indexer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize search indexer: {e}")
            raise
    
    async def index_document(
        self,
        file_id: str,
        content: str,
        filename: str,
        user_id: UUID,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Index a document for search.
        
        Args:
            file_id: Document file ID
            content: Document content
            filename: Original filename
            user_id: User ID
            metadata: Additional metadata
            
        Returns:
            True if indexed successfully
        """
        if not self.es_client:
            logger.error("Elasticsearch client not initialized")
            return False
        
        try:
            # Extract metadata
            meta = metadata or {}
            
            # Create document index entry
            doc = DocumentIndex(
                file_id=file_id,
                user_id=str(user_id),
                filename=filename,
                content_type=meta.get("content_type", "unknown"),
                title=meta.get("title", filename),
                content=content,
                extracted_text=content,  # Could be different if processed
                metadata=meta,
                tags=meta.get("tags", []),
                size_bytes=len(content.encode('utf-8')),
                language=meta.get("language", "en"),
                
                # Extracted entities (would come from processing)
                entities=meta.get("entities", []),
                keywords=meta.get("keywords", []),
                citations=meta.get("citations", []),
                sections=meta.get("sections", []),
                
                # Academic fields
                authors=meta.get("authors", []),
                abstract=meta.get("abstract"),
                doi=meta.get("doi"),
                publication_year=meta.get("publication_year"),
                journal=meta.get("journal")
            )
            
            # Index the document
            response = await self.es_client.index(
                index=self.document_index,
                id=file_id,
                document=doc.to_dict(),
                refresh=True  # Make immediately searchable
            )
            
            logger.info(f"Document indexed: {file_id} (result: {response['result']})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index document {file_id}: {e}")
            return False
    
    async def search(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
        facets: Optional[List[str]] = None,
        sort: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Search documents with advanced querying.
        
        Args:
            query: Search query string
            user_id: User ID for access control
            filters: Additional filters
            limit: Maximum results
            offset: Result offset
            facets: Facets to include
            sort: Sort configuration
            
        Returns:
            Search results with facets and metadata
        """
        if not self.es_client:
            logger.error("Elasticsearch client not initialized")
            return {"documents": [], "total": 0, "facets": {}}
        
        start_time = datetime.utcnow()
        
        try:
            # Build search query
            search_query = SearchQuery(
                query=query,
                user_id=user_id,
                filters=filters or {},
                size=min(limit, self.config.max_size),
                from_=offset,
                facets=facets or [],
                sort=sort or []
            )
            
            # Execute search
            search_body = search_query.to_elasticsearch_query()
            response = await self.es_client.search(
                index=self.document_index,
                body=search_body
            )
            
            # Process results
            results = {
                "documents": [],
                "total": response["hits"]["total"]["value"],
                "max_score": response["hits"]["max_score"],
                "took_ms": response["took"],
                "facets": {},
                "query": query
            }
            
            # Process document hits
            for hit in response["hits"]["hits"]:
                doc_result = {
                    "file_id": hit["_id"],
                    "score": hit["_score"],
                    **hit["_source"]
                }
                
                # Add highlights
                if "highlight" in hit:
                    doc_result["highlights"] = hit["highlight"]
                
                results["documents"].append(doc_result)
            
            # Process aggregations (facets)
            if "aggregations" in response:
                aggs = response["aggregations"]
                
                for facet_name, facet_data in aggs.items():
                    if "buckets" in facet_data:
                        results["facets"][facet_name] = [
                            {"key": bucket["key"], "count": bucket["doc_count"]}
                            for bucket in facet_data["buckets"]
                        ]
            
            # Track search metrics
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._search_queries.append((datetime.utcnow(), query, duration_ms))
            
            # Update query counts
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            self._query_counts[query_hash] = self._query_counts.get(query_hash, 0) + 1
            
            # Clean old search queries (keep last 1000)
            if len(self._search_queries) > 1000:
                self._search_queries = self._search_queries[-500:]
            
            logger.info(f"Search completed: '{query}' -> {results['total']} results in {duration_ms:.2f}ms")
            return results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return {"documents": [], "total": 0, "facets": {}, "error": str(e)}
    
    async def suggest(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        limit: int = 5
    ) -> List[str]:
        """Get search suggestions based on partial query."""
        if not self.es_client or len(query.strip()) < 2:
            return []
        
        try:
            # Use completion suggester or term suggester
            suggest_body = {
                "suggest": {
                    "title_suggest": {
                        "prefix": query,
                        "completion": {
                            "field": "title.suggest",
                            "size": limit
                        }
                    },
                    "content_suggest": {
                        "text": query,
                        "term": {
                            "field": "content",
                            "size": limit
                        }
                    }
                }
            }
            
            if user_id:
                suggest_body["suggest"]["title_suggest"]["completion"]["contexts"] = {
                    "user_id": [str(user_id)]
                }
            
            response = await self.es_client.search(
                index=self.document_index,
                body=suggest_body
            )
            
            suggestions = []
            
            # Process completion suggestions
            for option in response["suggest"]["title_suggest"][0]["options"]:
                suggestions.append(option["text"])
            
            # Process term suggestions
            for option in response["suggest"]["content_suggest"][0]["options"]:
                suggestions.append(option["text"])
            
            # Remove duplicates and limit
            unique_suggestions = list(dict.fromkeys(suggestions))
            return unique_suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Suggestion failed for query '{query}': {e}")
            return []
    
    async def update_document(
        self,
        file_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update specific fields of an indexed document."""
        if not self.es_client:
            logger.error("Elasticsearch client not initialized")
            return False
        
        try:
            # Add updated timestamp
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            response = await self.es_client.update(
                index=self.document_index,
                id=file_id,
                body={"doc": updates},
                refresh=True
            )
            
            logger.info(f"Document updated: {file_id} (result: {response['result']})")
            return True
            
        except NotFoundError:
            logger.warning(f"Document not found for update: {file_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to update document {file_id}: {e}")
            return False
    
    async def delete_document(self, file_id: str) -> bool:
        """Delete a document from the search index."""
        if not self.es_client:
            logger.error("Elasticsearch client not initialized")
            return False
        
        try:
            response = await self.es_client.delete(
                index=self.document_index,
                id=file_id,
                refresh=True
            )
            
            logger.info(f"Document deleted from index: {file_id}")
            return True
            
        except NotFoundError:
            logger.warning(f"Document not found for deletion: {file_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete document {file_id}: {e}")
            return False
    
    async def bulk_index(self, documents: List[DocumentIndex]) -> Dict[str, Any]:
        """Index multiple documents in a single operation."""
        if not self.es_client or not documents:
            return {"indexed": 0, "errors": []}
        
        try:
            # Prepare bulk operations
            operations = []
            for doc in documents:
                operations.extend([
                    {"index": {"_index": self.document_index, "_id": doc.file_id}},
                    doc.to_dict()
                ])
            
            # Execute bulk operation
            response = await self.es_client.bulk(
                body=operations,
                refresh=True
            )
            
            # Process results
            indexed_count = 0
            errors = []
            
            for item in response["items"]:
                if "index" in item:
                    result = item["index"]
                    if result.get("status") in [200, 201]:
                        indexed_count += 1
                    else:
                        errors.append({
                            "id": result["_id"],
                            "error": result.get("error", "Unknown error")
                        })
            
            logger.info(f"Bulk index completed: {indexed_count}/{len(documents)} documents indexed")
            
            return {
                "indexed": indexed_count,
                "total": len(documents),
                "errors": errors,
                "took_ms": response["took"]
            }
            
        except Exception as e:
            logger.error(f"Bulk index failed: {e}")
            return {"indexed": 0, "errors": [{"error": str(e)}]}
    
    async def optimize_index(self) -> Dict[str, Any]:
        """Optimize the search index for better performance."""
        if not self.es_client:
            return {"status": "failed", "error": "Elasticsearch not initialized"}
        
        try:
            start_time = datetime.utcnow()
            
            # Force merge to optimize segments
            merge_response = await self.es_client.indices.forcemerge(
                index=self.document_index,
                max_num_segments=1,
                wait_for_completion=True
            )
            
            # Refresh the index
            await self.es_client.indices.refresh(index=self.document_index)
            
            # Update settings for better search performance
            await self.es_client.indices.put_settings(
                index=self.document_index,
                body={
                    "index": {
                        "refresh_interval": self.config.refresh_interval,
                        "max_result_window": self.config.max_result_window
                    }
                }
            )
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.metrics.last_optimization = datetime.utcnow()
            
            logger.info(f"Index optimization completed in {duration_ms:.2f}ms")
            
            return {
                "status": "completed",
                "duration_ms": duration_ms,
                "shards": merge_response.get("_shards", {})
            }
            
        except Exception as e:
            logger.error(f"Index optimization failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive search metrics."""
        await self._update_metrics()
        return self.metrics.to_dict()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform search system health check."""
        health_status = {
            "status": "healthy",
            "elasticsearch_connected": False,
            "index_exists": False,
            "cluster_health": "unknown",
            "issues": []
        }
        
        try:
            if not self.es_client:
                health_status["status"] = "critical"
                health_status["issues"].append("Elasticsearch client not initialized")
                return health_status
            
            # Test connection
            await self.es_client.ping()
            health_status["elasticsearch_connected"] = True
            
            # Check cluster health
            cluster_health = await self.es_client.cluster.health()
            health_status["cluster_health"] = cluster_health["status"]
            
            if cluster_health["status"] == "red":
                health_status["status"] = "critical"
                health_status["issues"].append("Cluster health is red")
            elif cluster_health["status"] == "yellow":
                health_status["status"] = "warning"
                health_status["issues"].append("Cluster health is yellow")
            
            # Check if index exists
            index_exists = await self.es_client.indices.exists(index=self.document_index)
            health_status["index_exists"] = index_exists
            
            if not index_exists:
                health_status["status"] = "critical"
                health_status["issues"].append("Document index does not exist")
            
            # Check index stats
            if index_exists:
                stats = await self.es_client.indices.stats(index=self.document_index)
                index_stats = stats["indices"][self.document_index]
                
                # Check if index is too large or has issues
                total_size_mb = index_stats["total"]["store"]["size_in_bytes"] / (1024 * 1024)
                if total_size_mb > 1000:  # > 1GB
                    health_status["status"] = "warning"
                    health_status["issues"].append("Index size is large")
            
            return health_status
            
        except Exception as e:
            logger.error(f"Search health check failed: {e}")
            return {
                "status": "critical",
                "elasticsearch_connected": False,
                "error": str(e),
                "issues": ["Health check failed"]
            }
    
    # Private helper methods
    
    async def _create_indices(self) -> None:
        """Create Elasticsearch indices with proper mappings."""
        document_mapping = {
            "mappings": {
                "properties": {
                    "file_id": {"type": "keyword"},
                    "user_id": {"type": "keyword"},
                    "filename": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "content_type": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {
                                "type": "completion",
                                "contexts": [
                                    {"name": "user_id", "type": "category"}
                                ]
                            }
                        }
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "extracted_text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "metadata": {"type": "object"},
                    "tags": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "size_bytes": {"type": "long"},
                    "language": {"type": "keyword"},
                    "entities": {"type": "keyword"},
                    "keywords": {"type": "keyword"},
                    "citations": {"type": "text"},
                    "sections": {"type": "keyword"},
                    "authors": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "abstract": {"type": "text"},
                    "doi": {"type": "keyword"},
                    "publication_year": {"type": "integer"},
                    "journal": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    }
                }
            },
            "settings": {
                "number_of_shards": self.config.number_of_shards,
                "number_of_replicas": self.config.number_of_replicas,
                "refresh_interval": self.config.refresh_interval,
                "max_result_window": self.config.max_result_window,
                "analysis": {
                    "analyzer": {
                        "academic_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "stop",
                                "snowball"
                            ]
                        }
                    }
                }
            }
        }
        
        # Create document index
        if not await self.es_client.indices.exists(index=self.document_index):
            await self.es_client.indices.create(
                index=self.document_index,
                body=document_mapping
            )
            logger.info(f"Created document index: {self.document_index}")
    
    async def _update_metrics(self) -> None:
        """Update search metrics."""
        if not self.es_client:
            return
        
        try:
            # Get index stats
            stats = await self.es_client.indices.stats(index=self.document_index)
            index_stats = stats["indices"].get(self.document_index, {})
            
            # Update document count and size
            self.metrics.total_documents = index_stats.get("total", {}).get("docs", {}).get("count", 0)
            size_bytes = index_stats.get("total", {}).get("store", {}).get("size_in_bytes", 0)
            self.metrics.index_size_mb = size_bytes / (1024 * 1024)
            
            # Calculate search metrics from recent queries
            recent_queries = [
                q for q in self._search_queries
                if q[0] > datetime.utcnow() - timedelta(hours=24)
            ]
            
            self.metrics.search_count_24h = len(recent_queries)
            
            if recent_queries:
                self.metrics.avg_search_time_ms = sum(q[2] for q in recent_queries) / len(recent_queries)
            
            # Popular queries
            self.metrics.popular_queries = sorted(
                self._query_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Get cluster health
            health = await self.es_client.cluster.health()
            self.metrics.index_health = health["status"]
            
        except Exception as e:
            logger.error(f"Failed to update search metrics: {e}")
            self.metrics.index_health = "unknown"