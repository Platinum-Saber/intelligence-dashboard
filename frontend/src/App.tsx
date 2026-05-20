import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AppSidebar } from "@/components/layout/AppSidebar"
import { HomePage } from "@/pages/HomePage"
import { CalculatorPage } from "@/pages/CalculatorPage"
import { AlertsPage } from "@/pages/AlertsPage"
import { ConfigPage } from "@/pages/ConfigPage"
import { BacktestPage } from "@/pages/BacktestPage"

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

const PAGE_TITLES: Record<string, string> = {
  "/":            "Dashboard Overview",
  "/calculator":  "Landed Cost Calculator",
  "/alerts":      "Alert Event Log",
  "/config":      "Configurations",
  "/backtest":    "Backtesting & UAT",
}

function AppShell() {
  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 px-6 py-4 border-b border-border bg-background/95 backdrop-blur-sm">
          {/* Page title — derived from route */}
          <PageTitle />
          <span className="hidden sm:inline-flex items-center gap-1.5 text-[10px] font-bold tracking-widest uppercase text-[var(--c-gold)] border border-[var(--c-gold)]/30 rounded px-2 py-1 bg-[var(--c-gold)]/5">
            Phase 4 · Debug Mode
          </span>
        </header>

        {/* Main content */}
        <main className="flex-1 px-6 py-6 max-w-[1400px] w-full mx-auto">
          <Routes>
            <Route path="/"           element={<HomePage />} />
            <Route path="/calculator" element={<CalculatorPage />} />
            <Route path="/alerts"     element={<AlertsPage />} />
            <Route path="/config"     element={<ConfigPage />} />
            <Route path="/backtest"   element={<BacktestPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

function PageTitle() {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] ?? "Dashboard"
  return <h1 className="text-base font-semibold">{title}</h1>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
