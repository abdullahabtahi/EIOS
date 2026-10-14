import { describe, expect, it } from 'vitest';
import { metricLabel } from '@/lib/server/normalize';

describe('metricLabel', () => {
  it('reads the last part of an assistant fact id as words', () => {
    expect(metricLabel('partner.signals:PTR-723:days_to_intervention_deadline')).toBe('days to intervention deadline');
    expect(metricLabel('partner.worklist:partners[0].expected_loss_usd')).toBe('expected loss');
  });

  it('leaves a name that is already words alone', () => {
    expect(metricLabel('Governed Net Revenue')).toBe('Governed Net Revenue');
  });
});
