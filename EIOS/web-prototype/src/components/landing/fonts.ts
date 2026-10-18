import { Schibsted_Grotesk } from "next/font/google";

/** Display and UI voice of the landing page: a Nordic grotesque with squared terminals (variable font). */
export const landingSans = Schibsted_Grotesk({
  subsets: ["latin"],
  variable: "--fde-sans",
  display: "swap",
});
