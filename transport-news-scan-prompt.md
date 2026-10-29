You are running the daily Transportation News scan for a transportation engineering PhD researcher (CAV, AI/ML for transportation, shared mobility, traffic data). The digest feeds the Transportation News tab of a local HTML dashboard. Nobody is watching interactively. Use today's actual local date and finish without asking questions.

Working directory: `05 Career/`. Read `automation/transport-news-state.json` first. It has arrays named `av`, `maps`, `tdata`, `rideshare`, `policy`, and `evidence`; each contains URLs already reported. If absent or invalid, initialize those arrays. Read the latest prior `automation/transport-news-digests/*.md` so you do not repeat a story under a different URL.

Search for **new developments since the last scan** (on the first run, the past ~2 weeks). The goal is to show where the technology and industry stand now. Cover these six sections:

1. **Autonomous Vehicles**: deployment status, service-area expansions, fleet size, new cities, safety reports, technical posts and research from Waymo, Tesla (FSD / Robotaxi), Zoox, Aurora, Kodiak, May Mobility, Nuro, Wayve, Mobileye, Baidu Apollo Go, Pony.ai, WeRide, and comparable companies. Check each company's own blog or newsroom first (e.g. waymo.com/blog, aurora.tech/newsroom, zoox.com/journal).
2. **Maps & Navigation**: product and technical updates from Google Maps (blog.google/products/maps), Apple Maps, Waze, HERE, TomTom, and Mapbox: routing, traffic prediction, lane-level maps, AI features, EV routing.
3. **Traffic Data & Open Data**: OpenStreetMap (OSM Foundation blog, OSM Weekly), Overture Maps Foundation, INRIX, StreetLight Data, Replica, Iteris, and public open-data releases (e.g. USDOT, FHWA, NHTSA datasets). Note what the data covers and who can access it.
4. **Ride-hailing & Shared Mobility**: Uber (uber.com/newsroom, Uber Engineering blog), Lyft (lyft.com/blog, Lyft Engineering), DiDi, Lime, Via, and Bolt: AV partnerships, pricing/matching research, quarterly results that reveal ridership trends, micromobility.
5. **Policy & Safety**: regulation and safety events that change what these companies can do: NHTSA (standing general order crash data, investigations, exemptions), California DMV / CPUC AV permits, state laws, USDOT and FHWA guidance, and major non-US AV rules.

