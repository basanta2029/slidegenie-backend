"""
Example usage of the comprehensive storage system.

This example demonstrates:
1. Document storage with full processing pipeline
2. Content caching and retrieval
3. Search indexing and querying
4. File lifecycle management
5. Backup and versioning
6. Storage analytics and monitoring
"""

import asyncio
import logging
from uuid import uuid4
from pathlib import Path

from .storage_manager import StorageManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_storage_system():
    """Comprehensive demonstration of the storage system."""
    
    # Initialize the storage manager (this initializes all components)
    storage_manager = StorageManager()
    await storage_manager.initialize()
    
    print("🚀 Storage System Demonstration")
    print("=" * 50)
    
    # Sample user and document
    user_id = uuid4()
    sample_content = b"""
    # Research Paper: Advanced Document Processing
    
    ## Abstract
    This paper explores advanced techniques for document processing
    using machine learning and natural language processing.
    
    ## Introduction
    Document processing has become increasingly important...
    
    ## Methodology
    We used a combination of neural networks and traditional algorithms...
    
    ## Results
    Our experiments show significant improvements in accuracy...
    
    ## Conclusion
    The proposed approach demonstrates superior performance...
    """
    
    try:
        # 1. DOCUMENT STORAGE
        print("\n1. 📁 Storing Document")
        print("-" * 30)
        
        file_id, storage_info = await storage_manager.store_document(
            file_content=sample_content,
            filename="research_paper.pdf",
            content_type="application/pdf",
            user_id=user_id,
            metadata={
                "title": "Advanced Document Processing",
                "authors": ["Dr. Smith", "Dr. Johnson"],
                "keywords": ["document processing", "machine learning", "NLP"],
                "publication_year": 2024,
                "abstract": "This paper explores advanced techniques...",
                "doi": "10.1000/example.123456"
            }
        )
        
        print(f"✅ Document stored successfully!")
        print(f"   File ID: {file_id}")
        print(f"   Size: {storage_info['size_mb']:.2f} MB")
        print(f"   Processed: {storage_info['processed']}")
        print(f"   Indexed: {storage_info['indexed']}")
        
        # 2. USER QUOTA CHECK
        print("\n2. 📊 User Storage Quota")
        print("-" * 30)
        
        quota = await storage_manager.get_user_quota(user_id)
        print(f"   Total Limit: {quota.total_limit_mb} MB")
        print(f"   Used: {quota.used_mb:.2f} MB")
        print(f"   Available: {quota.available_mb:.2f} MB")
        print(f"   Usage: {quota.usage_percentage:.1f}%")
        print(f"   Files: {quota.file_count}/{quota.max_files}")
        
        # 3. DOCUMENT RETRIEVAL
        print("\n3. 📄 Retrieving Document")
        print("-" * 30)
        
        retrieved_doc = await storage_manager.retrieve_document(
            file_id=file_id,
            user_id=user_id,
            include_content=False  # Just metadata for demo
        )
        
        print(f"✅ Document retrieved successfully!")
        print(f"   Filename: {retrieved_doc['filename']}")
        print(f"   Content Type: {retrieved_doc['content_type']}")
        print(f"   Size: {retrieved_doc['size_mb']:.2f} MB")
        print(f"   Has processed content: {bool(retrieved_doc['processed_content'])}")
        
        # 4. SEARCH FUNCTIONALITY
        print("\n4. 🔍 Search Documents")
        print("-" * 30)
        
        search_results = await storage_manager.search_documents(
            query="machine learning document processing",
            user_id=user_id,
            facets=["content_type", "tags", "authors"],
            limit=10
        )
        
        print(f"✅ Search completed!")
        print(f"   Total results: {search_results['total']}")
        print(f"   Query time: {search_results.get('took_ms', 0)} ms")
        
        if search_results['documents']:
            doc = search_results['documents'][0]
            print(f"   Top result: {doc['filename']}")
            print(f"   Score: {doc['score']:.3f}")
            
        # Show facets
        if search_results['facets']:
            print("   Available facets:")
            for facet_name, facet_values in search_results['facets'].items():
                print(f"     {facet_name}: {len(facet_values)} options")
        
        # 5. STORAGE METRICS
        print("\n5. 📈 Storage System Metrics")
        print("-" * 30)
        
        metrics = await storage_manager.get_storage_metrics()
        print(f"   Total Files: {metrics.total_files}")
        print(f"   Total Size: {metrics.total_size_mb:.2f} MB")
        print(f"   Cache Hit Rate: {metrics.cache_hit_rate:.1%}")
        print(f"   Search Index Count: {metrics.search_index_count}")
        print(f"   Storage Health: {metrics.storage_health}")
        print(f"   Avg Response Time: {metrics.avg_response_time_ms:.2f} ms")
        print(f"   Errors (24h): {metrics.errors_last_24h}")
        
        # 6. CACHE PERFORMANCE
        print("\n6. ⚡ Cache Performance")
        print("-" * 30)
        
        cache_metrics = await storage_manager.cache_manager.get_metrics()
        print(f"   Total Keys: {cache_metrics['total_keys']}")
        print(f"   Cache Size: {cache_metrics['total_size_mb']:.2f} MB")
        print(f"   Hit Rate: {cache_metrics['hit_rate']:.1%}")
        print(f"   Hit Count: {cache_metrics['hit_count']}")
        print(f"   Miss Count: {cache_metrics['miss_count']}")
        print(f"   Avg Response: {cache_metrics['avg_response_time_ms']:.2f} ms")
        
        # 7. SEARCH INDEX METRICS
        print("\n7. 🔎 Search Index Metrics")
        print("-" * 30)
        
        search_metrics = await storage_manager.search_indexer.get_metrics()
        print(f"   Indexed Documents: {search_metrics['total_documents']}")
        print(f"   Index Size: {search_metrics['index_size_mb']:.2f} MB")
        print(f"   Searches (24h): {search_metrics['search_count_24h']}")
        print(f"   Avg Search Time: {search_metrics['avg_search_time_ms']:.2f} ms")
        print(f"   Index Health: {search_metrics['index_health']}")
        
        # 8. LIFECYCLE MANAGEMENT
        print("\n8. 🔄 File Lifecycle Management")
        print("-" * 30)
        
        lifecycle_metrics = await storage_manager.lifecycle_manager.get_metrics()
        print(f"   Active Files: {lifecycle_metrics['active_files']}")
        print(f"   Archived Files: {lifecycle_metrics['archived_files']}")
        print(f"   Soft Deleted: {lifecycle_metrics['soft_deleted_files']}")
        print(f"   Temp Files: {lifecycle_metrics['temp_files']}")
        print(f"   Oldest File: {lifecycle_metrics['oldest_file_days']:.1f} days")
        
        # Get file status
        file_status = await storage_manager.lifecycle_manager.get_file_status(file_id)
        if file_status:
            print(f"   Our file age: {file_status['age_days']:.1f} days")
            print(f"   File status: {file_status['status']}")
        
        # 9. BACKUP SYSTEM
        print("\n9. 💾 Backup System")
        print("-" * 30)
        
        backup_metrics = await storage_manager.backup_manager.get_metrics()
        print(f"   Total Backups: {backup_metrics['total_backups']}")
        print(f"   Successful: {backup_metrics['successful_backups']}")
        print(f"   Failed: {backup_metrics['failed_backups']}")
        print(f"   Success Rate: {backup_metrics['backup_success_rate']:.1%}")
        print(f"   Total Backup Size: {backup_metrics['total_backup_size_mb']:.2f} MB")
        print(f"   Avg Backup Time: {backup_metrics['average_backup_time_seconds']:.2f}s")
        
        # 10. ACCESS LOGS
        print("\n10. 📝 Access Logs")
        print("-" * 30)
        
        access_logs = await storage_manager.get_access_logs(
            user_id=user_id,
            limit=5
        )
        
        print(f"   Recent access events: {len(access_logs)}")
        for log in access_logs[:3]:
            timestamp = log['timestamp'].strftime("%H:%M:%S")
            operation = log['operation']
            success = "✅" if log['success'] else "❌"
            print(f"   {timestamp} - {operation} {success}")
        
        # 11. TEMPORARY FILE DEMO
        print("\n11. 📁 Temporary Files")
        print("-" * 30)
        
        temp_id, temp_path = await storage_manager.lifecycle_manager.create_temp_file(
            content=b"This is temporary content for processing",
            suffix=".tmp",
            prefix="demo_"
        )
        
        print(f"✅ Created temporary file: {temp_path.name}")
        print(f"   Temp ID: {temp_id}")
        print(f"   Path: {temp_path}")
        
        # Clean up temp file
        await storage_manager.lifecycle_manager.cleanup_temp_file(temp_id)
        print(f"✅ Cleaned up temporary file")
        
        # 12. SYSTEM MAINTENANCE
        print("\n12. 🔧 System Maintenance")
        print("-" * 30)
        
        maintenance_result = await storage_manager.run_maintenance()
        print(f"   Status: {maintenance_result['status']}")
        print(f"   Timestamp: {maintenance_result['timestamp']}")
        
        if maintenance_result['status'] == 'completed':
            results = maintenance_result['results']
            print("   Maintenance tasks completed:")
            for task, result in results.items():
                if isinstance(result, dict) and 'cleaned' in result:
                    print(f"     {task}: cleaned {result.get('cleaned', 0)} items")
                else:
                    print(f"     {task}: {result}")
        
        # 13. HEALTH CHECKS
        print("\n13. 🏥 System Health Checks")
        print("-" * 30)
        
        # Overall storage health
        overall_metrics = await storage_manager.get_storage_metrics()
        print(f"   Overall Health: {overall_metrics.storage_health}")
        
        # Component health checks
        components = [
            ("Cache", storage_manager.cache_manager),
            ("Search", storage_manager.search_indexer),
            ("Lifecycle", storage_manager.lifecycle_manager),
            ("Backup", storage_manager.backup_manager)
        ]
        
        for name, component in components:
            try:
                health = await component.health_check()
                status = health.get('status', 'unknown')
                issues = len(health.get('issues', []))
                print(f"   {name}: {status} ({issues} issues)")
            except Exception as e:
                print(f"   {name}: error - {e}")
        
        # 14. SOFT DELETE DEMO
        print("\n14. 🗑️  Soft Delete Demo")
        print("-" * 30)
        
        # Mark for deletion
        await storage_manager.lifecycle_manager.mark_for_deletion(file_id, user_id)
        print("✅ File marked for deletion")
        
        # Check status
        file_status = await storage_manager.lifecycle_manager.get_file_status(file_id)
        if file_status:
            print(f"   Status: {file_status['status']}")
        
        # Restore file
        restored = await storage_manager.lifecycle_manager.restore_file(file_id, user_id)
        if restored:
            print("✅ File restored from soft delete")
        
        # 15. FINAL CLEANUP
        print("\n15. 🧹 Cleanup")
        print("-" * 30)
        
        # Delete the document (permanent)
        deleted = await storage_manager.delete_document(
            file_id=file_id,
            user_id=user_id,
            permanent=True
        )
        
        if deleted:
            print("✅ Document permanently deleted")
        
        # Final quota check
        final_quota = await storage_manager.get_user_quota(user_id)
        print(f"   Final usage: {final_quota.used_mb:.2f} MB")
        print(f"   Files: {final_quota.file_count}")
        
        print("\n🎉 Storage System Demonstration Complete!")
        print("=" * 50)
        
        # Summary
        print("\n📋 SYSTEM CAPABILITIES DEMONSTRATED:")
        print("   ✅ Document storage with metadata")
        print("   ✅ Content processing and caching")
        print("   ✅ Full-text search with facets")
        print("   ✅ Storage quota management")
        print("   ✅ File lifecycle tracking")
        print("   ✅ Backup and versioning")
        print("   ✅ Temporary file management")
        print("   ✅ Access logging and auditing")
        print("   ✅ System health monitoring")
        print("   ✅ Automated maintenance")
        print("   ✅ Performance analytics")
        print("   ✅ Soft delete and recovery")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        print(f"\n❌ Error: {e}")


