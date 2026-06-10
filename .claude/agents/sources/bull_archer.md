# Intel Center sources -- Bull Archer

**Total assigned:** 67 resources across 3 categories.

## How to use this manifest

When a user query lands in your domain, READ this manifest FIRST and prefer these sources over guessing. Three modes:

1. **Search:** `intel search <query>` -- full-text across 745 resources
2. **Pull live:** `intel pull <domain>` -- fetch RSS/HTML, cache it, get latest items
3. **Investigate:** `intel investigate <target>` -- multi-source OSINT (port 8677)

Each resource below shows its **use_case** (how YOU specifically use it) and **setup_steps** (how to actually invoke it).

## Aviation & Maritime  (6)

### [adsb.fi](https://adsb.fi)
_Community flight tracking data_

**Use case:** Bull Archer tracks adsb.fi for live flight, vessel, or supply-chain movement. Use to confirm physical presence (charter routes, cargo deliveries, anomalies in port traffic).

**Setup:**
  1. Open https://adsb.fi.
  2. Live pull: `intel pull adsb.fi` -- captures positions if a public API exists.
  3. Cross-reference with logistics-desk shipment tracker.

### [dronezon.com](https://dronezon.com)
_Learn drone systems flight control and sensors_

**Use case:** Bull Archer tracks dronezon.com for live flight, vessel, or supply-chain movement. Use to confirm physical presence (charter routes, cargo deliveries, anomalies in port traffic).

**Setup:**
  1. Open https://dronezon.com.
  2. Live pull: `intel pull dronezon.com` -- captures positions if a public API exists.
  3. Cross-reference with logistics-desk shipment tracker.

### [flightradar24.com](https://flightradar24.com)
_live flights across the globe_

**Use case:** Bull Archer tracks flightradar24.com for live flight, vessel, or supply-chain movement. Use to confirm physical presence (charter routes, cargo deliveries, anomalies in port traffic).

**Setup:**
  1. Open https://flightradar24.com.
  2. Live pull: `intel pull flightradar24.com` -- captures positions if a public API exists.
  3. Cross-reference with logistics-desk shipment tracker.

### [globe.adsbexchange.com](https://globe.adsbexchange.com)
_Track aircraft globally and flight patterns_

**Use case:** Bull Archer tracks globe.adsbexchange.com for live flight, vessel, or supply-chain movement. Use to confirm physical presence (charter routes, cargo deliveries, anomalies in port traffic).

**Setup:**
  1. Open https://globe.adsbexchange.com.
  2. Live pull: `intel pull globe.adsbexchange.com` -- captures positions if a public API exists.
  3. Cross-reference with logistics-desk shipment tracker.

### [marinetraffic.com](https://marinetraffic.com)
_Track every ship on Earth right now_

**Use case:** Bull Archer tracks marinetraffic.com for live flight, vessel, or supply-chain movement. Use to confirm physical presence (charter routes, cargo deliveries, anomalies in port traffic).

**Setup:**
  1. Open https://marinetraffic.com.
  2. Live pull: `intel pull marinetraffic.com` -- captures positions if a public API exists.
  3. Cross-reference with logistics-desk shipment tracker.

### [opensky-network.org](https://opensky-network.org)
_live global air traffic data_

**Use case:** Bull Archer tracks opensky-network.org for live flight, vessel, or supply-chain movement. Use to confirm physical presence (charter routes, cargo deliveries, anomalies in port traffic).

**Setup:**
  1. Open https://opensky-network.org.
  2. Live pull: `intel pull opensky-network.org` -- captures positions if a public API exists.
  3. Cross-reference with logistics-desk shipment tracker.

## Economics & Markets  (1)

### [bea.gov](https://bea.gov)
_U.S. International Trade in Goods and Services, March 2026_

**Use case:** Brief Calloway pulled bea.gov live via `intel pull`. Latest items cached at cache/articles/. Refresh anytime: `intel pull bea.gov`.

**Setup:**
  1. Open https://bea.gov.
  2. Pull latest items: `intel pull bea.gov`.
  3. View detail at /09_Dashboard/resource.html?d=bea.gov

## Trading & Finance  (60)

### [abebooks.com](https://abebooks.com)
_Rare first edition antiquarian book prices_

