export interface Env {
  UPSTREAM_URL: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const upstream = new URL(env.UPSTREAM_URL);
    const incoming = new URL(request.url);
    const target = new URL(incoming.pathname + incoming.search, upstream);

    const headers = new Headers(request.headers);
    headers.delete("host");

    const proxiedRequest = new Request(target, {
      method: request.method,
      headers,
      body: request.body,
      redirect: "manual",
    });

    const response = await fetch(proxiedRequest);
    const responseHeaders = new Headers(response.headers);

    const location = responseHeaders.get("location");
    if (location) {
      responseHeaders.set(
        "location",
        location.replace(upstream.origin, incoming.origin),
      );
    }

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  },
};