6. **Research Evidence** (the candidate's favourite kind of item; spend real effort here): newly published peer-reviewed papers and serious preprints that use **real-world data** to measure how deployed transportation technology behaves and what it does to the system. The model example is "How Do Waymo Self-Driving Cars Impact Traffic Flow? Evidence from Empirical Data" (Chen, Li, Laval, Ahn & Zheng, *Data Science for Transportation*, Oct 2026, https://doi.org/10.1007/s42421-026-00177-1): it used large-scale Waymo driving data to estimate spacing–speed and flow–density relations and found driverless cars keep larger gaps, cutting arterial capacity by about 18%, with nearby human drivers also becoming more conservative.
   - Topics: AV and robotaxi driving behaviour, car-following and capacity; AV safety and crash-rate comparisons, incident and disengagement data; ACC/ADAS field experiments; ride-hailing effects on congestion, VMT, transit and drivers; micromobility; navigation-app routing effects; new open trajectory datasets (Waymo Open, Argoverse, I-24 MOTION, highD and similar).
   - Prefer empirical and field-data studies. Include a simulation study only if it is calibrated on real AV or platform data.
   - Where to look:
     - Crossref (no key), e.g. `https://api.crossref.org/works?query.bibliographic=waymo+traffic+empirical&filter=from-online-pub-date:<YYYY-MM-DD>,type:journal-article&sort=published&order=desc&rows=20`. Use the last scan date (first run: 30 days back) and several term sets: autonomous vehicle traffic flow; robotaxi safety crash; automated vehicle car-following empirical; ride-hailing congestion; adaptive cruise control field experiment.
     - arXiv, e.g. `https://export.arxiv.org/api/query?search_query=all:%22autonomous%20vehicle%22+AND+all:traffic&sortBy=submittedDate&sortOrder=descending&max_results=30`.
     - Journals: Data Science for Transportation, Transportation Research Parts A/B/C/D/F, Transportation Science, IEEE T-ITS, Transportation Research Record, Accident Analysis & Prevention, Traffic Injury Prevention, Nature/Science family. Also waymo.com/research.
   - For each paper state: journal or "preprint, not peer-reviewed"; first author et al. (and a notable group or affiliation if known); the data used; the method; the headline quantitative finding; one limitation. Link the DOI (`https://doi.org/...`) or the publisher page. Confirm the abstract supports every number you write. Aim for two to five items.

**Standing sources: check these on every run**, even when search does not surface them. Look for posts dated since the last scan.
- **Google Research, Mobility AI** (measurement, digital-twin simulation and optimization of urban traffic; the program was introduced at https://research.google/blog/introducing-mobility-ai-advancing-urban-transportation/):
  - Blog: https://research.google/blog/ (look for traffic, routing, mobility, simulation, parking, EV-routing and geospatial posts).
  - Publications: https://research.google/pubs/ (search traffic, routing, travel demand, simulation calibration).
  - Project Green Light (traffic-signal optimization with city partners): https://sites.research.google/greenlight/
  - Google Maps Platform blog: https://mapsplatform.google.com/resources/blog/
  - Research area page: https://research.google/research-areas/sustainability-crisis-resilience/
- Waymo research and safety pages: https://waymo.com/research/ and https://waymo.com/safety/
- Uber and Lyft engineering blogs: https://www.uber.com/blog/engineering/ and https://eng.lyft.com/

Where these go: a product or deployment announcement (e.g. a new Green Light city, a Maps feature) goes in its topic section. A post that presents a method or a paper with results (e.g. calibrating digital twins, congestion functions, routing with tolls) goes in **Research Evidence**; link the paper if there is one and the blog otherwise.

Prefer primary sources: company blog, engineering blog, newsroom, regulator page, or filing. Use a reputable news outlet only when the company has not posted, and say so. Open each linked page and confirm it supports every specific claim (dates, numbers, cities, features). A search snippet is not enough. Skip press-release rewrites, stock-tip articles, and items older than about a month. Use a handful of targeted searches per section. Skip items already in the matching state array.

Write `automation/transport-news-digests/<YYYY-MM-DD>.md` with exactly these headings and one-line linked bullets:

```
# Transportation News — <YYYY-MM-DD>

## Autonomous Vehicles
- [Specific headline](https://source.example/item) — Source: company blog/regulator/outlet; published YYYY-MM-DD. What happened, the concrete numbers, and why it matters for the state of the technology.

## Maps & Navigation
- [Specific headline](https://source.example/item) — Source: ...; published YYYY-MM-DD. What changed and why it matters.

## Traffic Data & Open Data
- [Specific headline](https://source.example/item) — Source: ...; published YYYY-MM-DD. What the data or tool covers, who can access it, and possible research use.

## Ride-hailing & Shared Mobility
- [Specific headline](https://source.example/item) — Source: ...; published YYYY-MM-DD. What happened and why it matters.

## Policy & Safety
- [Specific headline](https://source.example/item) — Source: ...; published YYYY-MM-DD. What the rule, investigation, or data release says and who it affects.

## Research Evidence
- [Paper title](https://doi.org/10.xxxx/xxxxx) — Source: Journal name (peer-reviewed) or arXiv (preprint, not peer-reviewed); published YYYY-MM-DD; First Author et al. (group). Data: what and how much. Method: one phrase. Finding: headline result with numbers. Limitation: one phrase.
```

All URLs must be `https://` links to the original item. Keep each bullet to one line so the HTML builder can parse it. Do not place Markdown links inside a note after the first link. When a section has no new items, write `No new items today.` under it. Write the file even when all sections have no new items.

Update `automation/transport-news-state.json` by appending only the reported URLs to the matching arrays, with no duplicates. Do not edit the career or AI Watch digests, `raw/`, or `wiki/`. Do not send a notification; the shell runner sends one after building the dashboard.
