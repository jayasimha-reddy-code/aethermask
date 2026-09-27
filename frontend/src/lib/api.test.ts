import { ApiError, assertRelative, manifestToFile } from './api';

describe('api client helpers', () => {
  test('ApiError captures message and HTTP status', () => {
    const err = new ApiError('Not found', 404);
    expect(err.message).toBe('Not found');
    expect(err.status).toBe(404);
    expect(err.name).toBe('ApiError');
  });

  test('assertRelative validates relative path', () => {
    expect(assertRelative('/api/v1/health')).toBe('/api/v1/health');
    expect(assertRelative('api/v1/health')).toBe('api/v1/health');
  });

  test('assertRelative rejects absolute or external URLs', () => {
    expect(() => assertRelative(['http:', '', 'external.site', 'leak'].join('/'))).toThrow();
    expect(() => assertRelative(['https:', '', 'external.site', 'leak'].join('/'))).toThrow();
    expect(() => assertRelative('//external.site/leak')).toThrow();
  });

  test('manifestToFile creates valid File object from manifest JSON', async () => {
    const manifest = { version: '2.1', cipher_suite: 'AES-256-GCM-Argon2id' };
    const file = manifestToFile(manifest, 'test.ciphermap');
    expect(file.name).toBe('test.ciphermap');
    expect(file.type).toBe('application/json');
    const text = await file.text();
    expect(JSON.parse(text)).toEqual(manifest);
  });
});
