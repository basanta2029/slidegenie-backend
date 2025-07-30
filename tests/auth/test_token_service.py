"""
Tests for JWT Token Service.
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from jose import jwt

from app.core.config import get_settings
from app.services.auth.token_service import (
    BlacklistService,
    SessionManager,
    TokenPayload,
    TokenPair,
    TokenService,
)

settings = get_settings()


class TestTokenService:
    """Test cases for TokenService."""
    
    @pytest.fixture
    def token_service(self):
        """Create TokenService instance."""
        return TokenService()
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "user_id": uuid4(),
            "email": "test@university.edu",
            "roles": ["researcher"],
            "institution": "Test University",
        }
    
    @pytest.mark.asyncio
    async def test_create_token_pair(self, token_service, sample_user_data):
        """Test token pair creation."""
        with patch('app.services.auth.token_service.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            token_pair = await token_service.create_token_pair(**sample_user_data)
            
            assert isinstance(token_pair, TokenPair)
            assert token_pair.access_token
            assert token_pair.refresh_token
            assert token_pair.token_type == "bearer"
            assert token_pair.expires_in > 0
            assert token_pair.refresh_expires_in > 0
    
    @pytest.mark.asyncio
    async def test_decode_valid_token(self, token_service, sample_user_data):
        """Test decoding valid tokens."""
        with patch('app.services.auth.token_service.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            # Create token pair
            token_pair = await token_service.create_token_pair(**sample_user_data)
            
            # Mock blacklist check to return False (not blacklisted)
            with patch.object(token_service, '_is_token_blacklisted', return_value=False):
                # Decode access token
                access_payload = await token_service.decode_token(token_pair.access_token)
                
                assert access_payload is not None
                assert access_payload.sub == str(sample_user_data["user_id"])
                assert access_payload.email == sample_user_data["email"]
                assert access_payload.roles == sample_user_data["roles"]
                assert access_payload.institution == sample_user_data["institution"]
                assert access_payload.type == "access"
                
                # Decode refresh token
                refresh_payload = await token_service.decode_token(token_pair.refresh_token)
                
                assert refresh_payload is not None
                assert refresh_payload.type == "refresh"
    
    @pytest.mark.asyncio
    async def test_decode_blacklisted_token(self, token_service, sample_user_data):
        """Test decoding blacklisted tokens returns None."""
        with patch('app.services.auth.token_service.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            # Create token pair
            token_pair = await token_service.create_token_pair(**sample_user_data)
            
            # Mock blacklist check to return True (blacklisted)
            with patch.object(token_service, '_is_token_blacklisted', return_value=True):
                payload = await token_service.decode_token(token_pair.access_token)
                assert payload is None
    
    @pytest.mark.asyncio
    async def test_decode_invalid_token(self, token_service):
        """Test decoding invalid tokens returns None."""
        with patch('app.services.auth.token_service.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            # Test with completely invalid token
            payload = await token_service.decode_token("invalid.token.here")
            assert payload is None
            
            # Test with token signed with wrong key
            fake_token = jwt.encode(
                {"sub": "test", "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())},
                "wrong_secret",
                algorithm="HS256"
            )
            payload = await token_service.decode_token(fake_token)
            assert payload is None
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, token_service, sample_user_data):
        """Test token refresh functionality."""
        with patch('app.services.auth.token_service.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            # Create initial token pair
            with patch.object(token_service, '_is_token_blacklisted', return_value=False):
                initial_tokens = await token_service.create_token_pair(**sample_user_data)
                
                # Mock blacklisting of old token
                with patch.object(token_service, '_blacklist_token', return_value=True):
                    # Refresh tokens
                    new_tokens = await token_service.refresh_token(initial_tokens.refresh_token)
                    
                    assert new_tokens is not None
                    assert new_tokens.access_token != initial_tokens.access_token
                    assert new_tokens.refresh_token != initial_tokens.refresh_token
    
    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, token_service):
        """Test refresh with invalid refresh token."""
        with patch('app.services.auth.token_service.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            # Try to refresh with invalid token
            new_tokens = await token_service.refresh_token("invalid.token")
            assert new_tokens is None
    
    @pytest.mark.asyncio
    async def test_refresh_with_access_token(self, token_service, sample_user_data):
        """Test refresh with access token (should fail)."""
        with patch('app.services.auth.token_service.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            with patch.object(token_service, '_is_token_blacklisted', return_value=False):
                # Create token pair
                tokens = await token_service.create_token_pair(**sample_user_data)
                
                # Try to refresh with access token (should fail)
                new_tokens = await token_service.refresh_token(tokens.access_token)
                assert new_tokens is None
    
    @pytest.mark.asyncio
    async def test_revoke_token(self, token_service, sample_user_data):
        """Test token revocation."""
        with patch('app.services.auth.token_service.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            # Create token pair
            tokens = await token_service.create_token_pair(**sample_user_data)
            
            # Mock blacklisting
            with patch.object(token_service, '_blacklist_token', return_value=True):
                result = await token_service.revoke_token(tokens.access_token)
                assert result is True
    
    def test_generate_jti(self, token_service):
        """Test JTI generation."""
        jti1 = token_service._generate_jti()
        jti2 = token_service._generate_jti()
        
        assert jti1 != jti2
        assert len(jti1) > 0
        assert len(jti2) > 0
    
    def test_generate_session_id(self, token_service):
        """Test session ID generation."""
        session1 = token_service._generate_session_id()
        session2 = token_service._generate_session_id()
        
        assert session1 != session2
        assert len(session1) > 0
        assert len(session2) > 0


class TestBlacklistService:
    """Test cases for BlacklistService."""
    
    @pytest.fixture
    def blacklist_service(self):
        """Create BlacklistService instance."""
        return BlacklistService()
    
    @pytest.mark.asyncio
    async def test_add_to_blacklist(self, blacklist_service):
        """Test adding JTI to blacklist."""
        mock_redis = AsyncMock()
        
        with patch('app.services.auth.token_service.get_redis_client', return_value=mock_redis):
            jti = "test_jti_123"
            ttl = 3600
            
            result = await blacklist_service.add_to_blacklist(jti, ttl)
            
            assert result is True
            mock_redis.setex.assert_called_once_with(f"token:blacklist:{jti}", ttl, "1")
    
    @pytest.mark.asyncio
    async def test_is_blacklisted(self, blacklist_service):
        """Test checking if JTI is blacklisted."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1  # Exists
        
        with patch('app.services.auth.token_service.get_redis_client', return_value=mock_redis):
            jti = "test_jti_123"
            
            result = await blacklist_service.is_blacklisted(jti)
            
            assert result is True
            mock_redis.exists.assert_called_once_with(f"token:blacklist:{jti}")
    
    @pytest.mark.asyncio
    async def test_remove_from_blacklist(self, blacklist_service):
        """Test removing JTI from blacklist."""
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 1  # Deleted
        
        with patch('app.services.auth.token_service.get_redis_client', return_value=mock_redis):
            jti = "test_jti_123"
            
            result = await blacklist_service.remove_from_blacklist(jti)
            
            assert result is True
            mock_redis.delete.assert_called_once_with(f"token:blacklist:{jti}")
    
    @pytest.mark.asyncio
    async def test_get_blacklist_stats(self, blacklist_service):
        """Test getting blacklist statistics."""
        mock_redis = AsyncMock()
        mock_redis.keys.return_value = ["token:blacklist:1", "token:blacklist:2"]
        mock_redis.memory_usage.return_value = 1024
        
        with patch('app.services.auth.token_service.get_redis_client', return_value=mock_redis):
            stats = await blacklist_service.get_blacklist_stats()
            
            assert stats["total_blacklisted"] == 2
            assert stats["memory_usage"] == 1024


