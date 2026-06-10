// API Configuration
export const API_URL = __DEV__
  ? 'http://localhost:5000/api/v1'  // Development
  : 'https://api.onyxpos.com/api/v1'; // Production

export const APP_NAME = 'OnyxPOS';

// Colors
export const COLORS = {
  primary: '#6366f1',      // Indigo
  secondary: '#8b5cf6',    // Purple
  accent: '#06b6d4',       // Cyan
  success: '#10b981',      // Green
  warning: '#f59e0b',      // Amber
  error: '#ef4444',        // Red
  dark: '#1a1a2e',         // Dark background
  darkCard: '#16213e',     // Card background
  text: '#ffffff',         // White text
  textMuted: '#94a3b8',    // Gray text
  border: '#334155',       // Border color
};
