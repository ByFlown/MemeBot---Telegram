"""
Solana AsyncClient proxy fix for Fly.io deployment
This module provides a patched version of AsyncClient that ignores proxy parameters
"""

import logging
from typing import Optional, Union
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment

logger = logging.getLogger(__name__)

class ProxyFreeAsyncClient(AsyncClient):
    """AsyncClient that ignores proxy settings to prevent initialization errors"""
    
    def __init__(self, endpoint: str, commitment: Optional[Union[Commitment, str]] = None, **kwargs):
        """Initialize AsyncClient without proxy support"""
        try:
            # Remove any proxy-related kwargs that might cause issues
            clean_kwargs = {k: v for k, v in kwargs.items() if 'proxy' not in k.lower()}
            
            # Clear proxy environment variables during initialization
            import os
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
            original_env = {}
            
            for var in proxy_vars:
                if var in os.environ:
                    original_env[var] = os.environ[var]
                    del os.environ[var]
            
            try:
                # Initialize parent class without proxy parameters
                if commitment:
                    if isinstance(commitment, str):
                        commitment = Commitment(commitment)
                    super().__init__(endpoint, commitment=commitment)
                else:
                    super().__init__(endpoint)
                
                logger.debug(f"ProxyFreeAsyncClient initialized for endpoint: {endpoint}")
                
            finally:
                # Restore environment variables
                for var, value in original_env.items():
                    os.environ[var] = value
            
        except Exception as e:
            logger.error(f"Error initializing ProxyFreeAsyncClient: {e}")
            # Try even more basic initialization
            try:
                # Manually set basic attributes
                self._endpoint = endpoint
                self._commitment = commitment if commitment else Commitment("confirmed")
                self._client = None
                logger.warning("Using minimal initialization for ProxyFreeAsyncClient")
            except Exception as fallback_error:
                logger.error(f"Minimal initialization also failed: {fallback_error}")
                raise Exception(f"Unable to initialize AsyncClient for {endpoint}: {e}")
    
    def __str__(self):
        return f"ProxyFreeAsyncClient(endpoint={getattr(self, '_endpoint', 'unknown')})"

def create_safe_rpc_client(endpoint: str, commitment: Optional[Union[Commitment, str]] = None) -> AsyncClient:
    """
    Create a safe RPC client that bypasses proxy issues
    
    Args:
        endpoint: RPC endpoint URL
        commitment: Transaction commitment level
        
    Returns:
        AsyncClient instance that works without proxy issues
    """
    try:
        # First, try the proxy-free version
        return ProxyFreeAsyncClient(endpoint, commitment)
    except Exception as e:
        logger.warning(f"ProxyFreeAsyncClient failed, trying standard client: {e}")
        
        try:
            # Fallback to original client with environment manipulation
            import os
            
            # Store and clear proxy environment variables
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
            original_env = {}
            
            for var in proxy_vars:
                if var in os.environ:
                    original_env[var] = os.environ[var]
                    del os.environ[var]
            
            try:
                # Create client without proxy environment
                if commitment:
                    client = AsyncClient(endpoint, commitment=commitment)
                else:
                    client = AsyncClient(endpoint)
                    
                logger.info(f"Successfully created standard AsyncClient for {endpoint}")
                return client
                
            finally:
                # Restore environment variables
                for var, value in original_env.items():
                    os.environ[var] = value
                    
        except Exception as fallback_error:
            logger.error(f"All client creation methods failed: {fallback_error}")
            raise Exception(f"Unable to create RPC client for {endpoint}: {fallback_error}")

# Monkey patch function to replace AsyncClient usage
def patch_async_client():
    """Replace AsyncClient with ProxyFreeAsyncClient globally"""
    try:
        import solana.rpc.async_api
        
        # Store original for reference
        _original_async_client = solana.rpc.async_api.AsyncClient
        
        # Replace with proxy-free version
        solana.rpc.async_api.AsyncClient = ProxyFreeAsyncClient
        
        logger.info("Successfully patched AsyncClient to bypass proxy issues")
        return True
    except Exception as e:
        logger.error(f"Failed to patch AsyncClient: {e}")
        return False

# Alternative approach: wrap the constructor to filter out proxy parameters
def create_proxy_safe_init(original_init):
    """Create a wrapped version of AsyncClient.__init__ that filters proxy parameters"""
    def safe_init(self, *args, **kwargs):
        # Remove any proxy-related parameters that might cause errors
        filtered_kwargs = {k: v for k, v in kwargs.items() 
                          if not any(proxy_term in k.lower() for proxy_term in ['proxy', 'http_proxy', 'https_proxy'])}
        
        # Clear proxy environment temporarily
        import os
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
        original_env = {}
        
        for var in proxy_vars:
            if var in os.environ:
                original_env[var] = os.environ[var]
                del os.environ[var]
        
        try:
            return original_init(self, *args, **filtered_kwargs)
        finally:
            # Restore environment
            for var, value in original_env.items():
                os.environ[var] = value
    
    return safe_init

def patch_async_client_init():
    """Alternative patching approach - wrap the __init__ method"""
    try:
        from solana.rpc.async_api import AsyncClient
        
        if not hasattr(AsyncClient, '_original_init'):
            AsyncClient._original_init = AsyncClient.__init__
            AsyncClient.__init__ = create_proxy_safe_init(AsyncClient._original_init)
            logger.info("Successfully patched AsyncClient.__init__ to bypass proxy issues")
            return True
    except Exception as e:
        logger.error(f"Failed to patch AsyncClient.__init__: {e}")
        return False