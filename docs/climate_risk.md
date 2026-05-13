# ACL Cables PLC — Risk & Climate Evidence Extraction
## Source: Annual Report 2024/25

> **Purpose:** This document consolidates every risk and climate/weather-related finding from the ACL Cables PLC Annual Report 2024/25 that is relevant to the Procurement Intelligence Dashboard project. It is structured for use as a project evidence base — for proposals, justification documents, and development reference.
>
> All quoted or paraphrased content is sourced directly from the AR unless otherwise noted.

---

## Part A: Risks Directly Relevant to the Proposed System

These are the formally documented risks from ACL's own Risk Management section (pages 64–71) that the dashboard is designed to address or support.

---

### Risk 6 — Exchange Rate Risk
**Formal Rating:** Moderate
**Position on Risk Heat Map:** Moderate likelihood, Minor–Moderate impact

> *"Volatility in USD/LKR exchange rates affecting the cost of imported raw materials like Copper, Aluminium and XLPE."*

**Current Mitigation Actions (as stated in AR — all manual):**
- Continuously monitor macroeconomic trends and changes in government policies to assess potential business impacts
- Maintain an adequate foreign currency reserve buffer to ensure the timely execution of critical international payments
- Stay informed on global political events that could impact trade regulations, currency stability, or supply chains

**Evidence of Financial Impact:**
- USD/LKR averaged **297** in FY2024/25 vs. **317** in FY2023/24 — a ~6.3% appreciation of LKR
- The AR explicitly attributes improved margin management to exchange rate predictability: *"Exchange rate predictability minimized volatility in raw material procurement costs, aiding margin management"*
- Gross profit margin improved from **24.47% → 27.27%** year-on-year; FX stability was a stated contributor
- Group revenue: Rs. 37,487 Mn — meaning even a 1% FX swing represents ~Rs. 375 Mn in potential landed cost variation on import-linked raw materials

**Gap the Dashboard Addresses:**
All three current mitigation actions are manual, reactive, and person-dependent. The dashboard automates monitoring, centralizes data, and adds a structured alerting layer.

---

### Risk 9 — Sustainability and Climate-Related Risk
**Formal Rating:** Moderate
**Position on Risk Heat Map:** Low–Moderate likelihood, Moderate impact

> *"Climate-related physical and transition risks significantly impact companies' prospects. From an overall perspective on Sustainability-Related Risks (SRR) and Climate-Related Risks (CRR), the increasing global requirements, regulations, and policies aimed at sustainability are reshaping economies and markets."*

**Current Mitigation Actions (as stated in AR):**
- Continuous evaluations of sustainability and climate-related risks and opportunities
- Implement awareness programs focused on sustainability in financial reporting
- Integrate ESG factors into strategic and operational decision-making processes
- Utilize solar panels and promote sustainable product development
- Monitoring and complying with evolving environmental regulations

**Gap the Dashboard Addresses:**
The mitigation actions are strategic/compliance-oriented. The dashboard addresses the operational side — specifically weather event monitoring and logistics disruption early warning — which is not covered by any listed mitigation.

---

### Risk 2 — Country Risk
**Formal Rating:** Significant
**Position on Risk Heat Map:** Moderate likelihood, Moderate–Major impact

> *"Negative impact arising due to adverse economic factors such as Political, Economic, Social, Technological, Environmental, and Legal."*

**Current Mitigation Actions:**
- Perform comprehensive and ongoing PESTEL factor evaluation
- Monitor and analyse potential impacts of legislative and regulatory changes
- Establish strong relationships with local government bodies, regulators, and industry associations

**Relevance to Dashboard:**
The NLP news sentiment module directly supports country risk monitoring by automatically tracking geopolitical and macroeconomic developments across ACL's supplier countries (UAE, China, Singapore, Vietnam) and Sri Lanka, surfacing them for the procurement team without manual news scanning.

---

### Risk 4 — Operational Risk
**Formal Rating:** Moderate

> *"Operational risk is focusing on the risks arising from the people, systems and processes through which the Company operates."*

**Relevant Mitigation Actions:**
- Continuously monitoring compliance with regulatory and internal requirements via compliance dashboards
- Maintaining a Business Continuity Plan (BCP) to ensure smooth business operations

**Relevance to Dashboard:**
Supply chain disruptions from weather events, or commodity price spikes that stress working capital, are operational risks. The weather logistics panel and commodity alert components directly support BCP preparedness.

---

### Risk 10 — Liquidity Risk
**Formal Rating:** Low

> *"Adverse impact on the liquidity position as a result of payment delays by debtors, long stock residence period, early payment to creditors, and other factors which may create a negative impact on the working capital cycle."*

