import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  Calculator,
  Bell,
  Settings2,
  FlaskConical,
  Sun,
  Moon,
  Menu,
  X,
} from "lucide-react"
import { useState } from "react"
import { useTheme } from "@/hooks/useTheme"
import { cn } from "@/lib/utils"

const NAV = [
  { to: "/",            label: "Home",           icon: LayoutDashboard },
  { to: "/calculator",  label: "Calculator",     icon: Calculator },
  { to: "/alerts",      label: "Alerts",         icon: Bell },
  { to: "/backtest",    label: "Backtesting",    icon: FlaskConical },
  { to: "/config",      label: "Configurations", icon: Settings2 },
]

export function AppSidebar() {
  const { theme, toggle } = useTheme()
  const [open, setOpen] = useState(false)

  return (
    <>
      {/* Mobile hamburger */}
      <button
        className="fixed top-4 left-4 z-50 flex items-center justify-center w-9 h-9 rounded-lg bg-sidebar text-sidebar-foreground border border-sidebar-border lg:hidden"
        onClick={() => setOpen((v) => !v)}
        aria-label="Toggle menu"
      >
        {open ? <X size={18} /> : <Menu size={18} />}
      </button>

      {/* Backdrop on mobile */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-40 h-screen w-60 flex flex-col",
          "bg-sidebar border-r border-sidebar-border",
          "transition-transform duration-200",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Logo */}
        <div className="px-5 py-5 border-b border-sidebar-border">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center justify-center w-8 h-8 rounded-md bg-sidebar-primary">
              <span className="text-sm font-black text-white tracking-tight">ACL</span>
            </div>
            <div>
              <p className="text-sm font-bold text-sidebar-foreground leading-tight">
                ACL Cables
              </p>
              <p className="text-[10px] text-sidebar-foreground/50 leading-tight tracking-wide uppercase">
                Procurement Intel
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-primary text-sidebar-primary-foreground"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer: theme toggle + phase badge */}
        <div className="px-3 py-4 border-t border-sidebar-border space-y-2">
          <button
            onClick={toggle}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </button>
          <div className="px-3">
            <span className="inline-flex items-center gap-1.5 text-[10px] font-bold tracking-widest uppercase text-[var(--c-gold)] opacity-70">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--c-gold)] animate-pulse" />
              Phase 4 · Debug
            </span>
          </div>
        </div>
      </aside>

      {/* Spacer for desktop layout */}
      <div className="hidden lg:block w-60 shrink-0" />
    </>
  )
}
