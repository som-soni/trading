# Sector taxonomy — sectors, industry groups, sub-industries

**Status: built (7 Oct 2026)** — levels 1–3 are live on the Sectors page
(Sectors / Industry groups / Sub-industries), in each group's detail and in the
chart's details panel. The assignments are in `data/sub_industries.csv`
(editable; 811 rows, 15 groups) plus rules in
`scripts/swing_screener/marketdata/subindustries.py` (US regional banks by size
and country, US asset management split into managers / BDCs / crypto-treasury
companies). US closed-end funds (341) are excluded from breadth, sectors and
movers (`classify` job). Not yet split: US Biotechnology (needs revenue to
separate commercial- from clinical-stage), Software—Application, Medical Devices
— see `TODO.md`. Themes are deferred (`TODO.md`).

## 1. Recommendation

Yes — leaders are found at the **industry-group** level and, for a handful of
large, mixed groups, one level below. Minervini (following O'Neil/IBD, who rank
~197 industry groups) looks for the strongest stocks *in the strongest groups*;
a broad sector like "Technology" or "Industrials" is too coarse to show where
leadership actually is.

But finer is not automatically better. A group needs enough liquid members for
its RS rating and breadth to mean anything — below ~4–5 stocks, one name's move
*is* the group. So the proposal is **three levels, with the third used
selectively**:

| Level | What | Count | Use |
|---|---|---|---|
| 1. Sector | Yahoo's 11 sectors | 11 | context: "is it Technology or Energy that's leading?" |
| 2. Industry group | Yahoo's industries (GICS-like) | 145 (≈138 US / ≈84 India have 3+ liquid stocks) | **the main unit**: RS rating, rotation, leaders — today's Sectors page |
| 3. Sub-industry | curated splits of ~16 large, mixed groups | ~60 | where an industry group mixes businesses with different drivers (e.g. cables vs transformers; PSU vs private banks) |
| Themes (cross-cutting) | named baskets across groups | as needed | AI infrastructure, data-centre power, railways, defence… — the playbook's Phase 6, kept separate from the taxonomy |

Why not adopt IBD's 197 groups directly: the list is proprietary (names are
public, the membership is not), and it is US-only. Why not NSE's own 4-level
classification for India (~197 "basic industries"): NSE blocks automated
access to it, so it cannot be kept current reliably. Yahoo's classification is
available for both markets and refreshed monthly by the `industries` job; the
curated level 3 fills its gaps.

## 2. Data hygiene to fix first (affects every page)

1. **US closed-end funds counted as companies.** "Asset Management" has 203 US
   members — most are closed-end funds and income trusts (Nuveen, Eaton Vance,
   Pimco, Gabelli…) that the Nasdaq listing does not flag as ETFs. They distort
   that group, breadth and movers. Proposal: exclude funds/trusts from the US
   universe by name and quote type, keep real managers (BLK, BX, KKR, APO…) and
   treat **BDCs** (ARCC, Golub, Hercules…) as their own sub-industry.
2. **Foreign ADRs mixed with domestic companies.** US "Banks—Regional" includes
   HDFC Bank, ICICI, Mizuho, Deutsche Bank, KB… (ADRs); semiconductors include
   TSM and UMC. Proposal: flag ADRs (`foreign` attribute) and either split them
   into an "… — Foreign (ADR)" sub-industry or filter them with a toggle.

## 3. Level 1 → Level 2: every sector and industry group

Counts are **liquid** common stocks in each market today (US ≥ $2M/day,
India ≥ ₹2 Cr/day — the Sectors page universe). "–" means none. Groups with
fewer than 3 are shown only inside their sector on the portal.

### Basic Materials  ·  US 186 · India 236

| Industry group | US | India |
|---|---:|---:|
| Agricultural Inputs | 8 | 27 |
| Aluminum | 4 | 6 |
| Building Materials | 13 | 20 |
| Chemicals | 11 | 26 |
| Coking Coal | 4 | 1 |
| Copper | 7 | 3 |
| Gold | 35 | 1 |
| Lumber & Wood Production | 4 | 3 |
| Other Industrial Metals & Mining | 24 | 10 |
| Other Precious Metals & Mining | 12 | 1 |
| Paper & Paper Products | 2 | 6 |
| Silver | 6 | – |
| Specialty Chemicals | 45 | 74 |
| Steel | 11 | 58 |

