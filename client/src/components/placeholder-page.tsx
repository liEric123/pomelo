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
      <div className="inline-flex items-center rounded-full border border-border bg-surfaceAlt px-3 py-1 text-sm font-medium text-textSecondary">
        Placeholder
      </div>
      <div className="space-y-3">
        <h2 className="text-3xl font-semibold text-textPrimary">{title}</h2>
        <p className="max-w-2xl text-base leading-7 text-textSecondary">
          {description}
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-3xl border border-border bg-surfaceAlt p-5">
          <p className="text-sm text-textSecondary">Flow</p>
          <p className="mt-2 text-lg font-semibold text-textPrimary">
            Ready for feature wiring
          </p>
        </div>
        <div className="rounded-3xl border border-border bg-surfaceAlt p-5">
          <p className="text-sm text-textSecondary">State</p>
          <p className="mt-2 text-lg font-semibold text-textPrimary">
            Shared theme applied
          </p>
        </div>
        <div className="rounded-3xl border border-border bg-surfaceAlt p-5">
          <p className="text-sm text-textSecondary">Next</p>
          <p className="mt-2 text-lg font-semibold text-textPrimary">
            Connect real data sources
          </p>
        </div>
      </div>
    </section>
  )
}
