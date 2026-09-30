export async function serviceJSON(path, { body, signal } = {}) {
  let response;
  try {
    response = await fetch(`/api/${path}`, body === undefined ? { signal } : {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Cannot reach the VAJRA service. Check the connection and local server, then retry.');
  }
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { detail = null; }
    throw new Error(typeof detail === 'string' ? detail : `The service could not complete the request (${response.status}).`);
  }
  return response.json();
}

export function downloadJSON(value, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
