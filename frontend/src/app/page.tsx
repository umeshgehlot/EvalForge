export default function Home() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">EvalForge</h1>
        <p className="text-muted-foreground mt-1">
          LLM Evals &amp; Observability Dashboard
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Datasets", href: "/datasets", description: "Upload and manage Q&A evaluation datasets" },
          { label: "App Versions", href: "/app-versions", description: "Register and track your LLM app versions" },
          { label: "Scorers", href: "/scorers", description: "Configure deterministic, programmatic, and LLM-judge scorers" },
          { label: "Eval Runs", href: "/runs", description: "Run evaluations and explore results" },
          { label: "Benchmark", href: "/benchmark", description: "Track pass-rate history and detect regressions over time" },
        ].map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="rounded-lg border p-6 hover:bg-accent transition-colors"
          >
            <h2 className="font-semibold">{item.label}</h2>
            <p className="text-sm text-muted-foreground mt-1">{item.description}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