**Relevance to Dashboard:**
The cost-impact calculator (Component 5 in the system design) helps the procurement team model the cash flow implications of purchasing decisions at different FX rates — directly supporting working capital management. Buying at an unfavourable FX rate ties up more LKR in inventory, worsening the working capital cycle.

---

## Part B: Risk Evidence from Strategic Analysis Sections

These are risk signals embedded in the AR's SWOT, PEST, MDA, and stakeholder sections — not the formal risk register — but directly relevant to the project.

---

### B1 — SWOT Analysis: Weaknesses

| Weakness | Relevance to Dashboard |
|---------|----------------------|
| *"Dependency on the construction industry"* — revenue heavily reliant on one sector | Demand forecasting signals (PMI, construction activity) could be added as a future data feed |
| *"Dependency on the local market"* — exposes company to local economic conditions | FX and macro monitoring becomes more critical, not less, when domestic demand is concentrated |

### B2 — SWOT Analysis: Threats

| Threat | Relevance to Dashboard |
|--------|----------------------|
| *"Global Trade Practices: With the tariff structures imposed by US on different countries will create an uneven level playing ground"* | Directly supports the geopolitical NLP news monitoring component — US tariff changes affect ACL's supplier countries (China, Vietnam especially) and can disrupt raw material pricing and availability |

### B3 — SWOT Analysis: Opportunities

| Opportunity | Relevance to Dashboard |
|------------|----------------------|
| *"Removal of forex and import restrictions can facilitate easier access to raw materials and components, potentially reducing production costs and improving competitiveness"* | The dashboard tracks the macro conditions (CBSL policies, IMF program milestones) that signal when such regulatory windows open |
| *"Diversification of supplier bases by foreign clients: Global trend on diversification of supply chain would benefit ACL"* | Supplier country weather and geopolitical monitoring becomes more valuable as supplier geography diversifies |

### B4 — PEST Analysis: Economic Factors

> *"Stability in exchange rates is essential for the industry's reliance on imported raw materials... Stability in interest rates and inflation, crucial for private sector credit growth, is supported by the government's commitment to the IMF-EFF program, aimed at achieving macroeconomic stability."*

**Direct evidence** that exchange rate stability is a structural dependency of ACL's business model, not a one-off concern.

> *"The industry's heavy reliance on imported raw materials makes it susceptible to fluctuations in import tariffs and controls."*

This validates the news/geopolitical monitoring component — tariff and trade policy changes need to be tracked in near real-time.

### B5 — Supply Chain Section

> *"Majority of raw materials are imported from several nations, including UAE, China, Singapore & Vietnam and the Group made sure that inputs were always available by prudently forecasting demand and production patterns."*

> *"By proactively managing working capital cycles and obtaining favorable credit terms from international suppliers, the supply chain was able to carefully navigate disruptions brought on by import restrictions and a depreciating currency."*

**Key insight:** "Prudently forecasting" and "proactively managing" are the stated methods — both currently done manually. The dashboard replaces manual monitoring with automated, data-driven equivalents.

**Supplier country breakdown:**
- UAE
- China
- Singapore
- Vietnam

These four countries are the geographic scope for the supplier-side weather and geopolitical monitoring modules.

### B6 — Management Discussion & Analysis: FX Narrative

> *"The USD/LKR exchange rate averaged 297 in 2024/25, compared to 317 in the previous year, reflecting enhanced market confidence and tighter forex liquidity management."*

> *"For ACL Cables PLC, the stable rupee and lower interest rates had a direct positive impact: Reduced Financing Costs... Import Cost Stability: Exchange rate predictability minimized volatility in raw material procurement costs, aiding margin management."*

**Numerical anchor for cost-impact calculator:**
- Average FX rate FY2024/25: **USD/LKR 297**
- Average FX rate FY2023/24: **USD/LKR 317**
- This ~20-point swing on import-heavy procurement directly affected gross margin (24.47% → 27.27%)

The cost-impact calculator should use this same logic: quantity ordered × commodity price × FX rate → landed LKR cost.

### B7 — Chairman's / MD's Commentary on FX

> *"The stabilization of the exchange rate further enhanced business predictability, fostering a conducive environment for industrial growth and investment."* — MD's Report

> *"Foreign exchange reserves continued to strengthen, bolstered by a resurgence in tourism, increased remittances, and growing export revenues."* — Chairman's Report

Both statements confirm FX as a top-of-mind executive concern. A dashboard that monitors the drivers of FX stability (reserves, remittances, tourism, IMF disbursements) would directly serve this.

