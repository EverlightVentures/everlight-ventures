/**
 * Web3 Wallet Integration Scaffold
 *
 * Frontend wallet connection for crypto casino path.
 * Detects MetaMask/injected providers. Displays address.
 * Scaffold for deposit/withdraw UI.
 *
 * No smart contracts yet -- just the connection flow.
 * Future: deploy chip contract on Avalanche C-Chain.
 */

export interface WalletState {
  connected: boolean
  address: string | null
  chainId: number | null
  balance: string | null
  error: string | null
}

const INITIAL_STATE: WalletState = {
  connected: false,
  address: null,
  chainId: null,
  balance: null,
  error: null,
}

// Check if MetaMask or any injected provider exists
export function hasWalletProvider(): boolean {
  if (typeof window === 'undefined') return false
  return !!(window as any).ethereum
}

// Connect wallet
export async function connectWallet(): Promise<WalletState> {
  if (!hasWalletProvider()) {
    return { ...INITIAL_STATE, error: 'No wallet detected. Install MetaMask.' }
  }

  try {
    const ethereum = (window as any).ethereum
    const accounts = await ethereum.request({ method: 'eth_requestAccounts' })
    const chainId = await ethereum.request({ method: 'eth_chainId' })

    if (accounts.length === 0) {
      return { ...INITIAL_STATE, error: 'No accounts found' }
    }

    const address = accounts[0]
    const balance = await ethereum.request({
      method: 'eth_getBalance',
      params: [address, 'latest'],
    })

    // Convert hex balance to ETH string
    const ethBalance = (parseInt(balance, 16) / 1e18).toFixed(4)

    return {
      connected: true,
      address,
      chainId: parseInt(chainId, 16),
      balance: ethBalance,
      error: null,
    }
  } catch (err: any) {
    return { ...INITIAL_STATE, error: err.message || 'Connection failed' }
  }
}

// Disconnect (clear state)
export function disconnectWallet(): WalletState {
  return { ...INITIAL_STATE }
}

// Format address for display (0x1234...5678)
export function formatAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`
}

// Supported chains for Vantaris
export const SUPPORTED_CHAINS: Record<number, string> = {
  1: 'Ethereum',
  43114: 'Avalanche',
  43113: 'Avalanche Fuji (Testnet)',
  137: 'Polygon',
  56: 'BNB Chain',
}

// Check if connected to supported chain
export function isSupportedChain(chainId: number | null): boolean {
  if (!chainId) return false
  return chainId in SUPPORTED_CHAINS
}
