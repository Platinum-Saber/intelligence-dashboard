import { Overview } from "@/components/Overview/Overview"
import { FXPanel } from "@/components/FXPanel/FXPanel"
import { CommodityPanel } from "@/components/CommodityPanel/CommodityPanel"
import { WeatherMap } from "@/components/WeatherMap/WeatherMap"
import { NewsFeed } from "@/components/NewsFeed/NewsFeed"
import { CostHistory } from "@/components/CostHistory/CostHistory"
import { SentimentBar } from "@/components/SentimentBar/SentimentBar"

export function HomePage() {
  return (
    <div className="flex flex-col gap-6">
      {/* KPI overview */}
      <Overview />

      {/* FX + Commodity charts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <FXPanel />
        <CommodityPanel />
      </div>

      {/* Cost history + Sentiment */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <CostHistory />
        <SentimentBar />
      </div>

      {/* Weather map + News */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <WeatherMap />
        <NewsFeed />
      </div>
    </div>
  )
}
