import Link from "next/link";
import React from "react";

export function Close() {
  return (
    <section className="fde-close" aria-labelledby="fde-close-title">
      <h2 id="fde-close-title" className="fde-close-title" data-reveal>
        Every number traced. Every action signed.
      </h2>
      <div className="fde-close-actions" data-reveal>
        <Link href="/cockpit" className="fde-button">
          Open the workstation <span aria-hidden="true">→</span>
        </Link>
        <p className="fde-note">
          Reviewer accounts are on the sign-in page. Client activity in the workstations is synthetic; the reference layers and
          regulatory documents are real and public.
        </p>
      </div>
      <footer className="fde-footer">
        <div className="fde-credit" data-reveal>
          {/* eslint-disable-next-line @next/next/no-img-element -- small static logo */}
          <img src="/landing/ai-builder-cup.webp" alt="AI Builder Cup by Google Cloud and Hack2skill" width={430} height={222} loading="lazy" />
          <p>
            Built for the AI Builder Cup, Google Cloud&apos;s JAPAC hackathon run with Hack2skill. Every Google Cloud service named
            on this page is provisioned in the repo&apos;s infrastructure or called from its code.
          </p>
        </div>
        <div className="fde-footer-base">
          <span>EIOS</span>
          <span>
            Client data is synthetic with a planted answer key. Results are measured against that key, not production traffic.
          </span>
          <a href="#top">Back to top ↑</a>
        </div>
      </footer>
    </section>
  );
}