**Use case:** Bull Archer pulls abebooks.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://abebooks.com.
  2. Pull a snapshot: `intel pull abebooks.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [aerolite.org](https://aerolite.org)
_Martian and lunar meteorite prices listed_

**Use case:** Bull Archer pulls aerolite.org for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://aerolite.org.
  2. Pull a snapshot: `intel pull aerolite.org`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [alphaspread.com](https://alphaspread.com)
_Check if a stock is overpriced_

**Use case:** Bull Archer pulls alphaspread.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://alphaspread.com.
  2. Pull a snapshot: `intel pull alphaspread.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [antiquearmsinc.com](https://antiquearmsinc.com)
_historical weapon collector prices_

**Use case:** Bull Archer pulls antiquearmsinc.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://antiquearmsinc.com.
  2. Pull a snapshot: `intel pull antiquearmsinc.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [aquabid.com](https://aquabid.com)
_Rare exotic tropical live fish prices_

**Use case:** Bull Archer pulls aquabid.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://aquabid.com.
  2. Pull a snapshot: `intel pull aquabid.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [asianmetal.com](https://asianmetal.com)
_Bismuth selenium tellurium minor metal prices_

**Use case:** Bull Archer pulls asianmetal.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://asianmetal.com.
  2. Pull a snapshot: `intel pull asianmetal.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [barchart.com](https://barchart.com)
_Options and futures data with free charting tools_

**Use case:** Bull Archer pulls barchart.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://barchart.com.
  2. Pull a snapshot: `intel pull barchart.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [barnebys.com](https://barnebys.com)
_Global rare collectible auction price search_

**Use case:** Bull Archer pulls barnebys.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://barnebys.com.
  2. Pull a snapshot: `intel pull barnebys.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [beckett.com](https://beckett.com)
_Rare sports trading card graded values_

**Use case:** Bull Archer pulls beckett.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://beckett.com.
  2. Pull a snapshot: `intel pull beckett.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [benchmarkminerals.com](https://benchmarkminerals.com)
_Lithium cobalt battery mineral prices_

**Use case:** Bull Archer pulls benchmarkminerals.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://benchmarkminerals.com.
  2. Pull a snapshot: `intel pull benchmarkminerals.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [benzinga.com](https://benzinga.com)
_world’s Fastest breaking market news_

**Use case:** Bull Archer pulls benzinga.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://benzinga.com.
  2. Pull a snapshot: `intel pull benzinga.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [bondsupermart.com](https://bondsupermart.com)
_Compare global bonds_

**Use case:** Bull Archer pulls bondsupermart.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://bondsupermart.com.
  2. Pull a snapshot: `intel pull bondsupermart.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [chrono24.com](https://chrono24.com)
_vintage luxury watch global prices_

**Use case:** Bull Archer pulls chrono24.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://chrono24.com.
  2. Pull a snapshot: `intel pull chrono24.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [clankapp.com](https://clankapp.com)
_live massive blockchain capital flows_

**Use case:** Bull Archer pulls clankapp.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://clankapp.com.
  2. Pull a snapshot: `intel pull clankapp.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [coindesk.com](https://coindesk.com)
_Ripple-linked XRP holds near $1.46 as breakout attempt fades despite $200 million raise_

**Use case:** Bull Archer pulled coindesk.com live via `intel pull`. Latest items cached at cache/articles/. Refresh anytime: `intel pull coindesk.com`.

**Setup:**
  1. Open https://coindesk.com.
  2. Pull latest items: `intel pull coindesk.com`.
  3. View detail at /09_Dashboard/resource.html?d=coindesk.com

### [coingecko.com](https://coingecko.com)
_Crypto prices rankings and stats_

**Use case:** Bull Archer pulls coingecko.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://coingecko.com.
  2. Pull a snapshot: `intel pull coingecko.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [cryptobubbles.net](https://cryptobubbles.net)
_Shows every crypto gain/ loss as bubbles_

**Use case:** Bull Archer pulls cryptobubbles.net for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://cryptobubbles.net.
  2. Pull a snapshot: `intel pull cryptobubbles.net`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [currentmarketvaluation.com](https://currentmarketvaluation.com)
_long-term stock market valuation models_

**Use case:** Bull Archer pulls currentmarketvaluation.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://currentmarketvaluation.com.
  2. Pull a snapshot: `intel pull currentmarketvaluation.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [dataroma.com](https://dataroma.com)
_View top investors stock picks_

**Use case:** Bull Archer pulls dataroma.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://dataroma.com.
  2. Pull a snapshot: `intel pull dataroma.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [defillama.com](https://defillama.com)
_largest aggregator for DeFi_

**Use case:** Bull Archer pulls defillama.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://defillama.com.
  2. Pull a snapshot: `intel pull defillama.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [dividendhistory.org](https://dividendhistory.org)
_stock dividend history records_

**Use case:** Bull Archer pulls dividendhistory.org for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://dividendhistory.org.
  2. Pull a snapshot: `intel pull dividendhistory.org`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [fastmarkets.com](https://fastmarkets.com)
_earth magnet neodymium prices_

**Use case:** Bull Archer pulls fastmarkets.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://fastmarkets.com.
  2. Pull a snapshot: `intel pull fastmarkets.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [findyourstampsvalue.com](https://findyourstampsvalue.com)
_vintage postage stamp values_

**Use case:** Bull Archer pulls findyourstampsvalue.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://findyourstampsvalue.com.
  2. Pull a snapshot: `intel pull findyourstampsvalue.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [gemval.com](https://gemval.com)
_colored gemstone price per carat_

**Use case:** Bull Archer pulls gemval.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://gemval.com.
  2. Pull a snapshot: `intel pull gemval.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [istdibs.com](https://istdibs.com)
_Rare luxury furniture and design object prices_

**Use case:** Bull Archer pulls istdibs.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://istdibs.com.
  2. Pull a snapshot: `intel pull istdibs.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [kingsnake.com](https://kingsnake.com)
_exotic reptile live market prices_

**Use case:** Bull Archer pulls kingsnake.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://kingsnake.com.
  2. Pull a snapshot: `intel pull kingsnake.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [labx.com](https://labx.com)
_rare used scientific equipment market prices_

**Use case:** Bull Archer pulls labx.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://labx.com.
  2. Pull a snapshot: `intel pull labx.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [liv-ex.com](https://liv-ex.com)
_Fine wine investment exchange price database_

**Use case:** Bull Archer pulls liv-ex.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://liv-ex.com.
  2. Pull a snapshot: `intel pull liv-ex.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [marketscreener.com](https://marketscreener.com)
_reliable Global stock news_

**Use case:** Bull Archer pulls marketscreener.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://marketscreener.com.
  2. Pull a snapshot: `intel pull marketscreener.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [mineralauctions.com](https://mineralauctions.com)
_mineral crystal auction prices_

**Use case:** Bull Archer pulls mineralauctions.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://mineralauctions.com.
  2. Pull a snapshot: `intel pull mineralauctions.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [moneycrashers.com](https://moneycrashers.com)
_how to manage money and build wealth_

**Use case:** Bull Archer pulls moneycrashers.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://moneycrashers.com.
  2. Pull a snapshot: `intel pull moneycrashers.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [morningstar.com](https://morningstar.com)
_essential research and investor education_

**Use case:** Bull Archer pulls morningstar.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://morningstar.com.
  2. Pull a snapshot: `intel pull morningstar.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [mpb.com](https://mpb.com)
_vintage camera and lens prices_

**Use case:** Bull Archer pulls mpb.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://mpb.com.
  2. Pull a snapshot: `intel pull mpb.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [mrmoneymustache.com](https://mrmoneymustache.com)
_Early retirement plans/lifestyle guides_

**Use case:** Bull Archer pulls mrmoneymustache.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://mrmoneymustache.com.
  2. Pull a snapshot: `intel pull mrmoneymustache.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [mutualart.com](https://mutualart.com)
_Fine art global auction realized prices_

**Use case:** Bull Archer pulls mutualart.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://mutualart.com.
  2. Pull a snapshot: `intel pull mutualart.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [nerdwallet.com](https://nerdwallet.com)
_essential financial product comparison tool_

**Use case:** Bull Archer pulls nerdwallet.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://nerdwallet.com.
  2. Pull a snapshot: `intel pull nerdwallet.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [optionstrat.com](https://optionstrat.com)
_Visualize any options strategy before trading_

**Use case:** Bull Archer pulls optionstrat.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://optionstrat.com.
  2. Pull a snapshot: `intel pull optionstrat.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [orchidweb.com](https://orchidweb.com)
_exotic orchid species current price_

**Use case:** Bull Archer pulls orchidweb.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://orchidweb.com.
  2. Pull a snapshot: `intel pull orchidweb.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [paulmerriman.com](https://paulmerriman.com)
_investment education guides(free)_

**Use case:** Bull Archer pulls paulmerriman.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://paulmerriman.com.
  2. Pull a snapshot: `intel pull paulmerriman.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [pineify.app](https://pineify.app)
_IPO, dividend, earnings calendar_

**Use case:** Bull Archer pulls pineify.app for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://pineify.app.
  2. Pull a snapshot: `intel pull pineify.app`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [portfoliocharts.com](https://portfoliocharts.com)
_portfolio performance comparisons_

**Use case:** Bull Archer pulls portfoliocharts.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://portfoliocharts.com.
  2. Pull a snapshot: `intel pull portfoliocharts.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [pricecharting.com](https://pricecharting.com)
_-vintage game and card prices_

**Use case:** Bull Archer pulls pricecharting.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://pricecharting.com.
  2. Pull a snapshot: `intel pull pricecharting.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [purekopiluwak.com](https://purekopiluwak.com)
_Wild civet kopi luwak coffee prices_

**Use case:** Bull Archer pulls purekopiluwak.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://purekopiluwak.com.
  2. Pull a snapshot: `intel pull purekopiluwak.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [rrauction.com](https://rrauction.com)
_Rare historical autograph auction prices_

**Use case:** Bull Archer pulls rrauction.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://rrauction.com.
  2. Pull a snapshot: `intel pull rrauction.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [saffron.com](https://saffron.com)
_Premium saffron current retail market prices_

**Use case:** Bull Archer pulls saffron.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://saffron.com.
  2. Pull a snapshot: `intel pull saffron.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [sidehustlenation.com](https://sidehustlenation.com)
_side hustle ideas and strategies_

**Use case:** Bull Archer pulls sidehustlenation.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://sidehustlenation.com.
  2. Pull a snapshot: `intel pull sidehustlenation.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [stonealgo.com](https://stonealgo.com)
_Fancy color diamond daily price index_

**Use case:** Bull Archer pulls stonealgo.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://stonealgo.com.
  2. Pull a snapshot: `intel pull stonealgo.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [strategicmetalsinvest.com](https://strategicmetalsinvest.com)
_Gallium, Hafnium, Indium, Rhenium prices_

**Use case:** Bull Archer pulls strategicmetalsinvest.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://strategicmetalsinvest.com.
  2. Pull a snapshot: `intel pull strategicmetalsinvest.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [sword-site.com](https://sword-site.com)
_antique sword and blade prices_

**Use case:** Bull Archer pulls sword-site.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://sword-site.com.
  2. Pull a snapshot: `intel pull sword-site.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [tartufo.com](https://tartufo.com)
_Daily updated white and black truffle prices_

**Use case:** Bull Archer pulls tartufo.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://tartufo.com.
  2. Pull a snapshot: `intel pull tartufo.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [thestreet.com](https://thestreet.com)
_Reliable market commentary and stock ideas_

**Use case:** Bull Archer pulls thestreet.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://thestreet.com.
  2. Pull a snapshot: `intel pull thestreet.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [tradingeconomics.com](https://tradingeconomics.com)
_Economic data for many countries_

**Use case:** Bull Archer pulls tradingeconomics.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://tradingeconomics.com.
  2. Pull a snapshot: `intel pull tradingeconomics.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [tradingview.com](https://tradingview.com)
_Advanced charts for all markets_

**Use case:** Bull Archer pulls tradingview.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://tradingview.com.
  2. Pull a snapshot: `intel pull tradingview.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [trocadero.com](https://trocadero.com)
_tribal ethnographic artifact prices_

**Use case:** Bull Archer pulls trocadero.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://trocadero.com.
  2. Pull a snapshot: `intel pull trocadero.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [vintageguitar.com](https://vintageguitar.com)
_vintage guitar market price guide_

**Use case:** Bull Archer pulls vintageguitar.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://vintageguitar.com.
  2. Pull a snapshot: `intel pull vintageguitar.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [wallstreetzen.com](https://wallstreetzen.com)
_Find undervalued stocks using DCF_

**Use case:** Bull Archer pulls wallstreetzen.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://wallstreetzen.com.
  2. Pull a snapshot: `intel pull wallstreetzen.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [wealthfolio.app](https://wealthfolio.app) *(curated)*
_Local investment tracker,,private,open source_

**Use case:** Bull Archer pulls wealthfolio.app for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://wealthfolio.app.
  2. Pull a snapshot: `intel pull wealthfolio.app`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [wid.world](https://wid.world)
_find Where you rank in global wealth distribution_

**Use case:** Bull Archer pulls wid.world for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://wid.world.
  2. Pull a snapshot: `intel pull wid.world`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [woodworkerssource.com](https://woodworkerssource.com)
_Rare exotic hardwood lumber prices_

**Use case:** Bull Archer pulls woodworkerssource.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://woodworkerssource.com.
  2. Pull a snapshot: `intel pull woodworkerssource.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.

### [worthpoint.com](https://worthpoint.com)
_antique collectible realized prices_

**Use case:** Bull Archer pulls worthpoint.com for prices, on-chain flows, options, or portfolio reference. Cross-check against XLM bot signals and broker pipeline stage.

**Setup:**
  1. Open https://worthpoint.com.
  2. Pull a snapshot: `intel pull worthpoint.com`.
  3. For automated tracking, wire into `06_DEVELOPMENT/xlm_bot/` if relevant.
