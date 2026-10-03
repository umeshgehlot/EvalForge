import Link from "next/link";

const navLinks = [
  { href: "/datasets", label: "Datasets" },
  { href: "/app-versions", label: "App Versions" },
  { href: "/scorers", label: "Scorers" },
  { href: "/runs", label: "Eval Runs" },
  { href: "/benchmark", label: "Benchmark" },
];

export function Navbar() {
  return (
    <nav className="border-b bg-background sticky top-0 z-50">
      <div className="container mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="font-semibold text-lg tracking-tight">
          EvalForge
        </Link>
        <div className="flex items-center gap-6 text-sm">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
