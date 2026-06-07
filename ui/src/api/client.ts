export class ApiError extends Error {
  public readonly status: number;
  public readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
}

async function parseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type')?.toLowerCase() ?? '';

  if (contentType.includes('application/json')) {
    return response.json();
  }

  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export async function request<T>(url: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;
  const response = await fetch(url, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...(headers ?? {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const parsedBody = await parseBody(response);
  if (!response.ok) {
    throw new ApiError(`Request failed: ${response.status}`, response.status, parsedBody);
  }

  return parsedBody as T;
}
