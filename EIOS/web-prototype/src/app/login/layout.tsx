import type { ReactNode } from "react";
import { landingSans } from "@/components/landing/fonts";

/** The sign-in wears the landing's type: the font variable is set here, on the server, so the page stays testable. */
export default function LoginLayout({ children }: { children: ReactNode }) {
  return <div className={landingSans.variable}>{children}</div>;
}
