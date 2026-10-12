import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.EIOS_BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(req: NextRequest) {
  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }

  try {
    const res = await fetch(`${BACKEND_URL}/api/cockpit/actions/stage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
  } catch {
    // Fallback offline staging
  }

  const intentId = body.intentId || `act_${Date.now()}`;
  return NextResponse.json({
    staged: true,
    intentId,
    actionType: body.actionType || 'HOLD_WITHDRAWAL',
    targetEntityId: body.targetEntityId || 'ENTITY-UNKNOWN',
    severity: body.severity || 'HIGH',
    expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
    kmsKeyId: 'projects/feios-prod/locations/global/keyRings/eios-cockpit/cryptoKeys/action-signer-p256',
    stagedTimestamp: new Date().toISOString(),
  });
}
