import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { calcLandedCost } from "@/api/calculator"
import type { LandedCostResponse } from "@/types"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { CostHistory } from "@/components/CostHistory/CostHistory"

const LKR = new Intl.NumberFormat("en-LK", { style: "currency", currency: "LKR", maximumFractionDigits: 0 })
const USD = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })

export function CalculatorPage() {
  const [material, setMaterial] = useState<"COPPER" | "ALUMINIUM">("COPPER")
  const [qty, setQty] = useState("")
  const [customLme, setCustomLme] = useState("")
  const [customFx, setCustomFx] = useState("")
  const [showOverrides, setShowOverrides] = useState(false)

  const calc = useMutation({ mutationFn: calcLandedCost })
  const result: LandedCostResponse | undefined = calc.data

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const quantity = parseFloat(qty)
    if (!quantity || quantity <= 0) return
    calc.mutate({
      material,
      quantity_tonnes: quantity,
      custom_lme_price_usd: customLme ? parseFloat(customLme) : null,
      custom_fx_rate: customFx ? parseFloat(customFx) : null,
    })
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* Calculator form */}
        <Card>
          <CardHeader>
            <CardTitle>Landed Cost Calculator</CardTitle>
            <CardDescription>
              Estimates import cost in LKR using current LME price and USD/LKR rate. Override for scenario analysis.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Material</Label>
                  <Select value={material} onValueChange={(v) => setMaterial(v as "COPPER" | "ALUMINIUM")}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="COPPER">Copper</SelectItem>
                      <SelectItem value="ALUMINIUM">Aluminium</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Quantity (tonnes)</Label>
                  <Input
                    type="number"
                    min="0.1"
                    step="0.1"
                    placeholder="e.g. 50"
                    value={qty}
                    onChange={(e) => setQty(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div>
                <button
                  type="button"
                  className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
                  onClick={() => setShowOverrides((v) => !v)}
                >
                  <span>{showOverrides ? "▾" : "▸"}</span>
                  Override prices (optional)
                </button>
                {showOverrides && (
                  <div className="grid grid-cols-2 gap-4 mt-3 p-3 rounded-lg border border-dashed border-border">
                    <div className="space-y-2">
                      <Label>Custom LME price (USD/t)</Label>
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="current"
                        value={customLme}
                        onChange={(e) => setCustomLme(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Custom USD/LKR rate</Label>
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="current"
                        value={customFx}
                        onChange={(e) => setCustomFx(e.target.value)}
                      />
                    </div>
                  </div>
                )}
              </div>

              <Button type="submit" className="w-full" disabled={calc.isPending}>
                {calc.isPending ? "Calculating…" : "Calculate Landed Cost"}
              </Button>
            </form>

            {/* Result */}
            {result && (
              <div className="mt-5 rounded-lg border border-border overflow-hidden">
                <div className="bg-muted px-4 py-2 flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Result</span>
                  <Badge variant="secondary">{result.material}</Badge>
                </div>
                <div className="divide-y divide-border">
                  {[
                    ["Quantity", `${result.quantity_tonnes.toLocaleString()} t`],
                    ["LME Price Used", `${USD.format(result.lme_price_usd_per_tonne)} / t`],
                    ["USD/LKR Rate", result.usd_lkr_rate.toFixed(2)],
                    ["Total (USD)", USD.format(result.total_usd)],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between items-center px-4 py-2.5 text-sm">
                      <span className="text-muted-foreground">{label}</span>
                      <span className="font-medium">{value}</span>
                    </div>
                  ))}
                  <div className="flex justify-between items-center px-4 py-3 bg-primary/5">
                    <span className="text-sm font-semibold text-primary">Total Landed (LKR)</span>
                    <span className="text-lg font-bold text-primary">{LKR.format(result.total_lkr)}</span>
                  </div>
                </div>
              </div>
            )}

            {calc.isError && (
              <p className="mt-3 text-sm text-destructive">Calculation failed — check backend connection.</p>
            )}
          </CardContent>
        </Card>

        {/* Quick reference */}
        <Card>
          <CardHeader>
            <CardTitle>How it works</CardTitle>
            <CardDescription>Calculation methodology</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="space-y-2">
              <p className="font-medium text-foreground">Formula</p>
              <div className="rounded-md bg-muted p-3 font-mono text-xs">
                Landed Cost (LKR) = LME Price (USD/t) × Quantity (t) × USD/LKR
              </div>
            </div>
            <div className="space-y-1.5">
              <p className="font-medium text-foreground">Data sources</p>
              <ul className="space-y-1 list-disc list-inside">
                <li>LME prices: Yahoo Finance (HG=F, ALI=F)</li>
                <li>USD/LKR rate: exchangerate-api.com</li>
                <li>Prices updated hourly via scheduler</li>
              </ul>
            </div>
            <div className="space-y-1.5">
              <p className="font-medium text-foreground">Override use cases</p>
              <ul className="space-y-1 list-disc list-inside">
                <li>Scenario planning with projected rates</li>
                <li>Forward price analysis</li>
                <li>Sensitivity testing</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Historical cost chart */}
      <CostHistory />
    </div>
  )
}