---

## Part C: Climate and Weather Risk — Full Extraction

This section consolidates all climate and weather-related content in the AR, organized by type.

---

### C1 — Formal Climate Risk Table (from Natural Capital / SLFRS S1-S2 Section, p.32–33)

ACL formally categorizes climate risks into **Physical Risks** and **Transition Risks**:

#### Physical Risks

**Acute Physical Risks** (extreme weather events):

| Risk | AR Description | Operational Impact Stated |
|------|---------------|--------------------------|
| Heatwaves | Formally listed as acute event | Production setbacks, decreased sales from damaged facilities |
| Wildfires | Formally listed | Same as above |
| Storms, hurricanes, cyclones | Formally listed | *"Disrupts the supply chain, drives up raw material costs, and impedes distribution"* |
| **Floods** | Formally listed — highlighted as especially relevant given island-wide distribution | *"Disruptions to logistics network, delay deliveries, impact warehouse operations, and limit employee access to facilities... lead to operational slowdowns and financial implications"* |

> *"As a company with island-wide distribution we are exposed to physical risks from extreme weather events. Severe flooding, like recent events in the region, could disrupt our logistics network, delay deliveries, impact warehouse operations, and limit employee access to facilities."*

**Chronic Physical Risks** (long-term climate shifts):

| Risk | AR Description | Operational Impact Stated |
|------|---------------|--------------------------|
| Rising sea levels | Formally listed | Long-term strategic risk to facilities and financial viability |
| **Water scarcity and drought** | Formally listed — specifically linked to manufacturing process | *"Water is crucial in cable manufacturing for cooling, cleaning, and lubricating machinery. Water shortages can disrupt production efficiency, potentially leading to overheating and equipment malfunctions"* |
| Ocean acidification | Formally listed | General strategic risk |
| Desertification | Formally listed | General strategic risk |

#### Transition Risks

| Risk | Category | AR Description |
|------|----------|---------------|
| Policy actions for low-carbon transition | Policy & Legal | Compliance with environmental regulations; cost implications of chemical use |
| Failure to comply with new/stricter climate laws | Reputation Risk | *"Non-compliance with climate regulations or stakeholder expectations could impact product demand and harm the business"* |
| Discontinuation of products ahead of lifecycle | Market Risk | Solvent-based product retirement risk; already being addressed with energy-saving cables |
| Competitive pressures on sustainability strategies | Market Risk | Need to quickly invest in and implement sustainability strategies |

---

### C2 — Climate-Related Opportunities (from AR p.34)

| Opportunity | Category | Description |
|------------|----------|-------------|
| Strategic investments in renewable energy | Investment | Shift toward wind and solar opens investment opportunities; supported by Sri Lanka Sustainable Energy Authority |
| Energy-efficient product lines | Innovation | *"Cables that minimize energy loss are in demand. Low-loss cables... can contribute significantly to reducing overall energy consumption"* |
| Green manufacturing practices | Investment | Sustainable production, renewable energy in manufacturing, waste reduction |

**Project relevance:** ACL's investment in **Resus Energy PLC** (renewable energy subsidiary) means ACL is exposed to weather/climate data on two fronts — as a cable manufacturer (supply chain/logistics risk) AND as an energy generator (solar/wind output variability). This strengthens the case for a weather monitoring module.

---

### C3 — Environmental Operations Data (from Natural Capital section, p.34–35)

Actual operational data that contextualizes climate vulnerability:

**Energy consumption:**
| Source | Units |
|--------|-------|
| Non-renewable electricity | 3,549,809 kWh |
| Renewable (solar) | 2,644,638 kWh |
| Diesel | 280,149 L |
| Petrol | 93,431 L |

**Emissions:**
| Type | Amount |
|------|--------|
| Direct (Scope 1) GHG | 784 tCO₂e |
| Indirect (Scope 2) GHG | 2,343 tCO₂e |
| Total carbon footprint | 3,127 tCO₂e |

**Water management:**
- Rainwater harvesting system on factory premises
- Cooling towers with recycled cooling water system
- Water quality monitoring to CEA standards

**Project relevance:** Water scarcity risk is concrete — the manufacturing process requires water for cooling, cleaning, and lubricating. A drought alert (integrated from Open-Meteo or DMC Sri Lanka data) could provide early warning of water stress risk to production continuity.

---

### C4 — SLFRS S1 and S2 Alignment (p.32)

> *"As the landscape of non-financial reporting evolves, ACL Cables PLC is closely monitoring the developments. We recognize the significant benefits of aligning our non-financial reporting with SLFRS S1 – General Requirements for Disclosure of Sustainability-related Financial Information, and SLFRS S2 – Climate-related Disclosures."*

