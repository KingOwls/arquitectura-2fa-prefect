import test from 'node:test';
import assert from 'node:assert/strict';
import {totp,hotp,normalizeSecret,decodeBase32} from './totp.mjs';
const secret='GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ';
for(const [time,expected] of [[59,'94287082'],[1111111109,'07081804'],[1111111111,'14050471'],[1234567890,'89005924'],[2000000000,'69279037'],[20000000000,'65353130']]) {
  test(`RFC 6238 SHA1 t=${time}`,()=>assert.equal(totp(secret,time,8),expected));
}
test('RFC 4226 counters',()=>['755224','287082','359152','969429','338314','254676','287922','162583','399871','520489'].forEach((v,i)=>assert.equal(hotp(secret,i),v)));
test('boundary and leading zeros',()=>{assert.equal(totp(secret,29),hotp(secret,0));assert.equal(totp(secret,30),hotp(secret,1));assert.equal(totp(secret,1111111109),'081804');});
test('import URI and Base32',()=>{assert.equal(normalizeSecret(`otpauth://totp/lab?secret=${secret}&period=30`),secret);assert.equal(new TextDecoder().decode(decodeBase32(secret)),'12345678901234567890');});
test('reject malformed input and incompatible URI',()=>{for(const value of ['@bad','A','otpauth://hotp/lab?secret=AAAA','otpauth://totp/lab?secret=AAAA&digits=8'])assert.throws(()=>normalizeSecret(value));});
