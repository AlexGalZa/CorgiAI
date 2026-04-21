import { cn } from '@/lib/utils'

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizes = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-[3px]',
}

export default function Spinner({ size = 'md', className }: SpinnerProps) {
  return (
    <div
      className={cn(
        'animate-spin rounded-full border-gray-200 border-t-[#ff5c00]',
        sizes[size],
        className,
      )}
    />
  )
}

/** Centered spinner inside a container of given height. */
export function SpinnerOverlay({ height = 'h-64' }: { height?: string }) {
  return (
    <div className={cn('flex items-center justify-center', height)}>
      <Spinner size="lg" />
    </div>
  )
}
