"use strict";
/* Glossary: plain-language definitions, shown where a term is first used.
 *
 * The problem this solves: the guides are written to be read in any order —
 * the Learn hub links straight into any of them — but a term explained in one
 * guide used to be used cold in four others. "QE", "expectancy", "yield curve"
 * and "core inflation" appeared in several guides and were defined in none.
 * A reader without a finance background hit a wall in the first paragraph.
 *
 * So definitions live HERE, once, and `annotate` marks each term's first
 * appearance in whatever document is on screen. A guide's prose does not have
 * to stop and define "basis point" for the fifth time, and a new guide gets
 * the whole vocabulary for free.
 *
 * What belongs here: VOCABULARY — a word whose meaning fits in a sentence or
 * two. What does NOT: a MECHANISM. "Why banks lend to each other overnight"
 * needs paragraphs and worked numbers, and belongs in the guide's own prose;
 * a tooltip that tries to carry it just hides the explanation. If an entry
 * here is growing past `eg`, that is the signal it should be prose instead.
 *
 * Writing rules for `d`, learned from what the guides got wrong:
 *   - no term inside a definition that is not itself defined here;
 *   - say what it IS before what it is FOR;
 *   - prefer a number to an adjective ("1/100th of a percentage point", not
 *     "a very small amount");
 *   - never "simply", "just", "of course", "obviously".
 */