### Communication Services  ·  US 126 · India 27

| Industry group | US | India |
|---|---:|---:|
| Advertising Agencies | 13 | 2 |
| Broadcasting | 5 | 3 |
| Electronic Gaming & Multimedia | 3 | 1 |
| Entertainment | 33 | 8 |
| Internet Content & Information | 32 | 2 |
| Publishing | 6 | 1 |
| Telecom Services | 34 | 10 |

### Consumer Cyclical  ·  US 314 · India 237

| Industry group | US | India |
|---|---:|---:|
| Apparel Manufacturing | 15 | 13 |
| Apparel Retail | 21 | 8 |
| Auto & Truck Dealerships | 16 | 2 |
| Auto Manufacturers | 12 | 15 |
| Auto Parts | 36 | 65 |
| Department Stores | 3 | 3 |
| Footwear & Accessories | 12 | 8 |
| Furnishings, Fixtures & Appliances | 16 | 23 |
| Gambling | 6 | – |
| Home Improvement Retail | 4 | 1 |
| Internet Retail | 13 | 7 |
| Leisure | 15 | 1 |
| Lodging | 7 | 10 |
| Luxury Goods | 5 | 24 |
| Packaging & Containers | 18 | 12 |
| Personal Services | 6 | – |
| Recreational Vehicles | 11 | – |
| Residential Construction | 17 | – |
| Resorts & Casinos | 11 | 3 |
| Restaurants | 33 | 8 |
| Specialty Retail | 24 | 2 |
| Textile Manufacturing | 1 | 27 |
| Travel Services | 12 | 5 |

### Consumer Defensive  ·  US 129 · India 93

| Industry group | US | India |
|---|---:|---:|
| Beverages—Brewers | 5 | 2 |
| Beverages—Non-Alcoholic | 11 | 2 |
| Beverages—Wineries & Distilleries | 2 | 9 |
| Confectioners | 3 | 13 |
| Discount Stores | 9 | 1 |
| Education & Training Services | 16 | 7 |
| Farm Products | 10 | 6 |
| Food Distribution | 7 | 1 |
| Grocery Stores | 9 | – |
| Household & Personal Products | 17 | 13 |
| Packaged Foods | 35 | 36 |
| Tobacco | 5 | 3 |

### Energy  ·  US 163 · India 33

| Industry group | US | India |
|---|---:|---:|
| Oil & Gas Drilling | 10 | – |
| Oil & Gas E&P | 46 | 5 |
| Oil & Gas Equipment & Services | 36 | 7 |
| Oil & Gas Integrated | 13 | 2 |
| Oil & Gas Midstream | 39 | – |
| Oil & Gas Refining & Marketing | 10 | 13 |
| Thermal Coal | 3 | 6 |
| Uranium | 6 | – |

### Financial Services  ·  US 641 · India 153

| Industry group | US | India |
|---|---:|---:|
| Asset Management | 203 | 16 |
| Banks—Diversified | 18 | – |
| Banks—Regional | 221 | 38 |
| Capital Markets | 47 | 21 |
| Credit Services | 33 | 43 |
| Financial Conglomerates | 4 | 4 |
| Financial Data & Stock Exchanges | 11 | 5 |
| Insurance Brokers | 15 | 2 |
| Insurance—Diversified | 8 | 2 |
| Insurance—Life | 14 | 9 |
| Insurance—Property & Casualty | 40 | 1 |
| Insurance—Reinsurance | 6 | 1 |
| Insurance—Specialty | 13 | – |
| Mortgage Finance | 6 | 11 |
| Shell Companies | 2 | – |

### Healthcare  ·  US 521 · India 141

