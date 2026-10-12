import { Metadata } from 'next';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { TripartiteShell } from '@/components/cockpit/shell/tripartite-shell';

export const metadata: Metadata = {
  title: 'EIOS | Institutional Operator Cockpit',
  description:
    'Institutional Common Operational Picture (COP) with real-time semantic provenance, causal refutation, and governed two-phase commit.',
};

export default function CockpitPage() {
  return (
    <CockpitProvider>
      <TripartiteShell />
    </CockpitProvider>
  );
}
