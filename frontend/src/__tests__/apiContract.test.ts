import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiRequest } from '../lib/api';

const fetchMock = vi.fn();

describe('apiRequest', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    global.fetch = fetchMock as unknown as typeof global.fetch;
    localStorage.clear();
  });

  it('injects the auth token when present in localStorage', async () => {
    localStorage.setItem('authToken', 'test-token');

    fetchMock.mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ success: true }),
    } as any);

    await apiRequest('/hello', { method: 'GET' });

    const [, options] = fetchMock.mock.calls[0];
    expect((options as RequestInit).headers).toMatchObject({
      Authorization: 'Bearer test-token',
      Accept: 'application/json',
    });
  });

  it('adds JSON content type for body payloads', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ created: true }),
    } as any);

    await apiRequest('/posts', { method: 'POST', body: JSON.stringify({ title: 'Test' }) });

    const [, options] = fetchMock.mock.calls[0];
    expect((options as RequestInit).headers).toMatchObject({
      'Content-Type': 'application/json',
    });
  });
});
