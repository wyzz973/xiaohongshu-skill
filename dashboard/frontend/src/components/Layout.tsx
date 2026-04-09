import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Monitor,
  FileText,
  MessageCircle,
  BarChart3,
  Settings,
  User,
} from 'lucide-react'

interface NavItem {
  to: string
  icon: React.ComponentType<{ size?: number }>
  label: string
}

const navItems: NavItem[] = [
  { to: '/', icon: LayoutDashboard, label: '总览' },
  { to: '/monitor', icon: Monitor, label: '监控' },
  { to: '/content', icon: FileText, label: '内容' },
  { to: '/interact', icon: MessageCircle, label: '互动' },
  { to: '/analytics', icon: BarChart3, label: '数据' },
  { to: '/settings', icon: Settings, label: '设置' },
]

export default function Layout() {
  const [hoveredNav, setHoveredNav] = useState<string | null>(null)

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-16 flex-shrink-0 bg-white border-r border-[#f0f0f0] flex flex-col items-center py-4">
        {/* Logo */}
        <div className="w-9 h-9 bg-[#FF2442] rounded-lg flex items-center justify-center mb-6">
          <span className="text-white text-xs font-bold tracking-tight">XHS</span>
        </div>

        {/* Nav icons */}
        <nav className="flex-1 flex flex-col items-center gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `relative w-10 h-10 flex items-center justify-center rounded-lg cursor-pointer transition-colors duration-200 ${
                  isActive
                    ? 'bg-red-50 text-[#FF2442]'
                    : 'text-gray-400 hover:bg-gray-50 hover:text-gray-600'
                }`
              }
              onMouseEnter={() => setHoveredNav(item.to)}
              onMouseLeave={() => setHoveredNav(null)}
            >
              <item.icon size={20} />
              {/* Tooltip */}
              {hoveredNav === item.to && (
                <div className="absolute left-full ml-2 px-2 py-1 bg-gray-800 text-white text-xs rounded-md whitespace-nowrap z-50 pointer-events-none">
                  {item.label}
                </div>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Bottom icons */}
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center text-gray-400">
            <User size={16} />
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 bg-[#fafafa] overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
