import type { FatfList, GeoEvidence, GeoReference, GeoSelection, ReferenceIndicator } from './geo-types';

const USD = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 });

export const formatUsd = (value: number): string => USD.format(value);
const COUNT = new Intl.NumberFormat('en-US');
const FATF_LABEL: Readonly<Record<FatfList, string>> = {
  call_for_action: 'Call for action',
  increased_monitoring: 'Increased monitoring',
};
const INDICATOR_LABEL: Readonly<Record<string, string>> = {
  'NY.GDP.PCAP.CD': 'GDP per capita',
  'NY.GDP.MKTP.CD': 'GDP',
  'BX.TRF.PWKR.CD.DT': 'Remittances received',
  'IT.NET.USER.ZS': 'Internet users',
  'FS.AST.PRVT.GD.ZS': 'Private credit, % of GDP',
  'BN.CAB.XOKA.GD.ZS': 'Current account, % of GDP',
};
const NOT_RECORDED = 'Not recorded';
const capitalise = (word: string): string => word.charAt(0).toUpperCase() + word.slice(1);

function indicatorRow(i: ReferenceIndicator): readonly [string, string] {
  const label = INDICATOR_LABEL[i.code] ?? i.name;
  const percent = i.code.endsWith('.ZS');
  const shown = percent ? `${i.value.toFixed(1)}%` : formatUsd(i.value);
  return [label, `${shown} (${i.year})`];
}

export interface SelectionView {
  readonly title: string;
  readonly rows: readonly (readonly [label: string, value: string])[];
}

/** Resolves a selection to display text from the evidence itself; an unknown id yields null, never a guess. */
export function describeSelection(
  evidence: GeoEvidence,
  reference: GeoReference | null,
  selection: GeoSelection,
): SelectionView | null {
  if (!selection) return null;
  const name = (code: string) => evidence.jurisdictions.find((j) => j.code === code)?.name ?? code;
  if (selection.kind === 'country') {
    const c = reference?.countries.find((x) => x.iso2 === selection.id);
    if (!c) return null;
    return {
      title: c.name,
      rows: [
        ['FATF list', c.fatf_list ? FATF_LABEL[c.fatf_list] : 'Not listed'],
        ['Offshore entities incorporated', c.entities_incorporated === null ? NOT_RECORDED : COUNT.format(c.entities_incorporated)],
        ['Offshore entities linked', c.entities_linked === null ? NOT_RECORDED : COUNT.format(c.entities_linked)],
        ...c.indicators.map(indicatorRow),
      ],
    };
  }
  if (selection.kind === 'corridor') {
    const c = evidence.corridors.find((x) => x.id === selection.id);
    return c
      ? {
          title: `${name(c.origin)} → ${name(c.destination)}`,
          rows: [['Risk tier', capitalise(c.riskTier)], ['Volume', formatUsd(c.volumeUsd)], ['Accounts', String(c.accountCount)]],
        }
      : null;
  }
  const m = evidence.mismatches.find((x) => x.accountId === selection.id);
  return m
    ? {
        title: `Account ${m.accountId}`,
        rows: [['KYC country', name(m.kycCountry)], ['IP country', name(m.ipCountry)], ['Volume', formatUsd(m.volumeUsd)]],
      }
    : null;
}
