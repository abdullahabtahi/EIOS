import type { Metadata } from "next";
import { LandingPage } from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "EIOS: a governed intelligence layer, built in the field",
  description:
    "A forward-deployed engineering case study: an AML, partner and executive intelligence system for a financial institution, with every figure traced, every action signed and every result measured against planted truth.",
};

export default function Page() {
  return <LandingPage />;
}
