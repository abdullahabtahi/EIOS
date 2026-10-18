import type { ReactNode } from "react";

/**
 * The cockpit draws its icons with the Material Symbols font. The landing page and sign-in do not,
 * so the stylesheet loads here instead of blocking first paint on every route.
 * `precedence` lets React hoist and de-duplicate the link into the document head.
 */
const MATERIAL_SYMBOLS =
  "https://fonts.googleapis.com/css2?family=Material+Symbols+Sharp:opsz,wght,FILL,GRAD@20..48,300..400,0,0&display=swap";

export default function CockpitLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link rel="stylesheet" href={MATERIAL_SYMBOLS} precedence="default" />
      {children}
    </>
  );
}