> *"We have identified a range of Sustainability-Related Risks and Opportunities (SRRSOs) and Climate-Related Risks and Opportunities (CRROs) that could impact the Group's financial viability, and are actively working to address these challenges."*

**Project relevance:** ACL is actively building climate risk reporting infrastructure to comply with SLFRS S1/S2. The dashboard's climate monitoring data (weather events, logistics disruption logs) could serve as an operational data source for these disclosures — adding a compliance use case on top of the procurement use case.

---

### C5 — Sustainability Risk in Formal Risk Register (Risk #9, p.70)

> *"Climate-related physical and transition risks significantly impact companies' prospects... companies face ongoing risks and challenges that must be addressed strategically."*

**Formal mitigation actions listed (all strategic-level, no operational tooling):**
- Continuous evaluations of sustainability and climate-related risks
- Implement ESG awareness programs
- Integrate ESG into strategic and operational decision-making
- Utilize solar panels
- Monitor and comply with evolving environmental regulations
- Transparent stakeholder communication
- Periodic assessments to identify emerging sustainability risks

**Gap:** None of the listed mitigations address real-time weather event monitoring or operational disruption early warning. The dashboard fills this gap.

---

## Part D: Quantified Financial Context

These numbers should be used to frame the project's business case and in the cost-impact calculator design.

| Metric | FY2024/25 | FY2023/24 | Change |
|--------|-----------|-----------|--------|
| Group Revenue | Rs. 37,487 Mn | Rs. 29,196 Mn | +28.4% |
| Gross Profit | Rs. 10,224 Mn | Rs. 7,143 Mn | +43.1% |
| Gross Profit Margin | 27.27% | 24.47% | +2.8pp |
| Profit After Tax | Rs. 5,420 Mn | Rs. 3,446 Mn | +57.3% |
| Company Revenue | Rs. 17,330 Mn | Rs. 13,889 Mn | +24.8% |
| Average USD/LKR Rate | 297 | 317 | -6.3% (LKR appreciated) |
| Import vendor share of purchases | 57% | — | — |
| Export revenue growth | +10.31% | — | — |
| Total Assets | Rs. 43,654 Mn | — | +14.07% |
| Total Equity | Rs. 36,020 Mn | Rs. 31,007 Mn | — |

**Key derived figure for business case:**
- Import-linked procurement ≈ 57% of purchases on a Rs. 37.5 Bn revenue base
- A 1% FX improvement on import costs = ~Rs. **213 Mn** in potential cost savings
- The FX swing from 317 → 297 (FY23/24 to FY24/25) contributed to a 2.8pp gross margin improvement
- This is the magnitude the dashboard aims to help the team capture more consistently

---

## Part E: Summary — Evidence Map to System Components

| System Component | AR Evidence Supporting It |
|-----------------|--------------------------|
| **FX Rate Monitoring** | Risk #6 (Exchange Rate Risk); MDA FX narrative; PEST Economic factors; GP margin improvement attribution |
| **Commodity Price Monitoring (Copper, Aluminium)** | Risk #6 explicitly names Copper, Aluminium, XLPE; backward integration into Ceylon Copper and ACL Metals & Alloys |
| **Geopolitical News / NLP Sentiment** | Risk #2 (Country Risk); SWOT Threat (US tariff structures); PEST Political factors; supplier country exposure (UAE, China, Singapore, Vietnam) |
| **Weather Monitoring — Sri Lanka Logistics** | Climate Risk Table (Floods, Storms, Heatwaves); Natural Capital section flooding narrative; island-wide distribution network (996 dealers, 219 distributors) |
| **Weather Monitoring — Production/Water** | Chronic risk (Water scarcity and drought); manufacturing water dependency confirmed in Natural Capital section |
| **Weather Monitoring — Supplier Countries** | Physical risk from storms/floods applies to supplier country port operations (UAE, China, Vietnam, Singapore) |
| **Alert & Notification Engine** | All manual mitigations in Risk #6, Risk #2, Risk #9 are candidates for automation via alerts |
| **Cost-Impact Calculator** | FX rate averages (297 vs 317), import vendor share (57%), GP margin data provide calibration inputs |
| **SLFRS S1/S2 Compliance Support** | Climate reporting obligations (p.32); need for operational climate data to support disclosures |

---

*Extracted: 2026-05-13 | Source: ACL Cables PLC Annual Report 2024/25*
*To be cross-referenced with: `ACL_ProcurementIntel_Project.md`*