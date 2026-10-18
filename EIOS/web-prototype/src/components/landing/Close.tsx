import Link from "next/link";
import React from "react";
import { landingAsset } from "./assets";
import { APP_HOME_HREF } from "@/components/cockpit/shell/app-nav-items";

export function Close() {
  return (
    <section className="fde-close" aria-labelledby="fde-close-title">
      <h2 id="fde-close-title" className="fde-close-title" data-reveal>
        Every number traced. Every action signed.
      </h2>
      <div className="fde-close-actions" data-reveal>
        <Link href={APP_HOME_HREF} className="fde-button">
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
          <img src={landingAsset("ai-builder-cup.webp")} alt="AI Builder Cup by Google Cloud and Hack2skill" width={430} height={222} loading="lazy" />
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
          <span className="fde-footer-links">
            <a href="#top">Back to top ↑</a>
            <a
              href="https://www.linkedin.com/in/abdullahabtahi/"
              className="fde-social"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Abdullah Abtahi on LinkedIn"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
                <rect x="2.5" y="2.5" width="19" height="19" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="8" cy="8.2" r="1.3" fill="currentColor" />
                <path
                  d="M6.9 10.5h2.2V17H6.9zM11 10.5h2.1v.9c.4-.7 1.2-1.1 2.1-1.1 1.9 0 2.8 1.2 2.8 3.1V17h-2.2v-3.2c0-.9-.3-1.5-1.1-1.5-.9 0-1.5.6-1.5 1.6V17H11z"
                  fill="currentColor"
                />
              </svg>
            </a>
          </span>
        </div>
      </footer>
    </section>
  );
}
