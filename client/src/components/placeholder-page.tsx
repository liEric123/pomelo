import type { ReactNode } from 'react'

type PlaceholderPageProps = {
  title: string
  description: ReactNode
}

export function PlaceholderPage({
  title,
  description,
}: PlaceholderPageProps) {
  return (
    <section className="space-y-6">
      <div className="type-kicker inline-flex items-center rounded-full border border-border bg-surfaceAlt px-3 py-1">
        Placeholder
      </div>
      <div className="space-y-4">
        <h2 className="type-display-page max-w-3xl">{title}</h2>
        <p className="type-body max-w-2xl">
          {description}
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-3xl border border-border bg-surfaceAlt p-5">
          <p className="type-meta">Flow</p>
          <p className="type-stat mt-3">
            Ready for feature wiring
          </p>
        </div>
        <div className="rounded-3xl border border-border bg-surfaceAlt p-5">
          <p className="type-meta">State</p>
          <p className="type-stat mt-3">
            Shared theme applied
          </p>
        </div>
        <div className="rounded-3xl border border-border bg-surfaceAlt p-5">
          <p className="type-meta">Next</p>
          <p className="type-stat mt-3">
            Connect real data sources
          </p>
        </div>
      </div>
    </section>
  )
}
