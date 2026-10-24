import { hmac } from '@noble/hashes/hmac.js';
import { sha1 } from '@noble/hashes/legacy.js';
export function normalizeSecret(input) {
  let secret = input.trim();
  if (secret.startsWith('otpauth://')) {
    const url = new URL(secret);
    if (url.hostname !== 'totp') throw new Error('Solo se admite TOTP.');
    for (const [name, expected] of [['algorithm','SHA1'],['digits','6'],['period','30']]) {
      const value = url.searchParams.get(name);
      if (value && value.toUpperCase() !== expected) throw new Error('Usa SHA1, 6 dígitos y 30 segundos.');
    }
    secret = url.searchParams.get('secret') || '';
  }
  secret = secret.replace(/\s/g,'').replace(/=+$/,'').toUpperCase();
  if (!/^[A-Z2-7]+$/.test(secret) || ![0,2,4,5,7].includes(secret.length % 8)) throw new Error('Semilla Base32 inválida.');
  return secret;
}
export function decodeBase32(input) {
  const secret = normalizeSecret(input), alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = 0, value = 0; const output = [];
  for (const char of secret) {
    value = (value << 5) | alphabet.indexOf(char); bits += 5;
    if (bits >= 8) { bits -= 8; output.push((value >>> bits) & 255); }
  }
  if (bits && (value & ((1 << bits) - 1)) !== 0) throw new Error('Base32 no canónico.');
  return new Uint8Array(output);
}
export function hotp(secret, counter, digits = 6) {
  const message = new Uint8Array(8); let count = BigInt(counter);
  for (let i = 7; i >= 0; i--) { message[i] = Number(count & 255n); count >>= 8n; }
  const hash = hmac(sha1, decodeBase32(secret), message), offset = hash[hash.length - 1] & 15;
  const binary = ((hash[offset] & 127) * 2 ** 24) + (hash[offset + 1] << 16) + (hash[offset + 2] << 8) + hash[offset + 3];
  return String(binary % (10 ** digits)).padStart(digits, '0');
}
export function totp(secret, unixSeconds = Date.now()/1000, digits = 6) { return hotp(secret, Math.floor(unixSeconds/30), digits); }
