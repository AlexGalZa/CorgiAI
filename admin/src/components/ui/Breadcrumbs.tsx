import { Link } from 'react-router-dom'
import { ChevronRight, Home } from 'lucide-react'

export interface BreadcrumbItem {
  label: string
  href?: string
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[]
}

export default function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav className="mb-4 flex items-center gap-1.5 text-xs text-gray-500">
      <Link
        to="/dashboard"
        className="flex items-center gap-1 transition-colors hover:text-[#ff5c00]"
      >
        <Home className="h-3 w-3" />
        <span>Dashboard</span>
      </Link>
      {items.map((item, i) => {
        const isLast = i === items.length - 1
        return (
          <span key={i} className="flex items-center gap-1.5">
            <ChevronRight className="h-3 w-3 text-gray-300" />
            {isLast || !item.href ? (
              <span className="font-medium text-gray-700">{item.label}</span>
            ) : (
              <Link
                to={item.href}
                className="transition-colors hover:text-[#ff5c00]"
              >
                {item.label}
              </Link>
            )}
          </span>
        )
      })}
    </nav>
  )
}