const Glossary = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  /* t: canonical term · aka: other spellings/abbreviations that should match
     d: the definition · eg: a concrete example, usually with numbers
     see: related terms · more: the guide that explains the mechanism in full
     skip: phrases where the word means something else entirely — "base effect"
           in an inflation guide is not a chart base, and "carry more debt" is
           not a carry trade. Marking those teaches the reader something false,
           which is worse than not marking the word at all. */
  const T = [
    // ---------------------------------------------------------------- basics
    { t: "share", aka: ["shares", "stock", "stocks", "equity", "equities"],
      d: "A unit of ownership in a company. Own one share of 100 million and you own one hundred-millionth of the company's profits and assets.",
      see: ["market cap", "dividend"] },
    { t: "index", aka: ["indices", "indexes"],
      d: "A basket of shares tracked as one number, used to describe a whole market. The S&P 500 is 500 large US companies; the Nifty 50 is 50 large Indian ones.",
      eg: "\"The index fell 2%\" means that basket, weighted by company size, is worth 2% less.",
      see: ["market cap", "ETF"], more: "learn-health-trend" },
    { t: "ETF", aka: ["ETFs", "exchange-traded fund", "exchange-traded funds"],
      d: "Exchange-traded fund: a fund that holds a basket of shares and itself trades like a single share. Buying one unit of a Nifty 50 ETF buys a slice of all 50 companies.",
      see: ["index", "index fund"] },
    { t: "index fund", aka: ["index funds"],
      d: "A fund that buys every share in an index in the index's own proportions, rather than picking. It aims to match the index, not beat it, which is why it is cheap to run.",
      see: ["index", "ETF", "expense ratio"] },
    { t: "expense ratio", aka: ["expense ratios"],
      d: "The annual fee a fund charges, as a percent of the money you have in it, deducted daily from the fund's value rather than billed to you. 0.20% on ₹1,00,000 is ₹200 a year.",
      see: ["index fund", "ETF"] },
    { t: "dividend", aka: ["dividends"],
      d: "Cash a company pays out to shareholders from its profits, usually quarterly or annually. A share price chart normally ignores dividends, so it understates what holding the share actually returned.",
      eg: "A ₹2,000 share paying ₹30 a year has a dividend yield of 1.5%.",
      see: ["share", "total return"] },
    { t: "total return", aka: ["total returns"],
      d: "The return including dividends reinvested, not only the price change. Over decades the gap is large: dividends added about 1.9%/yr to the S&P 500 and 0.8%/yr to the Nifty.",
      see: ["dividend"] },
    { t: "market cap", aka: ["market capitalisation", "market capitalization", "large cap", "mid cap", "small cap", "largecap", "midcap", "smallcap"],
      d: "A company's total stock-market value: share price × number of shares. It is how \"large cap\" and \"small cap\" are decided, and how most indices weight their members.",
      eg: "₹500 a share × 20 crore shares = ₹10,000 crore market cap.",
      see: ["share", "index", "float"] },
    { t: "float", aka: ["free float"],
      d: "The number of shares actually available to trade, excluding blocks held by founders, promoters or the government. A small float means fewer shares to go round, so the price moves further on the same demand.",
      see: ["market cap", "liquidity"] },
    { t: "EPS", aka: ["earnings per share"],
      d: "Earnings per share: a company's profit divided by its number of shares — the profit attributable to one share.",
      see: ["P/E", "earnings"] },
    { t: "earnings", aka: ["earnings report", "earnings results", "quarterly results"],
      d: "A company's profit, and the quarterly announcement of it. Share prices often move sharply on the day because the figure is compared against what the market expected, not against zero.",
      see: ["EPS", "P/E"] },
    { t: "P/E", aka: ["P/E ratio", "price-to-earnings", "PE ratio"],
      d: "Price divided by earnings per share: how many years of current profit you are paying for one share. A P/E of 25 means ₹25 of price per ₹1 of annual profit.",
      see: ["EPS", "earnings"] },

    // ------------------------------------------------------- trading mechanics
    { t: "broker", aka: ["brokerage"],
      d: "The firm that holds your account and sends your orders to the exchange. You never deal with the exchange directly.",
      see: ["market order", "limit order"] },
    { t: "market order", aka: ["market orders"],
      d: "An order to buy or sell immediately at whatever price is available. It is certain to execute and uncertain in price — the opposite of a limit order.",
      see: ["limit order", "slippage", "bid-ask spread"] },
    { t: "limit order", aka: ["limit orders"],
      d: "An order to buy or sell only at a stated price or better. It is certain in price and uncertain to execute: if the market never reaches your price, nothing happens.",
      see: ["market order"] },
    { t: "bid-ask spread", aka: ["bid-ask", "bid/ask", "bid and ask", "spread between bid and ask"],
      d: "The gap between the highest price a buyer is offering (the bid) and the lowest a seller is asking. You buy at the ask and sell at the bid, so the spread is a cost you pay on entry and exit.",
      eg: "Bid ₹99.95, ask ₹100.05 — a 10-paisa spread, 0.1% of the price.",
      see: ["liquidity", "slippage"] },
    { t: "slippage",
      d: "The difference between the price you expected and the price you got. It comes from the bid-ask spread and from the market moving while your order travels.",
      see: ["bid-ask spread", "market order"] },
    { t: "liquidity", aka: ["liquid", "illiquid"],
      d: "How easily something can be bought or sold without moving its price. A share trading ₹500 crore a day absorbs a large order; one trading ₹2 crore a day does not.",
      see: ["bid-ask spread", "float", "volume"] },
    { t: "volume",
      d: "The number of shares traded in a period — one bar on a chart is usually one day's volume. It measures participation, not direction: a big move on low volume means few people took part.",
      see: ["liquidity"], more: "learn-health-distribution" },
    { t: "short selling", aka: ["short sell", "shorting", "sold short", "short position"],
      d: "Selling shares you do not own, borrowed from someone who does, hoping to buy them back cheaper. It profits when the price falls, and its losses have no ceiling because a price can keep rising.",
      see: ["leverage", "margin"] },
    { t: "margin", aka: ["on margin", "margin call", "margin calls", "margin account"],
      skip: ["margin squeeze", "interest margin", "profit margin", "operating margin",
             "gross margin", "net margin", "margin expansion", "margin compression", "margin of safety"],
      d: "Money borrowed from your broker to hold a position larger than your cash. It multiplies gains and losses alike, and the broker can force you to sell if the position moves against you (a margin call).",
      see: ["leverage", "short selling"] },
    // a different "margin" entirely — profitability, not borrowing. Kept apart
    // because marking "net interest margin" with the broker definition would be
    // a plain error rather than an unhelpful tooltip.
    { t: "profit margin", aka: ["margins", "operating margin", "net margin", "gross margin", "net interest margin"],
      d: "Profit as a percent of sales — how much of each rupee of revenue survives to the bottom line. A 20% operating margin keeps ₹20 of every ₹100 sold, before interest and tax.",
      see: ["earnings", "EPS"] },
    { t: "leverage", aka: ["leveraged"],
      d: "Using borrowed money so that a position is larger than your own capital. 2× leverage turns a 10% move into a 20% gain or loss.",
      see: ["margin"] },
    { t: "delivery", aka: ["delivery trade", "cash segment"],
      d: "In India, buying shares and actually holding them in your demat account overnight, as opposed to intraday trading that is squared off the same day. Delivery and intraday are taxed and charged differently.",
      see: ["STT", "LTCG"] },
    { t: "STT", aka: ["securities transaction tax"],
      d: "Securities Transaction Tax: an Indian tax charged on the value of each trade, collected by the broker. Small per trade, and a real drag on a strategy that trades often.",
      see: ["delivery", "STCG"] },
    { t: "LTCG", aka: ["long-term capital gains", "long term capital gains"],
      d: "Long-term capital gains tax — on profits from assets held beyond a threshold (12 months for Indian equity). In India, 12.5% above a ₹1.25 lakh annual exemption.",
      see: ["STCG", "STT"] },
    { t: "STCG", aka: ["short-term capital gains", "short term capital gains"],
      d: "Short-term capital gains tax — on profits from assets held under the threshold (12 months for Indian equity), at 20%. Frequent trading realises gains short-term and is taxed hardest.",
      see: ["LTCG", "STT"] },

    // ------------------------------------------------------------ chart terms
    { t: "moving average", aka: ["moving averages", "SMA", "simple moving average", "50-day", "200-day", "50-day average", "200-day average"],
      d: "The average closing price over the last N days, recalculated each day, drawn as a line. It smooths daily noise so the trend is visible; the 50-day and 200-day are the two most watched.",
      eg: "The 200-day average on Monday is the mean of the last 200 closes up to Monday.",
      see: ["EMA", "trend"], more: "learn-health-trend" },
    { t: "EMA", aka: ["exponential moving average"],
      d: "A moving average that weights recent days more heavily, so it turns sooner than a simple average of the same length.",
      see: ["moving average"] },
    { t: "support",
      d: "A price area where buying has repeatedly appeared and stopped a fall. It is not a floor — it is a level where buyers showed up before, and may again.",
      see: ["resistance", "demand zone"], more: "learn-supply-demand" },
    { t: "resistance",
      d: "A price area where selling has repeatedly appeared and stopped a rise, often because people who bought there earlier are waiting to get out even.",
      see: ["support", "supply zone"], more: "learn-supply-demand" },
    { t: "breakout", aka: ["breaks out", "broke out", "breaking out"],
      d: "Price moving decisively above a level it had repeatedly failed to clear, usually on heavier volume. The idea is that the sellers who capped it there have been used up.",
      see: ["resistance", "base", "pivot"], more: "learn-chart-patterns" },
    { t: "base", aka: ["bases", "basing"],
      skip: ["base effect", "base year", "base case", "base rate", "database", "user base", "cost base", "base metal"],
      d: "A period of weeks or months where a share stops advancing and trades sideways in a range, while shares pass from impatient holders to patient ones. Breakouts start from bases.",
      see: ["breakout", "consolidation", "pivot"], more: "learn-bases" },
    { t: "consolidation", aka: ["consolidating", "consolidates"],
      d: "Sideways trading that digests a prior move, rather than reversing it. A base is a consolidation with a shape worth naming.",
      see: ["base"] },
    { t: "pivot", aka: ["pivot point", "pivot price"],
      d: "The specific price that defines a breakout — usually the high of the base's last resistance. Above it the pattern has triggered; below it, it has not.",
      see: ["breakout", "base"] },
    { t: "swing high", aka: ["swing low", "swing highs", "swing lows"],
      d: "A local peak (or trough) on a chart: a bar whose high is higher than the bars either side of it. Swing points are what trend lines and stops get anchored to.",
      see: ["support", "resistance"] },
    { t: "gap", aka: ["gaps", "gapped", "gapping", "gap up", "gap down"],
      skip: ["gap between", "gap in ", "gap of ", "gap to ", "gap was", "gap is ",
             "gap narrow", "gap widen", "the gap closed", "output gap"],
      d: "When a session opens at a price away from the previous close, leaving a blank space on the chart. It matters for risk because a stop order cannot execute inside a gap — it fills at the open instead.",
      eg: "Close ₹500, next open ₹470: a stop at ₹490 fills at ₹470, not ₹490.",
      see: ["stop"], more: "learn-risk-sizing" },
    { t: "RSI", aka: ["relative strength index"],
      d: "A 0–100 indicator comparing the size of recent gains to recent losses, used to judge whether a move has run hot. Above 70 is conventionally \"overbought\", below 30 \"oversold\" — descriptions, not signals.",
      see: ["ADX"] },
    { t: "ADX", aka: ["average directional index"],
      d: "A 0–100 indicator of how strongly a market is trending, in either direction. Above about 25 means a trend is present; it says nothing about which way.",
      see: ["RSI", "trend"] },
    { t: "ATR", aka: ["average true range"],
      d: "Average True Range: the average distance a share travels in a day, including any overnight gap, over the last N days (usually 14). It is the unit used to set stops in a share's own terms rather than a flat percentage.",
      eg: "A ₹1,000 share with ATR ₹25 moves about 2.5% on a normal day.",
      see: ["volatility", "stop"], more: "learn-risk-stops-exits" },
    { t: "relative strength", aka: ["RS", "RS rank", "relative strength rank"],
      d: "How a share has performed against the index or against other shares, rather than on its own. A share up 10% while the index is up 2% is strong on relative strength even though 10% alone says little.",
      see: ["index"], more: "learn-sectors-groups" },

    // -------------------------------------------------------------------- risk
    { t: "stop", aka: ["stop loss", "stop-loss", "stops", "stop order"],
      skip: ["stops where", "stops working", "it stops", "never stops", "stops short",
             "stops rising", "stops falling", "stops being", "stop by", "stops when"],
      d: "A pre-decided price at which you sell to cap a loss, placed when you enter rather than in the moment. It defines how much the trade can cost you.",
      see: ["R-multiple", "gap", "trailing stop"], more: "learn-risk-stops-exits" },
    { t: "trailing stop", aka: ["trailing stops", "trail the stop"],
      d: "A stop that moves up as the price rises and never moves back down, so it locks in gains while leaving room for the trend to continue.",
      see: ["stop"] },
    { t: "R-multiple", aka: ["R multiple", "R-multiples", "1R", "R"],
      skip: ["r&d", "r & d"],
      d: "A trade's result measured in units of what it risked. Risk ₹5,000 and make ₹10,000 and the trade is +2R. It makes trades of different sizes comparable.",
      see: ["stop", "expectancy"], more: "learn-risk-expectancy" },
    { t: "position sizing", aka: ["position size", "sizing"],
      d: "Deciding how many shares to buy, worked out from the distance to your stop so that being wrong costs a fixed amount. The stop decides the size, not the other way round.",
      eg: "Risk ₹10,000, stop ₹20 below entry → 500 shares.",
      see: ["stop", "R-multiple"], more: "learn-risk-sizing" },
    { t: "expectancy",
      d: "The average amount a strategy makes per trade, in R, over many trades: (win rate × average win) − (loss rate × average loss). Positive expectancy is the whole question; a high win rate with large losses can still be negative.",
      eg: "40% wins averaging +2R, 60% losses averaging −1R → (0.4×2) − (0.6×1) = +0.2R per trade.",
      see: ["R-multiple", "win rate", "profit factor"], more: "learn-risk-expectancy" },
    { t: "win rate", aka: ["hit rate"],
      d: "The share of trades that made money. On its own it says nothing about whether a strategy works — it has to be read against how big the wins and losses were.",
      see: ["expectancy", "profit factor"] },
    { t: "profit factor",
      d: "Gross profit divided by gross loss across all trades. Above 1 means the winners outweigh the losers; 1.5 means ₹1.50 made for every ₹1 lost.",
      see: ["expectancy", "win rate"] },
    { t: "drawdown", aka: ["drawdowns", "max drawdown", "maximum drawdown", "underwater"],
      d: "The fall from an account's highest point to its lowest before a new high, as a percent. It is the pain measure: a 50% drawdown needs a 100% gain to get back to even.",
      see: ["volatility", "Calmar"], more: "learn-risk-portfolio" },
    { t: "Kelly", aka: ["Kelly criterion", "Kelly fraction"],
      d: "A formula for the bet size that maximises long-run growth, given your edge. It is best read as a ceiling — betting above it loses money even with a winning strategy — and most traders use a fraction of it, because it assumes you know your edge exactly.",
      see: ["position sizing", "expectancy"], more: "learn-risk-sizing" },
    { t: "correlation", aka: ["correlated", "uncorrelated"],
      d: "How closely two things move together, from +1 (always the same direction) through 0 (unrelated) to −1 (always opposite). Positions that look different but are highly correlated are one bet, not several.",
      see: ["beta", "diversification"], more: "learn-risk-portfolio" },
    { t: "diversification", aka: ["diversified"],
      d: "Spreading money across holdings that do not move together, so that one bad outcome cannot sink the account. Holding ten shares in one sector is not diversification.",
      see: ["correlation"] },
    { t: "beta",
      d: "How much a share moves for a given move in the index. Beta 1.5 means it tends to move 1.5% when the index moves 1%, up or down.",
      see: ["correlation", "volatility"] },
    { t: "Sharpe", aka: ["Sharpe ratio"],
      d: "Return divided by the volatility it took to get it — return per unit of bumpiness. Higher is better; roughly, 0.5 is ordinary, 1.0 is good.",
      see: ["volatility", "Sortino", "Calmar"] },
    { t: "Sortino", aka: ["Sortino ratio"],
      d: "Like Sharpe, but it counts only downside moves as risk, on the view that upside volatility is not something to be penalised for.",
      see: ["Sharpe"] },
    { t: "Calmar", aka: ["Calmar ratio"],
      d: "Annual return divided by the worst drawdown. It asks what you earned per unit of the worst pain you had to sit through.",
      see: ["drawdown", "Sharpe"] },
    { t: "CAGR", aka: ["compound annual growth rate", "annualised return", "annualized return"],
      d: "The single yearly rate that would turn the starting value into the ending value over the whole period. It smooths away the path: the same CAGR can hide a calm ride or a brutal one.",
      eg: "₹1,00,000 → ₹2,00,000 over 10 years is 7.2% CAGR, not 10%.",
      see: ["drawdown", "total return"] },
    { t: "XIRR", aka: ["money-weighted return", "internal rate of return", "IRR"],
      d: "The annual rate that makes a stream of deposits at different dates add up to the final value. It is the right measure when money is going in over time, where CAGR is not.",
      see: ["CAGR", "SIP"] },
    { t: "SIP", aka: ["systematic investment plan", "dollar-cost averaging", "DCA"],
      d: "Investing a fixed amount on a regular schedule — monthly, usually — regardless of price. Called a SIP in India and dollar-cost averaging in the US.",
      see: ["XIRR"] },

    // ------------------------------------------------------------- volatility
    { t: "volatility", aka: ["volatile", "realised volatility", "realized volatility"],
      d: "How much a price swings about, usually the standard deviation of its daily returns stated as an annual percent. It measures size of movement, not direction.",
      see: ["ATR", "VIX", "implied volatility"], more: "learn-health-volatility" },
    { t: "implied volatility", aka: ["IV"],
      d: "The volatility the options market is pricing in for the future, backed out of option prices. Unlike realised volatility, which is history, this is an expectation.",
      see: ["VIX", "volatility"] },
    { t: "VIX", aka: ["India VIX", "volatility index"],
      d: "An index of the volatility the options market expects in the next 30 days, quoted as an annual percent. It rises when traders pay up for protection, which is why it is called a fear gauge.",
      eg: "VIX 16 implies about a 1% daily move; VIX 40 implies about 2.5%.",
      see: ["implied volatility"], more: "learn-health-volatility" },
    { t: "percentile",
      d: "Where a reading sits in its own history. The 90th percentile means higher than 90% of all past readings — the way to tell whether \"VIX 22\" is high without knowing the whole series.",
      see: ["z-score"] },
    { t: "z-score",
      d: "How many standard deviations a reading is from its own average. 0 is typical, +2 is unusually high, −2 unusually low.",
      see: ["percentile", "volatility"] },

    // ---------------------------------------------------------------- breadth
    { t: "breadth",
      d: "How many shares are taking part in a move, rather than what the index did. An index can rise on a handful of giants while most shares fall — breadth is what shows that.",
      see: ["advance-decline line", "index"], more: "learn-health-breadth" },
    { t: "advance-decline line", aka: ["A/D line", "advance-decline", "advancers and decliners", "advancers", "decliners"],
      d: "A running total of how many shares rose minus how many fell each day. Rising with the index means the move is broad; falling while the index rises means it is being carried by a few.",
      see: ["breadth"], more: "learn-health-breadth" },
    { t: "divergence", aka: ["diverges", "diverging"],
      d: "When two measures that usually move together stop doing so — most often the index making a new high while breadth does not. A warning, not a timing signal.",
      see: ["breadth"] },
    { t: "distribution day", aka: ["distribution days"],
      d: "A day the index falls meaningfully on heavier volume than the day before — read as large institutions selling. A cluster of them within a few weeks is the classic warning of a top.",
      see: ["follow-through day", "volume"], more: "learn-health-distribution" },
    { t: "follow-through day", aka: ["follow-through", "follow-through days"],
      d: "A strong, high-volume index gain several days into an attempted rally, used by O'Neil's method to mark a downtrend's end. It confirms a bottom that is already a few days old rather than calling it in advance.",
      see: ["distribution day"], more: "learn-health-distribution" },
    { t: "sector rotation", aka: ["rotation", "rotates"],
      d: "Money moving out of one group of shares and into another as the economic outlook changes — defensives to cyclicals as growth picks up, and back when it slows.",
      see: ["sector"], more: "learn-macro-cycle" },
    { t: "sector", aka: ["sectors", "industry group", "industry groups"],
      d: "A grouping of companies in the same line of business — banks, technology, energy. Shares in a group tend to move together, which makes the group a better unit of analysis than the single share.",
      see: ["sector rotation", "relative strength"], more: "learn-sectors-groups" },

    // ------------------------------------------------------------------ macro
    { t: "basis point", aka: ["basis points", "bp", "bps"],
      d: "One hundredth of a percentage point. A rate moving from 6.00% to 6.25% has moved 25 basis points. Used because \"a 1% rise\" is ambiguous between 6%→7% and 6%→6.06%.",
      see: ["policy rate"] },
    { t: "central bank", aka: ["central banks", "the Fed", "Federal Reserve", "RBI", "Reserve Bank of India", "FOMC", "MPC"],
      d: "The institution that sets a country's short-term interest rate and manages the supply of money — the Federal Reserve in the US, the Reserve Bank of India in India. It is not a commercial bank; its customers are banks and the government.",
      see: ["policy rate", "reserves"], more: "learn-macro-rates" },
    { t: "policy rate", aka: ["policy rates", "fed funds rate", "federal funds rate", "repo rate", "overnight rate"],
      d: "The interest rate the central bank sets for lending that lasts one night, which every other rate is built on. In the US it is the fed funds rate; in India, the repo rate.",
      see: ["central bank", "reserves", "basis point"], more: "learn-macro-rates" },
    { t: "reserves", aka: ["reserve balances", "bank reserves"],
      d: "Money commercial banks hold in their accounts at the central bank, used to settle payments between each other at the end of every day. Banks short of reserves borrow them overnight from banks with a surplus.",
      see: ["policy rate", "central bank"], more: "learn-macro-rates" },
    { t: "yield", aka: ["yields", "bond yield", "bond yields"],
      d: "The annual return a bond pays at its current price, as a percent. Prices and yields move in opposite directions: pay less for the same fixed payments and your yield is higher.",
      see: ["bond", "Treasury", "yield curve"], more: "learn-macro-yield-curve" },
    { t: "bond", aka: ["bonds"],
      d: "A loan to a government or company, tradeable like a share. You lend a sum, receive fixed interest for a set number of years, and get the sum back at the end.",
      see: ["yield", "coupon", "duration"], more: "learn-macro-yield-curve" },
    { t: "coupon", aka: ["coupons"],
      d: "The fixed interest payment a bond makes, as a percent of its original face value. It never changes; the bond's price does, which is what moves its yield.",
      see: ["bond", "yield"] },
    { t: "Treasury", aka: ["Treasuries", "T-bill", "T-bills", "Treasury bill", "Treasury bills", "government bond", "government bonds", "G-sec"],
      d: "Debt issued by a national government — the US Treasury, or Indian G-secs. Treated as the risk-free benchmark, because a government that prints its own currency can always repay in it.",
      see: ["bond", "yield"] },
    { t: "yield curve",
      d: "A chart of what the government pays to borrow across every length of loan, from 3 months out to 30 years. Normally it slopes up, because lending for longer deserves more.",
      see: ["yield", "inversion", "term premium"], more: "learn-macro-yield-curve" },
    { t: "inversion", aka: ["inverted", "inverted curve", "curve inversion"],
      d: "When short-term rates sit above long-term ones — the yield curve upside down. It means the market expects rates to be cut, which usually means it expects a recession. It has preceded most US recessions.",
      see: ["yield curve", "recession"], more: "learn-macro-yield-curve" },
    { t: "term premium",
      d: "The extra yield a lender demands for tying money up for longer, on top of where rates are expected to go. It is the part of a long yield that is compensation for uncertainty rather than a forecast.",
      see: ["yield curve", "duration"] },
    { t: "duration",
      d: "How much a bond's price moves when yields move, expressed in years. Duration 7 means a 1% rise in yields costs about 7% of the price — which is why long bonds fall hardest when rates rise.",
      see: ["bond", "yield"] },
    { t: "discount rate",
      d: "The rate used to convert future money into what it is worth today, because money later is worth less than money now. Raise it and the same future profits are worth less — which is how interest rates move share prices with no change in the business.",
      eg: "₹100 in 10 years is worth ₹61 today at 5%, but ₹39 at 10%.",
      see: ["yield", "policy rate"], more: "learn-macro-rates" },
    { t: "real yield", aka: ["real rate", "real rates", "real return"],
      d: "A rate after subtracting inflation — what you actually gain in purchasing power. 7% interest with 6% inflation is a 1% real yield.",
      see: ["nominal", "inflation"] },
    { t: "nominal",
      d: "A figure before adjusting for inflation — the number as quoted. Its opposite is \"real\", which is the same figure after inflation is taken out.",
      see: ["real yield", "inflation"] },
    { t: "inflation",
      d: "The rate at which prices in general rise, so each unit of money buys less. Usually quoted as the change over the same month a year earlier.",
      see: ["CPI", "core inflation", "real yield"], more: "learn-macro-inflation" },
    { t: "CPI", aka: ["consumer price index"],
      d: "Consumer Price Index: the price of a fixed basket of what households actually buy, tracked monthly. It is the main inflation number both the Fed and the RBI target.",
      see: ["inflation", "core inflation"], more: "learn-macro-inflation" },
    { t: "core inflation", aka: ["core CPI", "core inflation rate"],
      d: "Inflation excluding food and fuel, whose prices swing on weather and oil rather than on the economy. Central banks watch it because it shows the underlying trend they can actually influence — though in India food is nearly half the basket, so headline inflation still drives policy.",
      see: ["CPI", "inflation"], more: "learn-macro-inflation" },
    { t: "QE", aka: ["quantitative easing"],
      d: "Quantitative easing: a central bank creating new reserves to buy bonds, which pushes their prices up and yields down. Used when the policy rate is already near zero and cannot go lower.",
      see: ["QT", "reserves", "liquidity"], more: "learn-macro-liquidity-credit" },
    { t: "QT", aka: ["quantitative tightening"],
      d: "Quantitative tightening: the reverse of QE — the central bank lets its bonds mature without replacing them, draining reserves from the system.",
      see: ["QE", "reserves"], more: "learn-macro-liquidity-credit" },
    { t: "credit spread", aka: ["credit spreads", "spreads"],
      d: "The extra yield a company must pay to borrow over what the government pays for the same length of loan. It is the market's price of default risk, and it widens before trouble becomes visible in share prices.",
      see: ["yield", "bond"], more: "learn-macro-liquidity-credit" },
    { t: "hawkish", aka: ["hawk", "hawks"],
      d: "Leaning towards higher interest rates, because inflation is the bigger worry. Its opposite is dovish.",
      see: ["dovish", "policy rate"] },
    { t: "dovish", aka: ["dove", "doves"],
      d: "Leaning towards lower interest rates, because growth and jobs are the bigger worry. Its opposite is hawkish.",
      see: ["hawkish", "policy rate"] },
    { t: "GDP", aka: ["gross domestic product"],
      d: "Gross Domestic Product: the total value of everything a country produces in a period, the standard measure of the size of an economy. Reported quarterly, and well after the fact.",
      see: ["recession", "PMI"], more: "learn-macro-cycle" },
    { t: "recession",
      d: "A broad, sustained contraction in economic activity. The common shorthand is two consecutive quarters of falling GDP, though in the US an official committee decides using a wider set of measures.",
      see: ["GDP", "inversion"], more: "learn-macro-cycle" },
    { t: "PMI", aka: ["purchasing managers index", "purchasing managers' index"],
      d: "Purchasing Managers' Index: a monthly survey of company purchasing managers. Above 50 means more of them report expansion than contraction. Its value is timeliness — it arrives long before GDP.",
      see: ["GDP"], more: "learn-macro-cycle" },
    { t: "carry trade", aka: ["carry trades"],
      d: "Borrowing where interest rates are low and investing where they are high, pocketing the difference. It works until the currency moves against you, which it tends to do suddenly.",
      see: ["FII"], more: "learn-macro-currencies" },
    { t: "FII", aka: ["FIIs", "FPI", "FPIs", "foreign institutional investor", "foreign institutional investors"],
      d: "Foreign Institutional Investors: overseas funds buying Indian shares. Their flows are large enough to move the market, and they are sensitive to the rupee and to US interest rates.",
      see: ["DII", "carry trade"], more: "learn-macro-currencies" },
    { t: "DII", aka: ["DIIs", "domestic institutional investor", "domestic institutional investors"],
      d: "Domestic Institutional Investors: Indian mutual funds, insurers and pension funds. Monthly SIP money makes their buying steadier than foreign flows, and they often absorb FII selling.",
      see: ["FII", "SIP"], more: "learn-macro-currencies" },
  ];

  // index by every spelling, longest first so "moving average" wins over "average"
  const BY = new Map();
  for (const e of T) for (const k of [e.t, ...(e.aka || [])]) BY.set(k.toLowerCase(), e);
  const KEYS = [...BY.keys()].sort((a, b) => b.length - a.length);
  const key = (e) => e.t.toLowerCase().replace(/[^a-z0-9]+/g, "-");

  /** one pattern, alternation of every spelling, longest first.
   *  \b fails on terms ending in punctuation ("P/E", "A/D line"), so the
   *  boundaries are explicit: not preceded/followed by a word character. */
  const RE = new RegExp("(?<![\\w-])(" + KEYS.map((k) =>
    k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/[\s-]+/g, "[\\s-]+")).join("|") + ")(?![\\w-])", "i");

  const popHtml = (e) => `<b>${esc(e.t)}</b><p>${esc(e.d)}</p>`
    + (e.eg ? `<p class="gl-eg">${esc(e.eg)}</p>` : "")
    + (e.see && e.see.length ? `<p class="gl-see">See also: ${e.see.map(esc).join(", ")}</p>` : "");

  /** Mark the FIRST use of each term inside `root`.
   *
   *  Once per term per document on purpose: marking every "volume" in a guide
   *  that says it ninety times would be unreadable, and the reader only needs
   *  the definition the first time. Skips headings (a dotted underline in an
   *  <h2> looks like damage), code, links and anything already marked. */
  function annotate(root) {
    if (!root) return 0;
    // TH is deliberately NOT skipped. A results table's header row — CAGR,
    // Expectancy, Profit factor, Max drawdown — is the densest jargon in any
    // guide and the place a reader most needs the definition. Section
    // headings (H1-H6) are skipped instead: they are navigation, and the term
    // in them always recurs in the prose underneath.
    const SKIP = /^(CODE|PRE|A|H1|H2|H3|H4|H5|H6|BUTTON|SCRIPT|STYLE|FIGCAPTION)$/;
    const used = new Set();
    let n = 0;
    // collect first, mutate after — editing during a TreeWalker invalidates it
    const nodes = [];
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(t) {
        if (!t.nodeValue || !t.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        for (let p = t.parentNode; p && p !== root; p = p.parentNode) {
          if (SKIP.test(p.nodeName) || (p.classList && p.classList.contains("gl"))) return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    for (let t = w.nextNode(); t; t = w.nextNode()) nodes.push(t);

    for (const node of nodes) {
      let text = node.nodeValue, out = null, cursor = 0;
      const frag = document.createDocumentFragment();
      let m;
      const re = new RegExp(RE.source, "gi");
      while ((m = re.exec(text))) {
        const e = BY.get(m[0].toLowerCase().replace(/[\s-]+/g, " "))
               || BY.get(m[0].toLowerCase());
        if (!e || used.has(e.t)) continue;
        // the word may be the other meaning of itself — look at what it sits in
        if (e.skip) {
          const around = text.slice(Math.max(0, m.index - 24), m.index + m[0].length + 24).toLowerCase();
          if (e.skip.some((phrase) => around.includes(phrase))) continue;
        }
        used.add(e.t);
        out = true;
        frag.appendChild(document.createTextNode(text.slice(cursor, m.index)));
        const b = document.createElement("button");
        b.type = "button";
        b.className = "gl";
        b.dataset.gl = key(e);
        b.textContent = m[0];
        b.setAttribute("aria-label", `${e.t} — what this means`);
        frag.appendChild(b);
        cursor = m.index + m[0].length;
        n++;
      }
      if (out) {
        frag.appendChild(document.createTextNode(text.slice(cursor)));
        node.parentNode.replaceChild(frag, node);
      }
    }
    return n;
  }

  /** the shared popover: one element, moved to whichever term is active */
  let pop = null, open = null;
  function ensure() {
    if (pop) return pop;
    pop = document.createElement("div");
    pop.className = "gl-pop";
    pop.hidden = true;
    document.body.appendChild(pop);
    addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
    // Follow the term rather than closing. A capture-phase scroll listener sees
    // every scrollable element on the page — a chart finishing its layout used
    // to close the popover the instant it opened.
    addEventListener("scroll", () => { if (open) place(open); }, true);
    addEventListener("resize", () => { if (open) place(open); });
    return pop;
  }

  /** anchor the popover to `btn`: below it, or above when the room is there
   *  instead, and never off either side. Hides once the term scrolls away. */
  function place(btn) {
    const p = ensure(), r = btn.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) { hide(); return; }
    const pw = Math.min(340, innerWidth - 24);
    p.style.width = pw + "px";
    const ph = p.offsetHeight;
    const below = innerHeight - r.bottom > ph + 12;
    p.style.top = (below ? r.bottom + 8 : Math.max(8, r.top - ph - 8)) + scrollY + "px";
    p.style.left = Math.max(12, Math.min(r.left + scrollX, scrollX + innerWidth - pw - 12)) + "px";
  }

  function show(btn) {
    const e = [...BY.values()].find((x) => key(x) === btn.dataset.gl);
    if (!e) return;
    const p = ensure();
    p.innerHTML = popHtml(e);
    p.hidden = false;
    open = btn;
    place(btn);
  }
  function hide() { if (pop) { pop.hidden = true; open = null; } }

  /** delegated, so it keeps working for terms added after a re-render */
  function bind() {
    if (bind.done) return;
    bind.done = true;
    document.addEventListener("click", (ev) => {
      const b = ev.target.closest && ev.target.closest("button.gl");
      if (b) { ev.preventDefault(); open === b ? hide() : show(b); } else if (!ev.target.closest(".gl-pop")) hide();
    });
    document.addEventListener("mouseover", (ev) => {
      const b = ev.target.closest && ev.target.closest("button.gl");
      if (b && b !== open) show(b);
    });
    document.addEventListener("mouseout", (ev) => {
      const b = ev.target.closest && ev.target.closest("button.gl");
      // keep it up while the pointer is inside the popover itself
      if (b && !(ev.relatedTarget && ev.relatedTarget.closest && ev.relatedTarget.closest(".gl-pop"))) hide();
    });
    document.addEventListener("focusin", (ev) => {
      const b = ev.target.closest && ev.target.closest("button.gl");
      if (b) show(b);
    });
  }

  /** every term, for the glossary page */
  function all() { return T.slice().sort((a, b) => a.t.localeCompare(b.t, "en", { sensitivity: "base" })); }

  return { TERMS: T, all, annotate, bind, html: popHtml, keyOf: key,
           get: (t) => BY.get(String(t).toLowerCase()) };
})();