async def performance_test():
    """Performance test with multiple documents."""
    
    print("\n🚀 Performance Test")
    print("=" * 30)
    
    storage_manager = StorageManager()
    await storage_manager.initialize()
    
    user_id = uuid4()
    num_documents = 10
    
    print(f"Storing {num_documents} documents...")
    
    import time
    start_time = time.time()
    
    file_ids = []
    for i in range(num_documents):
        content = f"Document {i} content with some text to process and index for search."
        
        file_id, _ = await storage_manager.store_document(
            file_content=content.encode(),
            filename=f"document_{i}.txt",
            content_type="text/plain",
            user_id=user_id,
            metadata={"document_number": i, "category": "test"}
        )
        
        file_ids.append(file_id)
    
    storage_time = time.time() - start_time
    print(f"✅ Stored {num_documents} documents in {storage_time:.2f}s")
    print(f"   Average: {storage_time / num_documents:.3f}s per document")
    
    # Test search performance
    start_time = time.time()
    search_results = await storage_manager.search_documents(
        query="document content text",
        user_id=user_id,
        limit=20
    )
    search_time = time.time() - start_time
    
    print(f"✅ Search completed in {search_time:.3f}s")
    print(f"   Found {search_results['total']} results")
    
    # Test batch retrieval
    start_time = time.time()
    for file_id in file_ids[:5]:
        await storage_manager.retrieve_document(file_id, user_id, include_content=False)
    retrieval_time = time.time() - start_time
    
    print(f"✅ Retrieved 5 documents in {retrieval_time:.3f}s")
    print(f"   Average: {retrieval_time / 5:.3f}s per document")
    
    # Cleanup
    for file_id in file_ids:
        await storage_manager.delete_document(file_id, user_id, permanent=True)
    
    print("✅ Cleanup completed")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_storage_system())
    
    # Run performance test
    asyncio.run(performance_test())