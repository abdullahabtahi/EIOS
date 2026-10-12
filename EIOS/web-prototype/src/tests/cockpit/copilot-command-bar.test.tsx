import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { CopilotCommandBar } from '@/components/cockpit/shell/copilot-command-bar';

beforeEach(() => {
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/api/cockpit/copilot/query')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          queryId: 'qry_test_1',
          naturalLanguageQuery: 'What is the LatAm spread impact?',
          responseMarkdown: 'LatAm spread widened by 18 bps due to broker tiering adjustments.',
          citedMetrics: [
            {
              metricId: 'M-LATAM-01',
              name: 'Spread Shock LatAm',
              rawValue: 18.2,
              formattedValue: '+18.2 bps',
              unit: 'bps',
              semanticDefinitionVersion: 'v2.4.1 [d8a9f2]',
              asOfTimestamp: '2026-10-10T10:00:00Z',
              originEngine: 'duckdb:semantic_layer',
              stewardRole: 'VP Market Strategy',
              citation: '[BRIEF]',
              isCached: false,
            },
          ],
          auditorResult: {
            auditPassed: true,
            extractedNumbers: ['18', '18.2'],
            anchoredNumbers: ['18', '18.2'],
            untraceableNumbers: [],
            toolTracesCount: 2,
          },
          suggestedAction: {
            intentId: 'act_suggested_1',
            actionType: 'TUNE_MONITORING_THRESHOLD',
            targetEntityId: 'COMP-LATAM-01',
            targetEntityType: 'BROKER_FEED',
            severity: 'MEDIUM',
            lifecycleState: 'STAGED',
            stagedTimestamp: '2026-10-10T10:00:00Z',
            expiresAt: '2026-10-10T10:15:00Z',
            parameters: { newSpreadBps: 22 },
            estimatedImpact: 'Re-aligns broker alert sensitivity',
            requiresFourEyes: false,
            kmsSignatureBadge: {
              keyId: 'projects/feios-prod/locations/global/keyRings/eios-cockpit/cryptoKeys/action-signer-p256',
              algorithm: 'ECDSA_P256_SHA256',
              signatureDigest: 'DIGEST_SIM_881',
              verified: true,
            },
            fourEyesRecord: {
              initiatorOfficerId: 'OP_TEST',
              initiatorTimestamp: '2026-10-10T10:00:00Z',
              idpClaimValidation: true,
            },
          },
          timestamp: '2026-10-10T10:00:00Z',
        }),
      });
    }

    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        workstation: 'executive',
        isLiveConnected: true,
        isCachedFallback: false,
        asOfTimestamp: '2026-10-10T10:00:00Z',
        session: { sessionId: 'test', systemLatencyMs: 12 },
        triageItems: [],
        activeDossier: null,
        stagedActionCards: [],
      }),
    });
  });
});

describe('Copilot Command Bar & Metric Auditor Gate (User Story 1 / Feature 007)', () => {
  it('opens dialog via button or Cmd+K and renders query input', async () => {
    render(
      <CockpitProvider>
        <CopilotCommandBar />
      </CockpitProvider>
    );

    // Trigger Cmd+K shortcut
    fireEvent.keyDown(window, { key: 'k', metaKey: true });

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(/Ask Copilot or type institutional command/i)
      ).toBeInTheDocument();
    });
  });

  it('submits query and displays verified metric auditor badge on successful egress', async () => {
    render(
      <CockpitProvider>
        <CopilotCommandBar forceOpen={true} />
      </CockpitProvider>
    );

    const input = screen.getAllByPlaceholderText(/Ask Copilot or type institutional command/i)[0];
    fireEvent.change(input, { target: { value: 'What is the LatAm spread impact?' } });

    const submitBtn = screen.getAllByRole('button', { name: /Submit Query/i })[0];
    const form = submitBtn.closest('form');
    if (form) {
      fireEvent.submit(form);
    } else {
      fireEvent.click(submitBtn);
    }

    await waitFor(() => {
      expect(screen.getByText(/AUDIT PASSED/i)).toBeInTheDocument();
      expect(screen.getByText(/LatAm spread widened/i)).toBeInTheDocument();
    });
  });
});
