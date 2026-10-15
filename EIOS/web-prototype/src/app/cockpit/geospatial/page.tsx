import { Metadata } from 'next';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { GeoShell } from '@/components/cockpit/geo/geo-shell';
import { RequireAuth } from '@/components/auth/require-auth';

export const metadata: Metadata = {
  title: 'EIOS | Geospatial',
  description: 'Financial geography as an evidence lens inside the AML investigation.',
};

type Search = Promise<{ [key: string]: string | string[] | undefined }>;

/** The view and pick in the URL reach the workspace from the server, so the first render matches on both sides. */
export default async function GeospatialPage({ searchParams }: { searchParams: Search }) {
  const params = await searchParams;
  const initialSearch = new URLSearchParams(
    Object.entries(params).flatMap(([k, v]) => (typeof v === 'string' ? [[k, v]] : [])),
  ).toString();
  return (
    <RequireAuth>
      <CockpitProvider>
        <GeoShell initialSearch={initialSearch} />
      </CockpitProvider>
    </RequireAuth>
  );
}
