import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Overview } from "./components/Overview/Overview";
import { FXPanel } from "./components/FXPanel/FXPanel";
import { CommodityPanel } from "./components/CommodityPanel/CommodityPanel";
import { WeatherPanel } from "./components/WeatherPanel/WeatherPanel";
import { NewsFeed } from "./components/NewsFeed/NewsFeed";
import { CostCalculator } from "./components/CostCalculator/CostCalculator";
import styles from "./App.module.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

function Dashboard() {
  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoAccent}>ACL</span> Procurement Intelligence
        </div>
        <span className={styles.badge}>DEBUG MODE</span>
      </header>

      <main className={styles.main}>
        <section className={styles.section}>
          <Overview />
        </section>

        <section className={styles.section}>
          <div className={styles.twoCol}>
            <FXPanel />
            <CommodityPanel />
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.twoCol}>
            <WeatherPanel />
            <CostCalculator />
          </div>
        </section>

        <section className={styles.section}>
          <NewsFeed />
        </section>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  );
}
