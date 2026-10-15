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

export function ModelPicker({
  choices,
  selected,
  onSelect,
}: {
  choices: ModelChoice[];
  selected: string | undefined;
  onSelect: (key: string) => void;
}) {
  if (choices.length < 2 || !selected) return null;
  return (
    <label className="flex items-center gap-1 text-label text-cx-muted shrink-0">
      <span className="sr-only">Model</span>
      <select
        aria-label="Model"
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
        className="bg-white border border-cx-line text-cx-ink text-label py-0.5 pl-1.5 pr-1 cursor-pointer hover:border-blue-500"
        title={choices.find((c) => c.key === selected)?.note}
      >
        {choices.map((c) => (
          <option key={c.key} value={c.key}>
            {c.label} · {c.note}
          </option>
        ))}
      </select>
    </label>
  );
}
