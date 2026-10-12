/**
 * Canonical list of cockpit workstations (persona roles) shared by the
 * header persona strip and the global navigation rail.
 */

import type { PersonaRole } from '../state/cockpit-types';

export interface WorkstationRoleDef {
  readonly id: PersonaRole;
  readonly label: string;
  readonly icon: string;
  readonly shortcut: string;
}

export const WORKSTATION_ROLES: readonly WorkstationRoleDef[] = [
  { id: 'executive', label: 'Executive', icon: 'monitoring', shortcut: '1' },
  { id: 'aml_investigator', label: 'AML Investigator', icon: 'security', shortcut: '2' },
  { id: 'partner_manager', label: 'Partner Manager', icon: 'hub', shortcut: '3' },
  { id: 'compliance_auditor', label: 'Compliance & Audit', icon: 'verified_user', shortcut: '4' },
  { id: 'data_operations', label: 'Data Operations', icon: 'tune', shortcut: '5' },
];
