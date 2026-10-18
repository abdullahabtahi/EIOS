"use client";

/**
 * Which model answers the next question. The backend lists the choices and names the default (the fastest one); the
 * operator's pick is remembered in this browser only. If the list cannot be read the picker is simply absent and the
 * backend default answers: nothing is guessed about which models exist.
 */

import * as React from "react";
import { authFetch } from "@/lib/auth/token";

export interface ModelChoice {
  key: string;
  label: string;
  note: string;
  default: boolean;
}

const STORAGE_KEY = "eios.copilot.model";

function remembered(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function remember(key: string) {
  try {
    window.localStorage.setItem(STORAGE_KEY, key);
  } catch {
    /* a convenience only; the choice still applies to this session */
  }
}

function parseChoices(body: unknown): ModelChoice[] {
  const raw = (body as { models?: unknown } | null)?.models;
  if (!Array.isArray(raw)) return [];
  return raw.filter(
    (m): m is ModelChoice =>
      !!m &&
      typeof m.key === "string" &&
      typeof m.label === "string" &&
      typeof m.note === "string",
  );
}

/** The model list and the current pick. `selected` is undefined until the list is known, so a question never names a model the backend did not offer. */
export function useModelChoice() {
  const [choices, setChoices] = React.useState<ModelChoice[]>([]);
  const [picked, setPicked] = React.useState<string | null>(null);

  React.useEffect(() => {
    let live = true;
    authFetch("/api/cockpit/copilot/models")
      .then((res) => (res.ok ? res.json() : null))
      .then((body) => {
        if (!live) return;
        setChoices(parseChoices(body));
        setPicked(remembered());
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);

  const selected =
    choices.find((c) => c.key === picked) ?? choices.find((c) => c.default);
  const select = (key: string) => {
    setPicked(key);
    remember(key);
  };
  return { choices, selected: selected?.key, select };
}

/**
 * The picker sits with the composer and opens upward, like the reference chat apps: the trigger names the model, each
 * option adds what it is good for, and the pick is a tick. Arrow keys, Enter and Escape work; a click elsewhere closes it.
 */
export function ModelPicker({
  choices,
  selected,
  onSelect,
}: {
  choices: ModelChoice[];
  selected: string | undefined;
  onSelect: (key: string) => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [active, setActive] = React.useState(0);
  const root = React.useRef<HTMLDivElement>(null);
  const trigger = React.useRef<HTMLButtonElement>(null);
  const listId = React.useId();

  React.useEffect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', away);
    return () => document.removeEventListener('pointerdown', away);
  }, [open]);

  if (choices.length < 2 || !selected) return null;
  const current = choices.find((c) => c.key === selected) ?? choices[0];

  const show = () => {
    setActive(Math.max(0, choices.findIndex((c) => c.key === selected)));
    setOpen(true);
  };
  const pick = (key: string) => {
    onSelect(key);
    setOpen(false);
    trigger.current?.focus();
  };
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && open) {
      e.preventDefault();
      e.stopPropagation();
      setOpen(false);
      trigger.current?.focus();
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!open) return show();
      setActive((i) => (e.key === 'ArrowDown' ? Math.min(i + 1, choices.length - 1) : Math.max(i - 1, 0)));
    } else if ((e.key === 'Enter' || e.key === ' ') && open) {
      e.preventDefault();
      pick(choices[active].key);
    }
  };

  return (
    <div ref={root} className="relative shrink-0" onKeyDown={onKeyDown}>
      <button
        ref={trigger}
        type="button"
        aria-label={`Model: ${current.label}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        onClick={() => (open ? setOpen(false) : show())}
        className="flex h-8 cursor-pointer items-center px-2 text-label text-cx-muted outline-none transition-colors hover:bg-cx-sub-2 hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-cx-accent"
      >
        {current.label}
      </button>
      {open && (
        <ul
          id={listId}
          role="listbox"
          aria-label="Model"
          aria-activedescendant={`${listId}-${active}`}
          className="absolute bottom-full right-0 z-40 mb-1 w-64 border border-cx-line bg-white py-1 shadow-lg"
        >
          {choices.map((c, i) => (
            <li
              key={c.key}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={c.key === selected}
              onPointerEnter={() => setActive(i)}
              onClick={() => pick(c.key)}
              className={`flex cursor-pointer items-start gap-2 px-3 py-1.5 ${i === active ? 'bg-cx-sub-2' : ''}`}
            >
              <span className="material-symbols-sharp mt-px w-4 shrink-0 text-sm leading-none text-cx-accent" aria-hidden="true">
                {c.key === selected ? 'check' : ''}
              </span>
              <span className="min-w-0">
                <span className="block text-xs font-medium text-cx-ink">{c.label}</span>
                <span className="block text-label text-cx-muted">{c.note}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