| Industry group | US | India |
|---|---:|---:|
| Biotechnology | 251 | 10 |
| Diagnostics & Research | 35 | 9 |
| Drug Manufacturers—General | 13 | 13 |
| Drug Manufacturers—Specialty & Generic | 44 | 76 |
| Health Information Services | 22 | 3 |
| Healthcare Plans | 11 | 1 |
| Medical Care Facilities | 35 | 21 |
| Medical Devices | 70 | 2 |
| Medical Distribution | 5 | 1 |
| Medical Instruments & Supplies | 35 | 4 |
| Pharmaceutical Retailers | – | 1 |

### Industrials  ·  US 455 · India 318

| Industry group | US | India |
|---|---:|---:|
| Aerospace & Defense | 68 | 19 |
| Airlines | 10 | 1 |
| Airports & Air Services | 5 | 2 |
| Building Products & Equipment | 28 | 17 |
| Business Equipment & Supplies | 3 | 2 |
| Conglomerates | 15 | 22 |
| Consulting Services | 8 | 1 |
| Electrical Equipment & Parts | 27 | 44 |
| Engineering & Construction | 37 | 61 |
| Farm & Heavy Construction Machinery | 19 | 10 |
| Industrial Distribution | 19 | 1 |
| Infrastructure Operations | – | 4 |
| Integrated Freight & Logistics | 16 | 14 |
| Marine Shipping | 19 | 9 |
| Metal Fabrication | 11 | 24 |
| Pollution & Treatment Controls | 7 | 1 |
| Railroads | 9 | 5 |
| Rental & Leasing Services | 16 | 2 |
| Security & Protection Services | 10 | 1 |
| Specialty Business Services | 28 | 9 |
| Specialty Industrial Machinery | 60 | 57 |
| Staffing & Employment Services | 10 | 2 |
| Tools & Accessories | 8 | 8 |
| Trucking | 12 | 1 |
| Waste Management | 10 | 1 |

### Real Estate  ·  US 167 · India 42

| Industry group | US | India |
|---|---:|---:|
| REIT—Diversified | 12 | – |
| REIT—Healthcare Facilities | 16 | – |
| REIT—Hotel & Motel | 12 | – |
| REIT—Industrial | 15 | – |
| REIT—Mortgage | 24 | – |
| REIT—Office | 14 | – |
| REIT—Residential | 15 | – |
| REIT—Retail | 25 | – |
| REIT—Specialty | 17 | – |
| Real Estate Services | 13 | 6 |
| Real Estate—Development | 3 | 31 |
| Real Estate—Diversified | 1 | 5 |

### Technology  ·  US 472 · India 121

| Industry group | US | India |
|---|---:|---:|
| Communication Equipment | 30 | 12 |
| Computer Hardware | 23 | 4 |
| Consumer Electronics | 4 | 3 |
| Electronic Components | 30 | 7 |
| Electronics & Computer Distribution | 7 | 4 |
| Information Technology Services | 45 | 36 |
| Scientific & Technical Instruments | 17 | 1 |
| Semiconductor Equipment & Materials | 26 | 1 |
| Semiconductors | 51 | 1 |
| Software—Application | 123 | 26 |
| Software—Infrastructure | 108 | 11 |
| Solar | 8 | 15 |

### Utilities  ·  US 79 · India 32

| Industry group | US | India |
|---|---:|---:|
| Utilities—Diversified | 5 | – |
| Utilities—Independent Power Producers | 8 | 9 |
| Utilities—Regulated Electric | 35 | 6 |
| Utilities—Regulated Gas | 14 | 5 |
| Utilities—Regulated Water | 8 | 1 |
| Utilities—Renewable | 9 | 11 |

## 4. Level 3: proposed sub-industries

