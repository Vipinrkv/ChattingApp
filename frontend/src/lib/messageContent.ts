const FERNET_TOKEN_PATTERN = /^gAAAAA[A-Za-z0-9_-]{40,}={0,2}$/;

export function isEncryptedToken(value: unknown): value is string {
  return typeof value === 'string' && FERNET_TOKEN_PATTERN.test(value.trim());
}

export function displayMessageContent(value: unknown, fallback = 'Encrypted message unavailable') {
  if (isEncryptedToken(value)) {
    return fallback;
  }

  return typeof value === 'string' ? value : '';
}
