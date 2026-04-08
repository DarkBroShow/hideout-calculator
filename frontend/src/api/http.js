
export async function requestJson(url, options = {}) {
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    const error = new Error(`HTTP ${res.status}: ${text || res.statusText}`);
    error.status = res.status;
    throw error;
  }

  return res.json();
}