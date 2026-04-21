import { forwardRef, useId } from 'react'
import { Check, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CheckboxProps {
  checked?: boolean
  indeterminate?: boolean
  onChange?: (checked: boolean) => void
  label?: string
  disabled?: boolean
  className?: string
  id?: string
  name?: string
}

/**
 * Custom checkbox matching the app's design system.
 *
 * - Unchecked: white bg, gray-300 border, rounded-md
 * - Checked: primary-500 bg, white check icon, no border visible
 * - Indeterminate: primary-500 bg, white minus icon
 * - Hover: ring highlight
 * - Focus: ring-2 ring-primary-500/30
 * - Disabled: opacity-50
 *
 * Works as controlled (checked + onChange) or uncontrolled via ref.
 */
const Checkbox = forwardRef<HTMLButtonElement, CheckboxProps>(
  (
    {
      checked = false,
      indeterminate = false,
      onChange,
      label,
      disabled = false,
      className,
      id: externalId,
      name,
    },
    ref,
  ) => {
    const autoId = useId()
    const id = externalId ?? autoId

    const isOn = indeterminate || checked

    return (
      <div className={cn('inline-flex items-center gap-2.5', className)}>
        {name && (
          <input type="hidden" name={name} value={checked ? 'true' : 'false'} />
        )}
        <button
          ref={ref}
          id={id}
          type="button"
          role="checkbox"
          aria-checked={indeterminate ? 'mixed' : checked}
          aria-label={label ?? undefined}
          disabled={disabled}
          onClick={() => onChange?.(!checked)}
          className={cn(
            'relative flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-md border-[1.5px] transition-all',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/30 focus-visible:ring-offset-1',
            disabled && 'cursor-not-allowed opacity-50',
            isOn
              ? 'border-primary-500 bg-primary-500 hover:border-primary-600 hover:bg-primary-600'
              : 'border-gray-300 bg-white hover:border-gray-400 hover:bg-gray-50',
          )}
        >
          {indeterminate ? (
            <Minus className="h-3 w-3 text-white" strokeWidth={3} />
          ) : checked ? (
            <Check className="h-3 w-3 text-white" strokeWidth={3} />
          ) : null}
        </button>
        {label && (
          <label
            htmlFor={id}
            className={cn(
              'cursor-pointer select-none text-sm text-gray-700',
              disabled && 'cursor-not-allowed opacity-50',
            )}
          >
            {label}
          </label>
        )}
      </div>
    )
  },
)

Checkbox.displayName = 'Checkbox'
export default Checkbox
