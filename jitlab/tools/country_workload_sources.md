# Country Workload Profiles (30-minute bins) — Sources

These profiles are approximate workload shapes per local time, informed by:

- Cloudflare Radar — Traffic by time of day (country pages)
  - https://radar.cloudflare.com/traffic
  - Example: Germany — https://radar.cloudflare.com/country/DE?tab=traffic
  - Blog explainer on HTTP request insights — https://blog.cloudflare.com/http-requests-on-cloudflare-radar
- American Time Use Survey (ATUS) — Time of day people work (US hourly share)
  - https://www.bls.gov/tus/charts/time-of-day.htm
- Eurostat / HETUS — Harmonised European Time Use Surveys (activity by time of day)
  - Portal: https://ec.europa.eu/eurostat/web/time-use-surveys
- Our World in Data — Time use (Working at a given time), harmonised cross-country series
  - https://ourworldindata.org/time-use
- Japan Statistics Bureau — Survey on Time Use and Leisure Activities (STULA)
  - https://www.stat.go.jp/english/data/shakai/index.html
- Korea Time Use Survey (KOSTAT)
  - https://kostat.go.kr/eng/

Methodology (summary):
- Time-use datasets provide the working-hours window shape by country/region (e.g., earlier end in Europe, longer evening in East Asia).
- Cloudflare Radar hourly traffic curves provide after-work consumer usage timing. Profiles are shaped to reflect higher evening activity in East Asia and sharper post-17:00 drop in parts of Europe.
- Values are normalized shape factors (not absolute), intended to be scaled by experiment intensity. Adjust per your calibration.
