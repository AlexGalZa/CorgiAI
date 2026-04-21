import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  FileText,
  Shield,
  AlertTriangle,
  CreditCard,
  Users,
  Building2,
  BarChart3,
  UserCircle,
  ChevronLeft,
  ChevronRight,
  FolderOpen,
  DollarSign,
  Briefcase,
  Inbox,
  LayoutList,
  X,
  Blocks,
  Receipt,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import logo from '@/../assets/full-logo.svg'
import logoSmall from '@/../assets/small-logo.svg'

// ─── Nav definition ──────────────────────────────────────────────────────────

interface NavItem {
  label: string
  to: string
  icon: React.ComponentType<{ className?: string }>
}

interface NavGroup {
  title?: string
  items: NavItem[]
}

// ─── BDR Nav: Sales-focused, read-only except creating requests ──────────────

const bdrNav: NavGroup[] = [
  {
    items: [
      { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Pipeline',
    items: [
      { label: 'Brokered Requests', to: '/brokered-requests', icon: Inbox },
      { label: 'Quotes', to: '/quotes', icon: FileText },
      { label: 'Policies', to: '/policies', icon: Shield },
      { label: 'Claims', to: '/claims', icon: AlertTriangle },
    ],
  },
  {
    items: [
      { label: 'Profile', to: '/profile', icon: UserCircle },
    ],
  },
]

// ─── AE Nav: Full operational access ─────────────────────────────────────────

const aeNav: NavGroup[] = [
  {
    items: [
      { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Underwriting',
    items: [
      { label: 'Brokered Requests', to: '/brokered-requests', icon: Inbox },
      { label: 'Quotes', to: '/quotes', icon: FileText },
      { label: 'Policies', to: '/policies', icon: Shield },
      { label: 'Claims', to: '/claims', icon: AlertTriangle },
    ],
  },
  {
    title: 'Administration',
    items: [
      { label: 'Organizations', to: '/organizations', icon: Building2 },
      { label: 'Users', to: '/users', icon: Users },
      { label: 'Form Builder', to: '/form-builder', icon: Blocks },
      { label: 'Reports', to: '/reports', icon: BarChart3 },
    ],
  },
  {
    items: [
      { label: 'Profile', to: '/profile', icon: UserCircle },
    ],
  },
]

// ─── Finance Nav: Payments/transactions focused ──────────────────────────────

const financeNav: NavGroup[] = [
  {
    items: [
      { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Finance',
    items: [
      { label: 'Payments', to: '/payments', icon: CreditCard },
      { label: 'Commissions', to: '/commissions', icon: Receipt },
      { label: 'Policy Transactions', to: '/policies', icon: DollarSign },
      { label: 'Brokered Requests', to: '/brokered-requests', icon: Inbox },
    ],
  },
  {
    title: 'Insights',
    items: [
      { label: 'Reports', to: '/reports', icon: BarChart3 },
    ],
  },
  {
    items: [
      { label: 'Profile', to: '/profile', icon: UserCircle },
    ],
  },
]

// ─── Broker Nav: Own pipeline only ───────────────────────────────────────────

const brokerNav: NavGroup[] = [
  {
    items: [
      { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Portfolio',
    items: [
      { label: 'Pipeline', to: '/brokered-requests', icon: LayoutList },
      { label: 'My Quotes', to: '/quotes', icon: FileText },
      { label: 'My Policies', to: '/policies', icon: Shield },
      { label: 'Certificates', to: '/certificates', icon: FolderOpen },
    ],
  },
  {
    title: 'Clients',
    items: [
      { label: 'Organizations', to: '/organizations', icon: Building2 },
      { label: 'Users', to: '/users', icon: Users },
    ],
  },
  {
    items: [
      { label: 'Profile', to: '/profile', icon: UserCircle },
    ],
  },
]

// ─── Admin Nav: Everything ───────────────────────────────────────────────────

const adminNav: NavGroup[] = [
  {
    items: [
      { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
    ],
  },
  {
    title: 'Underwriting',
    items: [
      { label: 'Brokered Requests', to: '/brokered-requests', icon: Inbox },
      { label: 'Quotes', to: '/quotes', icon: FileText },
      { label: 'Policies', to: '/policies', icon: Shield },
      { label: 'Claims', to: '/claims', icon: AlertTriangle },
    ],
  },
  {
    title: 'Finance',
    items: [
      { label: 'Payments', to: '/payments', icon: CreditCard },
      { label: 'Commissions', to: '/commissions', icon: Receipt },
      { label: 'Certificates', to: '/certificates', icon: FolderOpen },
    ],
  },
  {
    title: 'Administration',
    items: [
      { label: 'Users', to: '/users', icon: Users },
      { label: 'Organizations', to: '/organizations', icon: Building2 },
      { label: 'Producers', to: '/producers', icon: Briefcase },
      { label: 'Reports', to: '/reports', icon: BarChart3 },
    ],
  },
  {
    items: [
      { label: 'Profile', to: '/profile', icon: UserCircle },
    ],
  },
]

function getNavGroups(role: string | undefined): NavGroup[] {
  switch (role) {
    case 'bdr':
      return bdrNav
    case 'ae':
    case 'ae_underwriting':
      return aeNav
    case 'finance':
      return financeNav
    case 'broker':
      return brokerNav
    case 'admin':
      return adminNav
    default:
      return aeNav
  }
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const user = useAuthStore((s) => s.user)
  // Superusers get the full admin nav regardless of role
  const groups = user?.is_superuser ? getNavGroups('admin') : getNavGroups(user?.role)
  const location = useLocation()
  const mobileSidebarOpen = useUIStore((s) => s.mobileSidebarOpen)
  const closeMobileSidebar = useUIStore((s) => s.closeMobileSidebar)

  // Auto-close mobile sidebar on navigation
  useEffect(() => {
    closeMobileSidebar()
  }, [location.pathname, closeMobileSidebar])

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="flex h-14 items-center justify-between border-b border-gray-100 px-3">
        <div className="flex items-center justify-center flex-1">
          {collapsed ? (
            <img src={logoSmall} alt="Corgi" className="h-6 w-6 object-contain" />
          ) : (
            <img src={logo} alt="Corgi Insurance" className="h-6" />
          )}
        </div>
        {/* Close button visible only on mobile overlay */}
        <button
          onClick={closeMobileSidebar}
          className="lg:hidden rounded-lg p-1 text-gray-400 hover:text-gray-600"
          aria-label="Close menu"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto scrollbar-hide scrollbar-dark px-2 py-3">
        {groups.map((group, gi) => (
          <div key={gi}>
            {/* Section label */}
            {group.title && !collapsed && (
              <p className="mb-1 mt-4 px-3 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
                {group.title}
              </p>
            )}
            {group.title && collapsed && <div className="my-2 border-t border-gray-100" />}

            {/* Items */}
            {group.items.map((item) => {
              const isActive = location.pathname === item.to ||
                (item.to !== '/dashboard' && location.pathname.startsWith(item.to + '/'))
              return (
                <NavLink
                  key={item.to + item.label}
                  to={item.to}
                  className={cn(
                    'group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-colors',
                    isActive
                      ? 'bg-orange-50 text-[#ff5c00]'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                    collapsed && 'justify-center px-0',
                  )}
                  title={collapsed ? item.label : undefined}
                >
                  <item.icon
                    className={cn(
                      'h-[18px] w-[18px] shrink-0 transition-colors',
                      isActive
                        ? 'text-[#ff5c00]'
                        : 'text-gray-400 group-hover:text-gray-600',
                    )}
                  />
                  {!collapsed && <span>{item.label}</span>}
                </NavLink>
              )
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-100">
        {/* Cmd+K hint */}
        {!collapsed && (
          <div className="flex items-center justify-center gap-1.5 px-3 py-2">
            <kbd className="rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium text-gray-400">
              Ctrl+K
            </kbd>
            <span className="text-[10px] text-gray-400">Quick search</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden lg:flex w-full items-center justify-center py-2.5 text-gray-400 transition-colors hover:text-gray-600"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <div className="flex items-center gap-1.5 text-xs">
              <ChevronLeft className="h-4 w-4" />
              Collapse
            </div>
          )}
        </button>
      </div>
    </>
  )

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden lg:flex flex-col border-r border-gray-200 bg-white transition-all duration-200',
          collapsed ? 'w-[60px]' : 'w-60',
        )}
      >
        {sidebarContent}
      </aside>

      {/* Mobile overlay sidebar */}
      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/40 transition-opacity"
            onClick={closeMobileSidebar}
          />
          {/* Sidebar panel */}
          <aside
            className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-white shadow-xl animate-in slide-in-from-left duration-200"
          >
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  )
}
