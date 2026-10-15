import { Metadata } from 'next';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { GeoShell } from '@/components/cockpit/geo/geo-shell';
import { RequireAuth } from '@/components/auth/require-auth';

export const metadata: Metadata = {
  title: 'EIOS | Geospatial',
  description: 'Financial geography as an evidence lens inside the AML investigation.',
};

export default function GeospatialPage() {
  return (
    <RequireAuth>
      <CockpitProvider>
        <GeoShell />
      </CockpitProvider>
    </RequireAuth>
  );
}
