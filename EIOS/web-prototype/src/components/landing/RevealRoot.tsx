"use client";

import React, { useRef } from "react";
import { useReveal } from "./hooks";

/** The one client boundary of the page shell: arms scroll reveals for its server-rendered children. */
export function RevealRoot({ className, children }: { className: string; children: React.ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  useReveal(root);
  return (
    <div ref={root} id="top" className={className}>
      {children}
    </div>
  );
}
