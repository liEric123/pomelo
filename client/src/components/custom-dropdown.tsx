import { useEffect, useMemo, useRef, useState } from 'react'

type DropdownOption = {
  value: string
  label: string
}

type CustomDropdownProps = {
  value: string
  options: DropdownOption[]
  onChange: (value: string) => void
  className?: string
}

export function CustomDropdown({
  value,
  options,
  onChange,
  className,
}: CustomDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  const selectedOption = useMemo(
    () => options.find((option) => option.value === value) ?? options[0] ?? null,
    [options, value],
  )

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    window.addEventListener('mousedown', handlePointerDown)
    window.addEventListener('keydown', handleEscape)

    return () => {
      window.removeEventListener('mousedown', handlePointerDown)
      window.removeEventListener('keydown', handleEscape)
    }
  }, [])

  return (
    <div ref={rootRef} className={className}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
        className="font-ui flex w-full items-center justify-between rounded-2xl border border-border bg-surface px-4 py-3 text-sm text-textPrimary outline-none transition hover:border-accentSecondary hover:bg-accentSecondary/12 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20"
      >
        <span className="truncate text-left">{selectedOption?.label ?? 'Select'}</span>
        <span
          className={[
            'ml-3 shrink-0 text-textSecondary transition-transform duration-200',
            isOpen ? 'rotate-180' : '',
          ].join(' ')}
        >
          ▾
        </span>
      </button>

      {isOpen ? (
        <div className="relative">
          <div className="absolute left-0 right-0 top-2 z-20 overflow-hidden rounded-[1.35rem] border border-border bg-surface shadow-[0_18px_45px_rgba(139,111,99,0.16)]">
            <div role="listbox" className="max-h-72 overflow-y-auto p-2">
              {options.map((option) => {
                const isSelected = option.value === value

                return (
                  <button
                    key={option.value}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => {
                      onChange(option.value)
                      setIsOpen(false)
                    }}
                    className={[
                      'font-ui flex w-full items-center justify-between rounded-[1rem] px-3 py-2.5 text-left text-sm transition',
                      isSelected
                        ? 'bg-accentPrimary/14 text-textPrimary'
                        : 'text-textSecondary hover:bg-surfaceAlt hover:text-textPrimary',
                    ].join(' ')}
                  >
                    <span>{option.label}</span>
                    {isSelected ? (
                      <span className="ml-3 shrink-0 text-xs font-semibold uppercase tracking-[0.16em] text-accentPrimary">
                        Selected
                      </span>
                    ) : null}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
