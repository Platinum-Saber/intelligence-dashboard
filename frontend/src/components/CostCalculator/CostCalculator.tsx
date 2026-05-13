import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { calcLandedCost } from "../../api/calculator";
import type { LandedCostResponse } from "../../types";
import styles from "./CostCalculator.module.css";

const LKR = new Intl.NumberFormat("en-LK", { style: "currency", currency: "LKR", maximumFractionDigits: 0 });
const USD = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export function CostCalculator() {
  const [material, setMaterial] = useState<"COPPER" | "ALUMINIUM">("COPPER");
  const [qty, setQty] = useState("");
  const [customLme, setCustomLme] = useState("");
  const [customFx, setCustomFx] = useState("");

  const calc = useMutation({ mutationFn: calcLandedCost });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const quantity = parseFloat(qty);
    if (!quantity || quantity <= 0) return;
    calc.mutate({
      material,
      quantity_tonnes: quantity,
      custom_lme_price_usd: customLme ? parseFloat(customLme) : null,
      custom_fx_rate: customFx ? parseFloat(customFx) : null,
    });
  }

  const result: LandedCostResponse | undefined = calc.data;

  return (
    <div className={styles.panel}>
      <h2 className={styles.title}>Landed Cost Calculator</h2>
      <p className={styles.hint}>
        Estimates import cost in LKR using current LME price and USD/LKR rate unless overridden.
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.row}>
          <label className={styles.label}>
            Material
            <select value={material} onChange={(e) => setMaterial(e.target.value as "COPPER" | "ALUMINIUM")}>
              <option value="COPPER">Copper</option>
              <option value="ALUMINIUM">Aluminium</option>
            </select>
          </label>

          <label className={styles.label}>
            Quantity (tonnes)
            <input
              type="number"
              min="0.1"
              step="0.1"
              placeholder="e.g. 50"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              required
            />
          </label>
        </div>

        <details className={styles.overrides}>
          <summary>Override prices (optional)</summary>
          <div className={styles.row} style={{ marginTop: 10 }}>
            <label className={styles.label}>
              Custom LME price (USD/t)
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="leave blank for current"
                value={customLme}
                onChange={(e) => setCustomLme(e.target.value)}
              />
            </label>
            <label className={styles.label}>
              Custom USD/LKR rate
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="leave blank for current"
                value={customFx}
                onChange={(e) => setCustomFx(e.target.value)}
              />
            </label>
          </div>
        </details>

        <button className={styles.btn} type="submit" disabled={calc.isPending}>
          {calc.isPending ? "Calculating…" : "Calculate"}
        </button>
      </form>

      {result && (
        <div className={styles.result}>
          <div className={styles.resultRow}>
            <span>Material</span>
            <strong>{result.material}</strong>
          </div>
          <div className={styles.resultRow}>
            <span>Quantity</span>
            <strong>{result.quantity_tonnes.toLocaleString()} t</strong>
          </div>
          <div className={styles.resultRow}>
            <span>LME Price Used</span>
            <strong>{USD.format(result.lme_price_usd_per_tonne)} / t</strong>
          </div>
          <div className={styles.resultRow}>
            <span>USD/LKR Rate Used</span>
            <strong>{result.usd_lkr_rate.toFixed(2)}</strong>
          </div>
          <div className={styles.resultRow}>
            <span>Total (USD)</span>
            <strong>{USD.format(result.total_usd)}</strong>
          </div>
          <div className={`${styles.resultRow} ${styles.highlight}`}>
            <span>Total Landed (LKR)</span>
            <strong>{LKR.format(result.total_lkr)}</strong>
          </div>
        </div>
      )}

      {calc.isError && (
        <p className={styles.error}>Calculation failed — check backend connection.</p>
      )}
    </div>
  );
}
