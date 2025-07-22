import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.system_program import TransferParams, transfer
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.async_client import AsyncToken
from spl.token.instructions import get_associated_token_address
import aiohttp
import json
import os
from datetime import datetime
import base58
import base64

logger = logging.getLogger(__name__)

class WalletManager:
    def __init__(self):
        # Solana RPC endpoints
        self.rpc_endpoints = [
            "https://api.mainnet-beta.solana.com",
            "https://solana-api.projectserum.com",
            "https://rpc.ankr.com/solana"
        ]
        self.current_rpc = 0
        
        # Jupiter API for swaps
        self.jupiter_api = "https://quote-api.jup.ag/v6"
        
        # Wallet configuration
        self.keypair = None
        self.wallet_address = None
        self.session = None
        
        # Trading configuration
        self.max_slippage = 0.5  # 0.5% slippage tolerance
        self.priority_fee = 0.0001  # SOL priority fee
        
        # Position tracking
        self.active_positions = {}
        self.trade_history = []
        
        self._load_wallet()
    
    def _load_wallet(self):
        """Load wallet from environment or configuration"""
        try:
            # Try to load private key from environment variable
            private_key_b58 = os.getenv('SOLANA_PRIVATE_KEY')
            
            if private_key_b58:
                # Decode base58 private key
                private_key_bytes = base58.b58decode(private_key_b58)
                self.keypair = Keypair.from_bytes(private_key_bytes)
                self.wallet_address = str(self.keypair.pubkey())
                logger.info(f"Wallet loaded: {self.wallet_address[:8]}...{self.wallet_address[-8:]}")
            else:
                logger.warning("No private key found. Wallet operations disabled.")
                
        except Exception as e:
            logger.error(f"Error loading wallet: {e}")
    
    def is_configured(self) -> bool:
        """Check if wallet is properly configured"""
        return self.keypair is not None
    
    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'MemeBot-WalletManager/1.0'}
            )
        return self.session
    
    async def get_rpc_client(self) -> AsyncClient:
        """Get Solana RPC client with failover"""
        endpoint = self.rpc_endpoints[self.current_rpc]
        try:
            return AsyncClient(endpoint, commitment=Commitment("confirmed"))
        except Exception as e:
            logger.warning(f"RPC endpoint {endpoint} failed: {e}")
            self.current_rpc = (self.current_rpc + 1) % len(self.rpc_endpoints)
            return AsyncClient(self.rpc_endpoints[self.current_rpc])
    
    async def get_sol_balance(self) -> float:
        """Get SOL balance of the wallet"""
        try:
            if not self.is_configured():
                return 0.0
            
            client = await self.get_rpc_client()
            
            try:
                balance_response = await client.get_balance(self.keypair.pubkey())
                
                if balance_response.value is not None:
                    # Convert lamports to SOL
                    return balance_response.value / 1e9
                
                return 0.0
                
            finally:
                await client.close()
                
        except Exception as e:
            logger.error(f"Error getting SOL balance: {e}")
            return 0.0
    
    async def get_token_balance(self, token_address: str) -> float:
        """Get balance of a specific SPL token"""
        try:
            if not self.is_configured():
                return 0.0
            
            client = await self.get_rpc_client()
            
            try:
                token_mint = Pubkey.from_string(token_address)
                associated_token_account = get_associated_token_address(
                    self.keypair.pubkey(), token_mint
                )
                
                # Get token account balance
                balance_response = await client.get_token_account_balance(
                    associated_token_account
                )
                
                if balance_response.value:
                    return float(balance_response.value.amount)
                
                return 0.0
                
            finally:
                await client.close()
                
        except Exception as e:
            logger.debug(f"Token balance error (may not have token): {e}")
            return 0.0
    
    async def get_wallet_info(self) -> Dict:
        """Get comprehensive wallet information"""
        try:
            if not self.is_configured():
                return {
                    'address': 'Not configured',
                    'sol_balance': 0.0,
                    'token_count': 0,
                    'connected': False
                }
            
            sol_balance = await self.get_sol_balance()
            
            # Get token accounts
            client = await self.get_rpc_client()
            try:
                token_accounts = await client.get_token_accounts_by_owner(
                    self.keypair.pubkey(),
                    {"programId": TOKEN_PROGRAM_ID}
                )
                
                token_count = len(token_accounts.value) if token_accounts.value else 0
                
            finally:
                await client.close()
            
            return {
                'address': self.wallet_address,
                'sol_balance': sol_balance,
                'token_count': token_count,
                'connected': True,
                'active_positions': len(self.active_positions)
            }
            
        except Exception as e:
            logger.error(f"Error getting wallet info: {e}")
            return {
                'address': self.wallet_address or 'Error',
                'sol_balance': 0.0,
                'token_count': 0,
                'connected': False
            }
    
    async def execute_trade(self, token_address: str, amount_sol: float, action: str) -> Dict:
        """Execute a trade (buy/sell) using Jupiter aggregator"""
        try:
            if not self.is_configured():
                return {
                    'success': False,
                    'error': 'Wallet not configured',
                    'type': 'config_error'
                }
            
            if action not in ['buy', 'sell']:
                return {
                    'success': False,
                    'error': f'Invalid action: {action}',
                    'type': 'invalid_action'
                }
            
            logger.info(f"Executing {action} trade: {amount_sol} SOL for {token_address}")
            
            # Get quote from Jupiter
            quote = await self._get_jupiter_quote(token_address, amount_sol, action)
            
            if not quote:
                return {
                    'success': False,
                    'error': 'Failed to get quote from Jupiter',
                    'type': 'quote_error'
                }
            
            # Execute the swap
            swap_result = await self._execute_jupiter_swap(quote, action)
            
            if swap_result.get('success'):
                # Track the position
                self._track_position(token_address, amount_sol, action, swap_result)
                
                # Add to trade history
                self.trade_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'action': action,
                    'token_address': token_address,
                    'amount_sol': amount_sol,
                    'result': swap_result,
                    'signature': swap_result.get('signature')
                })
            
            return swap_result
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {
                'success': False,
                'error': str(e),
                'type': 'execution_error'
            }
    
    async def _get_jupiter_quote(self, token_address: str, amount_sol: float, action: str) -> Optional[Dict]:
        """Get quote from Jupiter aggregator"""
        try:
            session = await self.get_session()
            
            # SOL mint address
            sol_mint = "So11111111111111111111111111111111111111112"
            
            # Convert SOL amount to lamports
            amount_lamports = int(amount_sol * 1e9)
            
            if action == "buy":
                # Buy token with SOL
                input_mint = sol_mint
                output_mint = token_address
                amount = amount_lamports
            else:
                # Sell token for SOL
                input_mint = token_address
                output_mint = sol_mint
                # For sell, we need to get token balance first
                token_balance = await self.get_token_balance(token_address)
                if token_balance == 0:
                    logger.warning(f"No tokens to sell for {token_address}")
                    return None
                amount = int(token_balance)
            
            # Get quote from Jupiter
            quote_url = f"{self.jupiter_api}/quote"
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': amount,
                'slippageBps': int(self.max_slippage * 100)  # Convert to basis points
            }
            
            async with session.get(quote_url, params=params) as response:
                if response.status == 200:
                    quote_data = await response.json()
                    logger.info(f"Jupiter quote: {quote_data.get('outAmount', 0)} output for {amount} input")
                    return quote_data
                else:
                    logger.error(f"Jupiter quote error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting Jupiter quote: {e}")
            return None
    
    async def _execute_jupiter_swap(self, quote: Dict, action: str) -> Dict:
        """Execute swap using Jupiter"""
        try:
            session = await self.get_session()
            
            # Get swap transaction from Jupiter
            swap_url = f"{self.jupiter_api}/swap"
            swap_payload = {
                'quoteResponse': quote,
                'userPublicKey': str(self.keypair.pubkey()),
                'wrapAndUnwrapSol': True,
                'dynamicComputeUnitLimit': True,
                'priorityLevelWithMaxLamports': {
                    'priorityLevel': 'medium',
                    'maxLamports': int(self.priority_fee * 1e9)
                }
            }
            
            async with session.post(swap_url, json=swap_payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Jupiter swap error: {response.status} - {error_text}")
                    return {
                        'success': False,
                        'error': f'Jupiter API error: {response.status}',
                        'type': 'api_error'
                    }
                
                swap_data = await response.json()
                swap_transaction = swap_data.get('swapTransaction')
                
                if not swap_transaction:
                    return {
                        'success': False,
                        'error': 'No swap transaction returned',
                        'type': 'no_transaction'
                    }
            
            # Decode and sign the transaction
            transaction_bytes = base64.b64decode(swap_transaction)
            transaction = Transaction.from_bytes(transaction_bytes)
            transaction.sign([self.keypair])
            
            # Send the transaction
            client = await self.get_rpc_client()
            try:
                signature = await client.send_transaction(
                    transaction,
                    opts={"skip_preflight": False, "max_retries": 3}
                )
                
                # Wait for confirmation
                confirmation = await client.confirm_transaction(
                    signature.value,
                    commitment=Commitment("confirmed")
                )
                
                if confirmation.value[0].err is None:
                    logger.info(f"Swap successful: {signature.value}")
                    return {
                        'success': True,
                        'signature': str(signature.value),
                        'action': action,
                        'quote': quote
                    }
                else:
                    logger.error(f"Transaction failed: {confirmation.value[0].err}")
                    return {
                        'success': False,
                        'error': f'Transaction failed: {confirmation.value[0].err}',
                        'type': 'transaction_failed'
                    }
                    
            finally:
                await client.close()
                
        except Exception as e:
            logger.error(f"Error executing Jupiter swap: {e}")
            return {
                'success': False,
                'error': str(e),
                'type': 'execution_error'
            }
    
    def _track_position(self, token_address: str, amount_sol: float, action: str, result: Dict):
        """Track active positions"""
        if action == "buy":
            if token_address not in self.active_positions:
                self.active_positions[token_address] = {
                    'amount_sol': 0,
                    'entry_time': datetime.now(),
                    'trades': []
                }
            
            self.active_positions[token_address]['amount_sol'] += amount_sol
            self.active_positions[token_address]['trades'].append({
                'action': action,
                'amount': amount_sol,
                'time': datetime.now(),
                'result': result
            })
            
        elif action == "sell":
            if token_address in self.active_positions:
                position = self.active_positions[token_address]
                position['trades'].append({
                    'action': action,
                    'amount': amount_sol,
                    'time': datetime.now(),
                    'result': result
                })
                
                # If fully sold, remove from active positions
                if position['amount_sol'] <= amount_sol:
                    del self.active_positions[token_address]
                else:
                    position['amount_sol'] -= amount_sol
    
    async def close_all_positions(self) -> List[Dict]:
        """Emergency close all positions"""
        try:
            if not self.is_configured():
                return []
            
            closed_positions = []
            
            for token_address, position in list(self.active_positions.items()):
                try:
                    # Get current token balance
                    token_balance = await self.get_token_balance(token_address)
                    
                    if token_balance > 0:
                        # Sell all tokens
                        result = await self.execute_trade(token_address, 0, 'sell')
                        
                        closed_positions.append({
                            'token_address': token_address,
                            'position': position,
                            'close_result': result,
                            'amount': token_balance
                        })
                        
                        if result.get('success'):
                            logger.info(f"Closed position for {token_address}")
                        else:
                            logger.error(f"Failed to close position for {token_address}: {result.get('error')}")
                
                except Exception as e:
                    logger.error(f"Error closing position for {token_address}: {e}")
                    continue
            
            # Clear active positions
            self.active_positions.clear()
            
            return closed_positions
            
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return []
    
    async def close(self):
        """Close resources"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()