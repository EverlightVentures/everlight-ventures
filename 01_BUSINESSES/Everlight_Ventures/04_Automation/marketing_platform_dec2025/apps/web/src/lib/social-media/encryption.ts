/**
 * Encryption utilities for secure storage of social media OAuth tokens
 * Uses AES-256-GCM encryption
 */

import crypto from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 16; // For AES, this is always 16
const SALT_LENGTH = 64;
const TAG_LENGTH = 16;
const KEY_LENGTH = 32;
const ITERATIONS = 100000; // PBKDF2 iterations

/**
 * Get the encryption key from environment variable
 * Key should be a 64-character hex string (32 bytes)
 */
function getEncryptionKey(): Buffer {
  const key = process.env.SOCIAL_MEDIA_ENCRYPTION_KEY;

  if (!key) {
    throw new Error(
      'SOCIAL_MEDIA_ENCRYPTION_KEY environment variable is not set. ' +
      'Generate one with: openssl rand -hex 32'
    );
  }

  if (key.length !== 64) {
    throw new Error(
      'SOCIAL_MEDIA_ENCRYPTION_KEY must be 64 characters (32 bytes in hex). ' +
      'Generate one with: openssl rand -hex 32'
    );
  }

  return Buffer.from(key, 'hex');
}

/**
 * Encrypt a string (e.g., OAuth access token)
 * Returns encrypted string in format: iv:salt:authTag:encryptedData (all hex-encoded)
 */
export function encryptToken(plaintext: string): string {
  const masterKey = getEncryptionKey();

  // Generate random IV and salt
  const iv = crypto.randomBytes(IV_LENGTH);
  const salt = crypto.randomBytes(SALT_LENGTH);

  // Derive encryption key using PBKDF2
  const key = crypto.pbkdf2Sync(masterKey, salt, ITERATIONS, KEY_LENGTH, 'sha256');

  // Create cipher
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv);

  // Encrypt the plaintext
  let encrypted = cipher.update(plaintext, 'utf8', 'hex');
  encrypted += cipher.final('hex');

  // Get authentication tag
  const authTag = cipher.getAuthTag();

  // Return combined string: iv:salt:authTag:encryptedData
  return [
    iv.toString('hex'),
    salt.toString('hex'),
    authTag.toString('hex'),
    encrypted,
  ].join(':');
}

/**
 * Decrypt an encrypted string
 * Expects input in format: iv:salt:authTag:encryptedData (all hex-encoded)
 */
export function decryptToken(encryptedString: string): string {
  const masterKey = getEncryptionKey();

  // Split the encrypted string into its components
  const parts = encryptedString.split(':');

  if (parts.length !== 4) {
    throw new Error('Invalid encrypted string format');
  }

  const [ivHex, saltHex, authTagHex, encryptedHex] = parts;

  // Convert from hex
  const iv = Buffer.from(ivHex, 'hex');
  const salt = Buffer.from(saltHex, 'hex');
  const authTag = Buffer.from(authTagHex, 'hex');
  const encrypted = Buffer.from(encryptedHex, 'hex');

  // Derive the same key using PBKDF2
  const key = crypto.pbkdf2Sync(masterKey, salt, ITERATIONS, KEY_LENGTH, 'sha256');

  // Create decipher
  const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
  decipher.setAuthTag(authTag);

  // Decrypt
  let decrypted = decipher.update(encrypted);
  decrypted = Buffer.concat([decrypted, decipher.final()]);

  return decrypted.toString('utf8');
}

/**
 * Test encryption/decryption (useful for verification)
 */
export function testEncryption(): boolean {
  try {
    const testString = 'test-oauth-token-12345';
    const encrypted = encryptToken(testString);
    const decrypted = decryptToken(encrypted);
    return decrypted === testString;
  } catch (error) {
    console.error('Encryption test failed:', error);
    return false;
  }
}

/**
 * Safely handle encrypted tokens in database operations
 */
export interface EncryptedTokenData {
  accessToken: string;
  refreshToken?: string | null;
}

/**
 * Encrypt token data for storage
 */
export function encryptTokenData(data: {
  accessToken: string;
  refreshToken?: string | null;
}): EncryptedTokenData {
  return {
    accessToken: encryptToken(data.accessToken),
    refreshToken: data.refreshToken ? encryptToken(data.refreshToken) : null,
  };
}

/**
 * Decrypt token data from storage
 */
export function decryptTokenData(data: {
  accessToken: string;
  refreshToken?: string | null;
}): {
  accessToken: string;
  refreshToken?: string | null;
} {
  return {
    accessToken: decryptToken(data.accessToken),
    refreshToken: data.refreshToken ? decryptToken(data.refreshToken) : null,
  };
}
