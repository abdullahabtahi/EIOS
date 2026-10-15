import { NextResponse } from 'next/server';
import { parseDemoAccess } from '@/lib/auth/demo-access';

// Read at request time: a statically optimised route would bake in the build's (empty) environment.
export const dynamic = 'force-dynamic';

/** The reviewer accounts the owner chose to publish on the login page, or 404 when none are configured. */
export async function GET() {
  const access = parseDemoAccess(process.env.EIOS_DEMO_ACCESS);
  if (!access) return NextResponse.json({ detail: 'not configured' }, { status: 404 });
  return NextResponse.json(access, { headers: { 'Cache-Control': 'no-store' } });
}
