/**
 * Service-to-service identity for Cloud Run: an ID token for the API's audience, minted by the
 * metadata server. Sent as X-Serverless-Authorization so the operator's own Authorization header
 * (a Firebase token) passes through to the API untouched.
 */
interface CachedToken {
  audience: string;
  token: string;
  expiresAtMs: number;
}

let cached: CachedToken | null = null;
const METADATA_IDENTITY_URL = 'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity';
const REFRESH_MARGIN_MS = 60_000;

function tokenExpiryMs(jwt: string): number {
  try {
    const payload = JSON.parse(Buffer.from(jwt.split('.')[1], 'base64url').toString('utf8'));
    return Number(payload.exp) * 1000;
  } catch {
    return Date.now() + 5 * 60_000;
  }
}

/** The IAM ID token for the configured backend audience, or null when none is configured (local dev). */
export async function getServiceIdToken(audience: string | undefined = process.env.EIOS_BACKEND_IAM_AUDIENCE): Promise<string | null> {
  if (!audience) return null;
  if (cached && cached.audience === audience && cached.expiresAtMs - REFRESH_MARGIN_MS > Date.now()) return cached.token;
  const res = await fetch(`${METADATA_IDENTITY_URL}?audience=${encodeURIComponent(audience)}&format=full`, {
    headers: { 'Metadata-Flavor': 'Google' },
    signal: AbortSignal.timeout(2000),
  });
  if (!res.ok) throw new Error(`metadata server returned ${res.status}`);
  const token = (await res.text()).trim();
  cached = { audience, token, expiresAtMs: tokenExpiryMs(token) };
  return token;
}

export function resetServiceIdTokenCache(): void {
  cached = null;
}