Only groups that are both **large** and **mixed** are split. Example members are
the largest liquid stocks in each (today's data); the final mapping would be
reviewed name by name.

### United States

| Industry group (members) | Proposed sub-industries — examples |
|---|---|
| Semiconductors (51) | **AI & compute** — NVDA, AMD, AVGO, MRVL, ARM, ALAB, CRDO · **Memory & storage** — MU · **Analog, power & MCU** — TXN, ADI, MCHP, NXPI, ON, MPWR, STM · **RF & mobile** — QCOM, SWKS, QRVO · **Foundry** — TSM, UMC, GFS, TSEM, INTC |
| Software—Infrastructure (108) | **Cybersecurity** — PANW, CRWD, FTNT, ZS, OKTA, RBRK · **Cloud & data platforms** — ORCL, MDB, NET, CRWV, NTNX · **Platforms** — MSFT, PLTR · **Design software (EDA)** — SNPS · **Payments infrastructure** — XYZ, CPAY |
| Software—Application (123) | **Enterprise apps** · **Vertical SaaS** (health, real estate, finance) · **Fintech** · **Consumer & media apps** · **Ad-tech** |
| Aerospace & Defense (68) | **Defense primes** — LMT, NOC, GD, LHX, HII, RTX · **Commercial aerospace** — BA, GE, HWM, TDG, HEI, WWD, FTAI · **Space & drones** — RKLB and peers · **Public safety & security** — AXON |
| Electrical Equipment & Parts (27) | **Data-centre power & cooling** — VRT, NVT, POWL, HUBB · **Fuel cells & hydrogen** — BE, FCEL · **Batteries & storage** — EOSE, AMPX, ENS |
| Banks—Regional (221) | **Large regionals** (> $20B) — USB, PNC, TFC, FITB, MTB, HBAN · **Mid-size** · **Community** (< $2B) · **Foreign banks (ADR)** — HDB, IBN, MFG, DB, KB, BAP |
| Asset Management (203) | **Asset managers & alternatives** — BLK, BX, KKR, APO, ARES, OWL, TROW · **BDCs** — ARCC, GBDC, HTGC, FSK · *(closed-end funds removed — §2)* |
| Biotechnology (251) | **Commercial-stage** (meaningful product revenue) — VRTX, REGN, ALNY, INCY, BMRN · **Clinical-stage** — the rest (split by revenue, refreshed with fundamentals) |
| Capital Markets (47) | **Exchanges & data** · **Brokers & investment banks** · **Crypto-linked** |
| Medical Devices (70) | **Surgical & robotics** · **Cardio & vascular** · **Diabetes & monitoring** · **Other devices** |

### India

| Industry group (members) | Proposed sub-industries — examples |
|---|---|
| Banks—Regional (38) | **Private banks** — HDFCBANK, ICICIBANK, KOTAKBANK, AXISBANK, INDUSINDBK, FEDERALBNK, IDFCFIRSTB · **PSU banks** — SBIN, PNB, BANKBARODA, CANBK, UNIONBANK, INDIANB, BANKINDIA, MAHABANK, IOB, UCOBANK · **Small finance banks** — AUBANK and peers |
| Credit Services (43) | **Diversified NBFC** — BAJFINANCE, TATACAP, POONAWALLA, PIRAMALFIN · **Vehicle finance** — SHRIRAMFIN, CHOLAFIN, M&MFIN, SUNDARMFIN · **Gold loans** — MUTHOOTFIN, MANAPPURAM · **Govt. infra & power lenders** — PFC, RECLTD, IRFC, HUDCO, IREDA · **Cards** — SBICARD · **Microfinance** — CREDITACC |
| Drug Manufacturers—Specialty & Generic (76) | **US generics exporters** — SUNPHARMA, DRREDDY, LUPIN, AUROPHARMA, ZYDUSLIFE, CIPLA, GLENMARK · **Domestic formulations** — MANKIND, TORNTPHARM, ALKEM, ABBOTINDIA, AJANTPHARM, IPCALAB · **CDMO & API** — DIVISLAB, LAURUSLABS, NEULANDLAB, GRANULES, PPLPHARMA, GLAND |
| Specialty Chemicals (74) | **Paints & coatings** — ASIANPAINT, BERGEPAINT, KANSAINER, JSWDULUX · **Adhesives & construction chemicals** — PIDILITIND · **Fluorochemicals** — FLUOROCHEM · **Pharma & agro intermediates (custom synthesis)** — AARTIIND, VINATIORGA, ANURAS, AETHER, ACUTAAS · **Explosives & defence chemicals** — SOLARINDS · **Carbon black & others** — PCBL |
| Electrical Equipment & Parts (44) | **Transmission & distribution / transformers** — POWERINDIA, CGPOWER, SCHNEIDER, TARIL, VOLTAMP · **Cables & wires** — POLYCAB, KEI, RRKABEL, FINCABLES, APARINDS · **Consumer electricals** — HAVELLS, VGUARD · **Graphite electrodes** — GRAPHITE, HEGAM · **Batteries & energy storage** — HBLENGINE, ARE&M |
| Engineering & Construction (61) | **Diversified E&C** — LT · **Railway infra (PSU)** — RVNL, IRCON, RITES · **Power T&D EPC** — KEC, KPIL, SKIPPER · **Roads & highways** — GRINFRA, CEIGALL, DBL, NCC · **Water** — WABAG · **Urban & buildings** — NBCC, AFCONS |
| Auto Parts (65) | **Tyres** — MRF, BALKRISIND, APOLLOTYRE · **Batteries** — EXIDEIND · **EV & electronics** — SONACOMS, UNOMINDA · **Forgings & castings** — CRAFTSMAN, SANSERA · **Diversified components** — MOTHERSON, BOSCHLTD, SCHAEFFLER, ENDURANCE |
| Steel (58) | **Integrated steel** · **Pipes & tubes** · **Stainless & alloys** · **Sponge iron & small producers** |
| Specialty Industrial Machinery (57) | **Heavy capital goods & power equipment** · **Railway equipment** · **Defence equipment** · **Industrial products** |
| Information Technology Services (36) | **Large IT services** · **Mid-tier IT** · **Engineering R&D services** |

## 5. Themes (separate from the taxonomy)

Cross-cutting baskets that span groups — tracked like a group (equal-weight
index, RS rating, rotation) but defined by a thesis, not a classification:
AI infrastructure (chips, networking, data-centre power & cooling, utilities);
India defence; India railways; capital-markets plays (brokers, AMCs, exchanges,
depositories); EV supply chain; power & T&D capex. See the playbook §3 and
Phase 6.

## 6. How it would be built (after review)

1. A curated file `data/sub_industries_<market>.csv` (symbol → sub-industry),
   plus a few **rules** where a list is impractical: bank size by market cap,
   biotech stage by revenue, ADR flag by country, fund exclusion by quote type
   and name.
2. The `industries` job applies it, storing a third column in `symbol_industry`;
   unmapped stocks inherit their industry group.
3. The Sectors page gains the level ("Sectors / Industry groups /
   Sub-industries"), and every page that shows a sector (screening, chart
   details, post-market, watchlists) shows *industry group › sub-industry*.
4. Screening gains group context (Phase 3 of the playbook): each candidate's
   group RS rating, so "leader in a leading group" is a filter, not a hunt.

## 6a. Status (built)

Every tradable stock in a split group carries a sub-industry, each with its source
(`marketdata/subindustries.py`): your edits (Library → Sub-industries) › the curated list ›
rules (US banks by size, asset managers vs BDCs) › suggestions awaiting review › official codes
mapped to a sub-industry › for India, BSE's own industry where a group spans several.

- **Official codes** (`marketdata/classcodes.py`, monthly job `subindustries`): India — BSE's
  classification (the exchanges' common 4-level scheme; its "Industry" level has ~140 values such as
  "Heavy Electrical Equipment", "Civil Construction"); US — Nasdaq's SIC-based industry. NSE's own API
  blocks automated access; SEC EDGAR needs a contact e-mail and carries the same SIC codes as Nasdaq.
- **US codes are coarse** (SIC from old filings: most regional banks are "Major Banks"; all chips
  are "Semiconductors"), so US sub-industries are curated by theme; codes are shown as hints.
- **US groups split** (besides the first seven): Software—Application, Semiconductor Equipment,
  Electronic Components, Computer Hardware, Communication Equipment, Specialty Industrial Machinery,
  Medical Devices, Engineering & Construction, Oil & Gas Midstream, IT Services, Internet Content —
  357 tradable stocks labelled as suggestions for review.

## 7. Questions for review

- Are the proposed India sub-industries the cuts you trade by? (e.g. PSU vs
  private banks; T&D vs cables; railway PSUs as their own group)
- US: split foreign ADRs out, or hide them with a toggle?
- Any themes to define first?
