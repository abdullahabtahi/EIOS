import Link from "next/link";

const LINKS = [
  { href: "#system", label: "The system" },
  { href: "#capabilities", label: "Capabilities" },
  { href: "#geo", label: "Geospatial" },
  { href: "#product", label: "Product" },
  { href: "#architecture", label: "Architecture" },
  { href: "#results", label: "Results" },
] as const;

export function SiteNav() {
  return (
    <header className="fde-nav">
      <Link href="/" className="fde-wordmark" aria-label="EIOS home">
        EIOS
      </Link>
      <nav aria-label="Case study sections" className="fde-nav-links">
        {LINKS.map((l) => (
          <a key={l.href} href={l.href}>
            {l.label}
          </a>
        ))}
      </nav>
      <Link href="/cockpit" className="fde-nav-cta">
        Open the workstation <span aria-hidden="true">→</span>
      </Link>
    </header>
  );
}
