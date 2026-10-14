import type { PersonaRole } from '../state/cockpit-types';

export interface ChatEntity {
  id: string;
  kind: 'PARTNER' | 'ACCOUNT' | string;
}

const ABOUT = 'What can you do?';

/**
 * A few starting questions for the workstation and the entity on screen. Fixed templates, so a suggestion never costs
 * a model call and never names a thing the operator is not looking at. Each question maps to a tool the role has.
 */
export function suggestedQuestions(role: PersonaRole, entity: ChatEntity | null): string[] {
  const partner = entity?.kind === 'PARTNER' ? entity.id : null;
  const account = entity?.kind === 'ACCOUNT' ? entity.id : null;
  switch (role) {
    case 'partner_manager':
      return [
        ...(partner ? [`Why is ${partner} at risk?`] : []),
        'Which partners need my attention?',
        ...(partner ? [] : ['Give me a brief on the partner ecosystem']),
        ABOUT,
      ];
    case 'aml_investigator':
      return [
        ...(account ? [`Brief me on ${account}`] : []),
        'Show the open alerts',
        ABOUT,
      ];
    case 'executive':
      return ['Give me the morning briefing', 'What is our net revenue?', 'Is the spread cut causing churn?', ABOUT];
    case 'compliance_auditor':
      return ['Verify the ledger hash chain', 'Show the ledger timeline', ABOUT];
    case 'data_operations':
      return ['How is data quality right now?', ABOUT];
    default:
      return [ABOUT];
  }
}
