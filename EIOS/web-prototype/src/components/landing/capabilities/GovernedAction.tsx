"use client";

import React, { useCallback, useRef, useState } from "react";

interface Block {
  readonly seq: number;
  readonly action: string;
  readonly prev: string;
  readonly hash: string;
}

const GENESIS = "0".repeat(64);

async function sha256(text: string): Promise<string> {
  if (!globalThis.crypto?.subtle) throw new Error("crypto.subtle is unavailable on an insecure origin");
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

type Stage = "proposed" | "signed" | "approved";

/** The proposal text is the recorded live turn geo_propose_hold (2026-10-18); hashes are computed in your browser. */
export function GovernedAction() {
  const [stage, setStage] = useState<Stage>("proposed");
  const [refusal, setRefusal] = useState<string | null>(null);
  const [chain, setChain] = useState<readonly Block[]>([]);

  const sign = () => {
    setRefusal(null);
    setStage("signed");
  };

  const approveAsProposer = () => {
    setRefusal("Refused: the proposer cannot approve their own intent. A second operator must.");
  };

  const approving = useRef(false);

  const approveAsSecond = useCallback(async () => {
    if (approving.current) return;
    approving.current = true;
    setRefusal(null);
    try {
      const prev = chain.length ? chain[chain.length - 1].hash : GENESIS;
      const seq = chain.length + 1;
      const action = "HOLD W-84920-1 · CR84920";
      const hash = await sha256(JSON.stringify({ seq, action, prev }));
      setChain((c) => [...c, { seq, action, prev, hash }]);
      setStage("approved");
    } catch (err) {
      console.error("landing ledger demo could not hash", err);
      setRefusal("This browser cannot compute the SHA-256 hash here (it needs a secure https page), so the demo ledger stays empty.");
    } finally {
      approving.current = false;
    }
  }, [chain]);

  const reset = () => {
    setStage("proposed");
    setRefusal(null);
  };

  return (
    <figure className="fde-viz">
      <ol className="fde-gov">
        <li className="is-done">
          <span className="fde-gov-n">01</span>
          <p className="fde-gov-name">Agent proposes</p>
          <p className="fde-gov-quote">
            &ldquo;A hold has been proposed for withdrawal W-84920-1 on account CR84920. A second operator must approve it in the
            approvals area.&rdquo;
          </p>
        </li>
        <li className={stage !== "proposed" ? "is-done" : "is-next"}>
          <span className="fde-gov-n">02</span>
          <p className="fde-gov-name">Intent hub validates, Cloud KMS signs</p>
          <p className="fde-gov-body">ECDSA P-256 over the intent and its evidence bundle id. The intent expires.</p>
          {stage === "proposed" && (
            <button type="button" className="fde-chipbtn" onClick={sign}>
              Stage and sign
            </button>
          )}
        </li>
        <li className={stage === "approved" ? "is-done" : stage === "signed" ? "is-next" : ""}>
          <span className="fde-gov-n">03</span>
          <p className="fde-gov-name">Four-eyes approval</p>
          <p className="fde-gov-body">Nothing executes on the agent&apos;s word, or on one person&apos;s.</p>
          {stage === "signed" && (
            <span className="fde-gov-actions">
              <button type="button" className="fde-chipbtn" onClick={approveAsProposer}>
                Approve as the proposer
              </button>
              <button type="button" className="fde-chipbtn is-primary" onClick={() => void approveAsSecond()}>
                Approve as a second operator
              </button>
            </span>
          )}
          {refusal && (
            <p className="fde-gov-refusal" role="alert">
              {refusal}
            </p>
          )}
        </li>
        <li className={stage === "approved" ? "is-done" : ""}>
          <span className="fde-gov-n">04</span>
          <p className="fde-gov-name">Written to the WORM ledger</p>
          <p className="fde-gov-body">Monotonic sequence, each entry chained to the last by SHA-256.</p>
          {stage === "approved" && (
            <button type="button" className="fde-chipbtn" onClick={reset}>
              Propose another
            </button>
          )}
        </li>
      </ol>

      <div className="fde-ledger-chain" aria-live="polite" aria-label="Ledger entries">
        {chain.length === 0 && <p className="fde-ledger-empty">The ledger is empty until two people agree.</p>}
        {chain.map((b) => (
          <div key={b.seq} className="fde-block">
            <span className="fde-block-seq">#{b.seq}</span>
            <span className="fde-block-act">{b.action}</span>
            <span className="fde-block-hash" title={b.hash}>
              prev {b.prev.slice(0, 10)}… → {b.hash.slice(0, 16)}…
            </span>
          </div>
        ))}
      </div>
      <figcaption className="fde-viz-cap">
        The proposal is a recorded live turn. The signing and approval steps mirror the intent hub&apos;s rules; the ledger hashes
        shown here are computed in your browser, not by Cloud KMS.
      </figcaption>
    </figure>
  );
}
