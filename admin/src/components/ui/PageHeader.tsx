interface PageHeaderProps {
  title: string
  subtitle?: string
  count?: number
  action?: React.ReactNode
}

export default function PageHeader({
  title,
  subtitle,
  count,
  action,
}: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
          {count !== undefined && (
            <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
              {count.toLocaleString()}
            </span>
          )}
        </div>
        {subtitle && (
          <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  )
}
