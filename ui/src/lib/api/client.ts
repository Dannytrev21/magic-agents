type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details: JsonValue | Record<string, unknown> | null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type JsonRequestOptions = Omit<RequestInit, "body"> & {
  body?: JsonValue | Record<string, unknown>;
  fetchImpl?: typeof fetch;
};

export async function jsonRequest<T>(
  input: RequestInfo | URL,
  options: JsonRequestOptions = {},
): Promise<T> {
  const { body, fetchImpl = fetch, headers, ...rest } = options;
  const response = await fetchImpl(input, {
    ...rest,
    headers: {
      Accept: "application/json",
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const rawText = await response.text();
  const parsed = rawText ? (JSON.parse(rawText) as T | Record<string, unknown>) : null;

  if (!response.ok) {
    const message =
      typeof parsed === "object" && parsed !== null && "error" in parsed
        ? String(parsed.error)
        : response.statusText;
    throw new ApiError(message, response.status, parsed);
  }

  return (parsed ?? {}) as T;
}