class TestSessionManager:
    """Test cases for SessionManager."""
    
    @pytest.fixture
    def session_manager(self):
        """Create SessionManager instance."""
        return SessionManager()
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Test session creation."""
        mock_redis = AsyncMock()
        
        with patch('app.services.auth.token_service.get_redis_client', return_value=mock_redis):
            user_id = str(uuid4())
            session_id = "test_session_123"
            metadata = {"ip": "192.168.1.1", "user_agent": "test"}
            
            result = await session_manager.create_session(user_id, session_id, metadata)
            
            assert result is True
            mock_redis.setex.assert_called_once()
            mock_redis.sadd.assert_called_once_with(f"user:sessions:{user_id}", session_id)
    
    @pytest.mark.asyncio
    async def test_validate_session(self, session_manager):
        """Test session validation."""
        mock_redis = AsyncMock()
        session_data = {
            "user_id": str(uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }
        mock_redis.get.return_value = json.dumps(session_data)
        
        with patch('app.services.auth.token_service.get_redis_client', return_value=mock_redis):
            session_id = "test_session_123"
            
            result = await session_manager.validate_session(session_id)
            
            assert result is not None
            assert result["user_id"] == session_data["user_id"]
            mock_redis.get.assert_called_once_with(f"session:{session_id}")
    
    @pytest.mark.asyncio
    async def test_invalidate_session(self, session_manager):
        """Test session invalidation."""
        mock_redis = AsyncMock()
        session_data = {"user_id": str(uuid4())}
        mock_redis.get.return_value = json.dumps(session_data)
        mock_redis.delete.return_value = 1
        
        with patch('app.services.auth.token_service.get_redis_client', return_value=mock_redis):
            session_id = "test_session_123"
            
            result = await session_manager.invalidate_session(session_id)
            
            assert result is True
            mock_redis.delete.assert_called_with(f"session:{session_id}")
    
    @pytest.mark.asyncio
    async def test_invalidate_all_user_sessions(self, session_manager):
        """Test invalidating all user sessions."""
        mock_redis = AsyncMock()
        user_id = str(uuid4())
        session_ids = ["session1", "session2", "session3"]
        mock_redis.smembers.return_value = session_ids
        
        with patch('app.services.auth.token_service.get_redis_client', return_value=mock_redis):
            result = await session_manager.invalidate_all_user_sessions(user_id)
            
            assert result is True
            # Should delete all sessions
            assert mock_redis.delete.call_count == len(session_ids) + 1  # +1 for user session set
    
    @pytest.mark.asyncio
    async def test_get_active_sessions(self, session_manager):
        """Test getting active sessions."""
        mock_redis = AsyncMock()
        user_id = str(uuid4())
        session_ids = ["session1", "session2"]
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }
        
        mock_redis.smembers.return_value = session_ids
        mock_redis.get.return_value = json.dumps(session_data)
        
        with patch('app.services.auth.token_service.get_redis_client', return_value=mock_redis):
            sessions = await session_manager.get_active_sessions(user_id)
            
            assert len(sessions) == len(session_ids)
            assert all("session_id" in session for session in sessions)
    
    @pytest.mark.asyncio
    async def test_extend_session(self, session_manager):
        """Test extending session TTL."""
        mock_redis = AsyncMock()
        mock_redis.ttl.return_value = 3600  # 1 hour remaining
        mock_redis.expire.return_value = True
        
        with patch('app.services.auth.token_service.get_redis_client', return_value=mock_redis):
            session_id = "test_session"
            additional_ttl = 1800  # 30 minutes
            
            result = await session_manager.extend_session(session_id, additional_ttl)
            
            assert result is True
            mock_redis.expire.assert_called_once_with(f"session:{session_id}", 3600 + 1800)


@pytest.mark.integration
class TestTokenServiceIntegration:
    """Integration tests requiring Redis."""
    
    @pytest.mark.asyncio
    async def test_full_token_lifecycle(self):
        """Test complete token lifecycle with real Redis."""
        # This test would require a real Redis instance
        # Skip if Redis is not available in test environment
        pytest.skip("Integration test requires Redis setup")
    
    @pytest.mark.asyncio
    async def test_concurrent_token_operations(self):
        """Test concurrent token operations."""
        # This test would verify thread safety and concurrent access
        pytest.skip("Integration test requires Redis setup")