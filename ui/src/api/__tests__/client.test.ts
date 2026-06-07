import { ApiError, request } from '../client';

describe('request', () => {
  it('returns parsed json for successful responses', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    vi.stubGlobal('fetch', fetchMock);

    await expect(
      request<{ ok: boolean }>('/api/test', { method: 'POST', body: { id: 1 } }),
    ).resolves.toEqual({ ok: true });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ id: 1 }),
      }),
    );
  });

  it('throws ApiError with parsed body for failed responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: 'nope' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    try {
      await request('/api/test');
      throw new Error('request should have failed');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect(error).toMatchObject({
        name: 'ApiError',
        status: 400,
        body: { error: 'nope' },
      });
    }
  });
});
