export function levelOptions(max, selected = 1) {
  let s = "";
  for (let i = 1; i <= max; i++) {
    s += `<option value="${i}" ${i === selected ? "selected" : ""}>${i}</option>`;
  }
  return s;
}

export function fmtNumber(n) {
  return new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 2 }).format(n);
}
export function fmtInt(n) {
  return new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 0 }).format(n);
}

// --- base64url helpers ---
export function bytesToB64Url(bytes) {
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function b64UrlToBytes(s) {
  s = String(s).replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4 !== 0) s += "=";
  const bin = atob(s);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

