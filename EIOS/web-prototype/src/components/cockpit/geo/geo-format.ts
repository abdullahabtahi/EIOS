import { BAND_LABEL } from './geo-basis';
import type { BaselScore, FatfList, GeoFlows, GeoReference, GeoSelection, ReferenceIndicator } from './geo-types';

// Digits are pinned: the default minimum differs between ICU versions ($900K here, $900.0K on another Node).
const USD = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', minimumFractionDigits: 0, maximumFractionDigits: 1 });

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
const NOT_IN_INDEX = 'Not in the public index';

const baselText = (b: BaselScore | null): string => (b ? `${b.score.toFixed(2)} of 10 · ${BAND_LABEL[b.band]} · rank ${b.rank} of ${b.of}` : NOT_IN_INDEX);

/** P-4: the offshore counts come from a leak database; being in it says nothing about the entity. Said once, in the legend of the offshore layer. */
export const OFFSHORE_NOTICE = 'Counts of entities in the ICIJ Offshore Leaks Database. Appearing there is not evidence of wrongdoing.';
export const ICIJ_URL = 'https://offshoreleaks.icij.org';

const TIER_LABEL = { high: 'High', medium: 'Medium', low: 'Low' } as const;

/** A country's display name from the reference layer; its code when the layer is absent or does not know it. */
export const nameOf = (reference: GeoReference | null, code: string): string =>
  reference?.countries.find((c) => c.iso2 === code)?.name ?? code;
export const FATF_TEXT = FATF_LABEL;
export const tierText = (tier: keyof typeof TIER_LABEL | null): string => (tier ? TIER_LABEL[tier] : 'Unrated');

function indicatorRow(i: ReferenceIndicator): readonly [string, string] {
  const label = INDICATOR_LABEL[i.code] ?? i.name;
  const percent = i.code.endsWith('.ZS');
  const shown = percent ? `${i.value.toFixed(1)}%` : formatUsd(i.value);
  return [label, `${shown} (${i.year})`];
}

export interface SelectionView {
  readonly title: string;
  readonly rows: readonly (readonly [label: string, value: string])[];
  /** Accounts behind this mark, each of which can be opened. */
  readonly accounts?: readonly string[];
  readonly note?: string;
}

const REGIONS = typeof Intl !== 'undefined' && 'DisplayNames' in Intl ? new Intl.DisplayNames(['en'], { type: 'region' }) : null;

/** A country's English name from its ISO code without any data fetch; the code itself when the runtime cannot name it. */
export function regionName(code: string): string {
  try {
    return REGIONS?.of(code) ?? code;
  } catch {
    return code;
  }
}

/** Resolves a selection to display text from the data itself; an unknown id yields null, never a guess. */
export function describeSelection(
  flows: GeoFlows | null,
  reference: GeoReference | null,
  selection: GeoSelection,
): SelectionView | null {
  if (!selection) return null;
  const name = (code: string) => nameOf(reference, code);
  if (selection.kind === 'country') {
    const c = reference?.countries.find((x) => x.iso2 === selection.id);
    if (!c) return null;
    return {
      title: c.name,
      rows: [
        ['FATF list', c.fatf_list ? FATF_LABEL[c.fatf_list] : 'Not listed'],
        ['EU high-risk list', c.eu_high_risk ? 'Listed' : 'Not listed'],
        ['Basel AML Index', baselText(c.basel)],
        ['Offshore entities incorporated', c.entities_incorporated === null ? NOT_RECORDED : COUNT.format(c.entities_incorporated)],
        ['Offshore entities linked', c.entities_linked === null ? NOT_RECORDED : COUNT.format(c.entities_linked)],
        ...c.indicators.map(indicatorRow),
      ],
    };
  }
  if (selection.kind === 'corridor') {
    const c = flows?.corridors.find((x) => `${x.origin}>${x.destination}` === selection.id);
    return c
      ? {
          title: `${name(c.origin)} → ${name(c.destination)}`,
          rows: [
            ['Risk tier', tierText(c.tier)],
            ['Volume', formatUsd(c.volume_usd)],
            ['Accounts', COUNT.format(c.accounts)],
            ['Payments', COUNT.format(c.events)],
          ],
        }
      : null;
  }
  if (selection.kind === 'gateway') {
    const g = flows?.gateways?.find((x) => x.gateway_id === selection.id);
    if (!g) return null;
    const from = g.home_countries.map((h) => `${name(h.iso2)} ${h.accounts}`).join(', ');
    return {
      title: `Shared exit in ${name(g.country)}`,
      rows: [
        ['Gateway', g.gateway_id],
        ['Accounts using it', COUNT.format(g.accounts)],
        ['Registered in', from],
        ['Impossible jumps', COUNT.format(g.impossible_jumps)],
      ],
      accounts: g.sample_accounts,
      note:
        flows?.hubs_suppressed != null
          ? `None of these accounts lives in ${name(g.country)}. ${COUNT.format(flows.hubs_suppressed)} gateway${flows.hubs_suppressed === 1 ? '' : 's'} shared by more than 100 accounts ${flows.hubs_suppressed === 1 ? 'was' : 'were'} set aside as hubs (RL-4).`
          : undefined,
    };
  }
  if (selection.kind !== 'mismatch') return null;
  const p = flows?.mismatch_pairs.find((x) => `${x.kyc_country}>${x.ip_country}` === selection.id);
  return p
    ? {
        title: `Registered in ${name(p.kyc_country)}, logging in from ${name(p.ip_country)}`,
        rows: [
          ['Flagged accounts', COUNT.format(p.accounts)],
          ['Foreign logins', `${COUNT.format(p.foreign_events)} of ${COUNT.format(p.events)}`],
          ['Volume', formatUsd(p.volume_usd)],
          ['Examples', p.sample_accounts.join(', ')],
        ],
        accounts: p.sample_accounts,
      }
    : null;
}
