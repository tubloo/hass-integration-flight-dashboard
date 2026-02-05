# Flight Dashboard (Home Assistant)

> This project was created with the assistance of OpenAI Codex.

Flight Dashboard is a Home Assistant integration that tracks upcoming flights and their status.

## Privacy & Data Handling

Flight Dashboard is **per‑user and BYO‑API‑keys**. It does **not** operate any shared
backend and does **not** transmit your travellers/notes to third parties. Flight
status and schedule lookups are performed directly from your Home Assistant
instance to the configured provider APIs using your own keys.

## Installation

### Manual (current)
**Option A — git clone (recommended)**
```
cd /config/custom_components
git clone https://github.com/tubloo/hass-integration-flight-dashboard flight_dashboard
```
Then restart Home Assistant.

**Option B — download ZIP**
1. Download the repo ZIP from GitHub.
2. Extract it.
3. Copy `custom_components/flight_dashboard` into `/config/custom_components/flight_dashboard`.
4. Restart Home Assistant.

Finally, add the integration in **Settings → Devices & Services**.

### HACS (future)
HACS support is not enabled yet. Once the repository is made HACS‑ready, these
instructions will be added.

## Setup Package (Helpers + Scripts)

The easiest way to create the required helpers/scripts is to include the
package file in your configuration and restart HA:

1) Ensure `packages:` is enabled in `configuration.yaml`:
```yaml
homeassistant:
  packages: !include_dir_named packages
```

2) Copy the package file from this repo to your HA config:
```
/config/packages/flight_dashboard_add_flow.yaml
```

3) Restart Home Assistant.

This will create:
- `input_text.fd_airline`
- `input_text.fd_flight_number`
- `input_text.fd_dep_airport` (optional, for disambiguation)
- `input_text.fd_travellers`
- `input_text.fd_notes`
- `input_datetime.fd_flight_date`
- `script.fd_preview_flight`
- `script.fd_confirm_add`
- `script.fd_clear_preview`

### Manual Helper + Script Creation (UI)

If you prefer the UI instead of packages:

**Helpers**
1. Settings → Devices & Services → Helpers → **Create Helper**
2. Create these:
   - **Text**: `input_text.fd_airline`
   - **Text**: `input_text.fd_flight_number`
   - **Text**: `input_text.fd_dep_airport` (optional)
   - **Text**: `input_text.fd_travellers`
   - **Text**: `input_text.fd_notes`
   - **Date & Time**: `input_datetime.fd_flight_date`

**Scripts**
1. Settings → Automations & Scenes → **Scripts** → Create Script
2. Create:
   - `script.fd_preview_flight`
   - `script.fd_confirm_add`
   - `script.fd_clear_preview`

You can copy the script YAML directly from
`/config/packages/flight_dashboard_add_flow.yaml` if you want exact parity.

## Required / Recommended Frontend Components

These Lovelace examples use the following custom cards:

**Required for the examples below**
- **Mushroom** cards (`custom:mushroom-*`)
- **auto-entities** (`custom:auto-entities`)
- **tailwindcss-template-card** (`custom:tailwindcss-template-card`)

If you don’t have these, install them via HACS → Frontend, then restart HA.

## Helpers & Scripts (Add Flight Flow)

The Add Flight card expects these helpers/scripts to exist. Use the provided
`/config/packages/flight_dashboard_add_flow.yaml` or create them in UI:

- `input_text.fd_airline`
- `input_text.fd_flight_number`
- `input_text.fd_travellers`
- `input_text.fd_notes`
- `input_datetime.fd_flight_date`
- `script.fd_preview_flight`
- `script.fd_confirm_add`
- `script.fd_clear_preview`

## Post‑Install Checklist

1) **Configure the integration**  
   Settings → Devices & Services → Add Integration → Flight Dashboard  
   Add API keys, choose providers, set cache/refresh options.

2) **Install required frontend cards** (via HACS → Frontend)  
   - Mushroom  
   - auto‑entities  
   - tailwindcss‑template‑card

3) **Create helpers + scripts**  
   Use the **Setup Package** above or create them in UI.

4) **Add Lovelace dashboards/cards**  
   Copy the Flight Status and Manage Flights dashboards from the examples below.

## Uninstall / Cleanup

Use this if you want to fully remove the integration and its data.

1) **Remove the integration**
   - Settings → Devices & Services → Flight Dashboard → Remove

2) **Remove the custom component files**
   - Delete `/config/custom_components/flight_dashboard/`

3) **Remove helpers & scripts (if you used the package)**
   - Delete `/config/packages/flight_dashboard_add_flow.yaml`
   - Restart Home Assistant
   - Or delete the helpers/scripts manually in UI (Helpers / Scripts)

4) **Remove stored data (manual flights, preview, directory cache)**
   - Delete the following files from `/config/.storage/`:
     - `flight_dashboard.manual_flights`
     - `flight_dashboard.preview`
     - `flight_dashboard.directory_cache`
   - Restart Home Assistant

5) **Remove Lovelace resources / custom cards (optional)**
   - If you installed custom cards only for this integration, uninstall via HACS → Frontend:
     - Mushroom
     - auto‑entities
     - tailwindcss-template-card
     - button-card (if used)
   - Also remove any Lovelace resources if you added them manually.

6) **Remove dashboards/cards**
   - Delete any dashboards/cards you added for Flight Dashboard.

## Status Refresh Policy

By default, **no status polling is performed until the flight is within 6 hours
of scheduled departure**. After that, refresh intervals tighten as departure
approaches and while in‑flight, and stop several hours after arrival.
You can add flights with minimal inputs (airline code, flight number, date) and let the integration enrich the details using provider APIs.

## Features
- Add flights with minimal inputs.
- Preview and confirm before saving.
- Automatic status refresh with smart API call rationing.
- Manual flights are editable; provider-sourced flights are read-only.
- On-demand refresh button/service.
- Schedule provider and status provider can be set independently.
- Optional auto-removal of arrived/cancelled manual flights.
- Optional airport/airline directory cache (default 180 days).

## Configuration
All configuration is done via the UI (config flow).

Key points:
- **Schedule provider** is used for preview/add (must return scheduled times).
- **Status provider** is used for live status updates.
- **Position provider** controls live map location updates (default: same as status).
- FR24 is great for status, but does not always return scheduled times. Use AirLabs or Aviationstack for schedule.
- FR24 sandbox: enable **Use FR24 sandbox** and set the sandbox key.
- **Auto-remove past flights** removes flights whose arrival time is older than the cutoff.
- **Delay grace (minutes)** controls when a flight is considered delayed (default 10 min).
- **Preview displays scheduled times only** (est/act appear after the flight is added).

### Required inputs when adding a flight
```
airline, flight_number, date
```
Optional:
```
dep_airport
```

### Delay Status Logic
Computed field: `delay_status` (on_time | delayed | cancelled | unknown)  
Computed field: `delay_status_key` (normalized snake_case, e.g. on_time, delayed)  
Computed field: `delay_minutes` (minutes vs sched; arrival preferred if available)
Computed fields: `duration_scheduled_minutes`, `duration_estimated_minutes`, `duration_actual_minutes`  
Computed field: `duration_minutes` (best available: actual → estimated → scheduled)

### Provider Status Mapping
Raw provider status is preserved as:
- `status.provider_state` (inside `status`)

Normalized status is:
- `status_state` (used by UI & logic)

Normalization rules:
- FlightAPI: `Scheduled` → `Scheduled`, `In Air` / `Departed` → `En Route`, `Landed` → `Arrived`, `Cancelled` → `Cancelled`
- FR24: `scheduled` / `active` / `landed` / `canceled` mapped to `Scheduled` / `En Route` / `Arrived` / `Cancelled`
- Aviationstack / AirLabs: provider state mapped to `status_state` (unknown if missing)

### Provider Time Normalization
Providers are inconsistent about timezone handling:
- Some return **UTC with offsets** (authoritative).
- Some return **local airport time without TZ** (naive strings).
- Some return **local time with an offset**.

The integration normalizes all provider times to UTC:
- If a timestamp includes an offset, it is treated as authoritative and converted to UTC.
- If a timestamp is **naive**, it is interpreted in the **airport’s TZ** (from directory/cache/OpenFlights).
  This is why airport tz lookup is important; without it, `*_local` fields can’t be computed.

### Canonical Fields (What They Mean)
Top‑level:
- `status_state`: normalized state (Scheduled | En Route | Arrived | Cancelled | Diverted | Unknown)
- `delay_status`: computed on_time | delayed | cancelled | unknown
- `delay_minutes`: minutes late/early vs schedule (arrival preferred)
- `duration_*_minutes`: computed durations from dep/arr timestamps

Per‑leg:
- `dep.scheduled/estimated/actual`: UTC ISO timestamps for departure
- `arr.scheduled/estimated/actual`: UTC ISO timestamps for arrival
- `dep.scheduled_local/estimated_local/actual_local`: airport‑local timestamps
- `arr.scheduled_local/estimated_local/actual_local`: airport‑local timestamps
- `dep.airport/arr.airport`: name, city, iata, tz, tz_short

Provider block:
- `status.provider`: provider name
- `status.provider_state`: raw status from provider
> `status` is a normalized subset of provider fields, not the full raw response.

Logic:
- If status_state == cancelled → `cancelled`
- If status_state == arrived → compute delay from actual vs scheduled (arrival preferred)
- If arrival estimated/actual is available:
  - arrival_delay = arrival_est_or_act − arrival_scheduled
  - delayed if arrival_delay > grace
  - otherwise on_time
- Else if departure estimated/actual is available:
  - departure_delay = dep_est_or_act − dep_scheduled
  - delayed if departure_delay > grace
  - otherwise on_time
- If no sched/est/act → `unknown`

### Merge Tolerance
When the integration sees multiple records that look like the same flight, it
uses **Merge tolerance (hours)** to decide whether to combine them. If two
records share airline + flight number + route and their scheduled times are
within the tolerance window, they are merged to avoid duplicates. Default: **6 hours**.

### Supported providers
**Schedule provider**
- Auto (best available)
- Aviationstack
- AirLabs
- FlightAPI.io
- Flightradar24
- Mock

**Status provider**
- Flightradar24 (default)
- Aviationstack
- AirLabs
- FlightAPI.io
- OpenSky (tracking-only)
- Local (no API calls)
- Mock

## Directory Cache
- Enable **Cache airports/airlines** to store directory lookups in `.storage`.
- **Directory cache TTL (days)** controls refresh age (default 90).
- Cache is only used when a field is missing (name, city, tz, airline name/logo).
- If the cache and provider miss, the integration falls back to OpenFlights datasets
  (airlines.dat / airports.dat) on-demand and stores results in the cache.

## Lovelace Examples

Below are **full dashboard YAMLs** and **individual card snippets**.

### Flight Status Dashboard (full)
```yaml
title: Flight Status
views:
  - title: Flights
    path: flights
    cards:
      - type: custom:auto-entities
        card:
          type: entities
          title: Flights
          show_header_toggle: false
        filter:
          template: >
            {% set flights = state_attr('sensor.flight_dashboard_upcoming_flights','flights') or [] %} [
            {%- for f in flights -%}

              {

                "{%- set dep_date = f.dep.scheduled and (as_timestamp(f.dep.scheduled) | timestamp_custom('%d %b', true)) or '—' -%}"

                "{%- set dep_sched_local_dt = f.dep.scheduled_local and as_datetime(f.dep.scheduled_local) -%}"
                "{%- set dep_est_local_dt = f.dep.estimated_local and as_datetime(f.dep.estimated_local) -%}"
                "{%- set dep_act_local_dt = f.dep.actual_local and as_datetime(f.dep.actual_local) -%}"

                "{%- set arr_sched_local_dt = f.arr.scheduled_local and as_datetime(f.arr.scheduled_local) -%}"
                "{%- set arr_est_local_dt = f.arr.estimated_local and as_datetime(f.arr.estimated_local) -%}"
                "{%- set arr_act_local_dt = f.arr.actual_local and as_datetime(f.arr.actual_local) -%}"

                "{%- set dep_sched_local = dep_sched_local_dt and (dep_sched_local_dt.strftime('%H:%M')) -%}"
                "{%- set dep_est_local = dep_est_local_dt and (dep_est_local_dt.strftime('%H:%M')) -%}"
                "{%- set dep_act_local = dep_act_local_dt and (dep_act_local_dt.strftime('%H:%M')) -%}"

                "{%- set arr_sched_local = arr_sched_local_dt and (arr_sched_local_dt.strftime('%H:%M')) -%}"
                "{%- set arr_est_local = arr_est_local_dt and (arr_est_local_dt.strftime('%H:%M')) -%}"
                "{%- set arr_act_local = arr_act_local_dt and (arr_act_local_dt.strftime('%H:%M')) -%}"

                "{%- set dep_sched_viewer_dt = f.dep.scheduled and (as_datetime(f.dep.scheduled) | as_local) -%}"
                "{%- set dep_est_viewer_dt = f.dep.estimated and (as_datetime(f.dep.estimated) | as_local) -%}"
                "{%- set dep_act_viewer_dt = f.dep.actual and (as_datetime(f.dep.actual) | as_local) -%}"

                "{%- set arr_sched_viewer_dt = f.arr.scheduled and (as_datetime(f.arr.scheduled) | as_local) -%}"
                "{%- set arr_est_viewer_dt = f.arr.estimated and (as_datetime(f.arr.estimated) | as_local) -%}"
                "{%- set arr_act_viewer_dt = f.arr.actual and (as_datetime(f.arr.actual) | as_local) -%}"

                "{%- set dep_sched_viewer = dep_sched_viewer_dt and (dep_sched_viewer_dt.strftime('%H:%M')) -%}"
                "{%- set dep_est_viewer = dep_est_viewer_dt and (dep_est_viewer_dt.strftime('%H:%M')) -%}"
                "{%- set dep_act_viewer = dep_act_viewer_dt and (dep_act_viewer_dt.strftime('%H:%M')) -%}"

                "{%- set arr_sched_viewer = arr_sched_viewer_dt and (arr_sched_viewer_dt.strftime('%H:%M')) -%}"
                "{%- set arr_est_viewer = arr_est_viewer_dt and (arr_est_viewer_dt.strftime('%H:%M')) -%}"
                "{%- set arr_act_viewer = arr_act_viewer_dt and (arr_act_viewer_dt.strftime('%H:%M')) -%}"

                "{%- set dep_sched_local_date = dep_sched_local_dt and dep_sched_local_dt.strftime('%d %b') -%}"
                "{%- set dep_est_local_date = dep_est_local_dt and dep_est_local_dt.strftime('%d %b') -%}"
                "{%- set dep_act_local_date = dep_act_local_dt and dep_act_local_dt.strftime('%d %b') -%}"

                "{%- set arr_sched_local_date = arr_sched_local_dt and arr_sched_local_dt.strftime('%d %b') -%}"
                "{%- set arr_est_local_date = arr_est_local_dt and arr_est_local_dt.strftime('%d %b') -%}"
                "{%- set arr_act_local_date = arr_act_local_dt and arr_act_local_dt.strftime('%d %b') -%}"

                "{%- set dep_sched_viewer_date = dep_sched_viewer_dt and dep_sched_viewer_dt.strftime('%d %b') -%}"
                "{%- set dep_est_viewer_date = dep_est_viewer_dt and dep_est_viewer_dt.strftime('%d %b') -%}"
                "{%- set dep_act_viewer_date = dep_act_viewer_dt and dep_act_viewer_dt.strftime('%d %b') -%}"

                "{%- set arr_sched_viewer_date = arr_sched_viewer_dt and arr_sched_viewer_dt.strftime('%d %b') -%}"
                "{%- set arr_est_viewer_date = arr_est_viewer_dt and arr_est_viewer_dt.strftime('%d %b') -%}"
                "{%- set arr_act_viewer_date = arr_act_viewer_dt and arr_act_viewer_dt.strftime('%d %b') -%}"

                "{%- set dep_base_local_dt = dep_act_local_dt or dep_est_local_dt or dep_sched_local_dt -%}"
                "{%- set dep_base_local_date = dep_base_local_dt and dep_base_local_dt.strftime('%d %b') -%}"

                "{%- set dep_tz_short = f.dep.airport.tz_short -%}"
                "{%- set arr_tz_short = f.arr.airport.tz_short -%}"
                "{%- set viewer_tz_short = now().strftime('%Z') -%}"

                "{%- set dep_label = f.dep.airport.iata -%}"
                "{%- set arr_label = f.arr.airport.iata -%}"

                "type": "custom:mushroom-template-card",
                "entity": "sensor.flight_dashboard_upcoming_flights",
                "picture": "{{ f.airline_logo_url }}",
                "primary": "{{ f.airline_code }} {{ f.flight_number }} · {{ dep_label }} → {{ arr_label }} · {{ dep_date }} · {{ (f.get('delay_status') or "unknown") | title }} · ({{ (f.status_state or "unknown") | title }})",
                "state": "{{ (f.status_state or 'unknown') | title }}",
                "secondary":

                  "Dep: "
                  "{%- if dep_sched_local -%} S: {{ dep_sched_local }} {{ dep_tz_short }} {%- endif -%}"
                  "{%- if dep_tz_short and dep_tz_short != viewer_tz_short and dep_sched_viewer -%}"
                    " · {{ dep_sched_viewer }} {{ viewer_tz_short }}{% if dep_sched_viewer_date and dep_sched_local_date and dep_sched_viewer_date != dep_sched_local_date %} ({{ dep_sched_viewer_date }}){% endif %}"
                  "{%- endif -%}"
                  "{%- if dep_est_local -%}, E: {{ dep_est_local }} {{ dep_tz_short }} {%- endif -%}"
                  "{%- if dep_tz_short and dep_tz_short != viewer_tz_short and dep_est_viewer -%}"
                    " · {{ dep_est_viewer }} {{ viewer_tz_short }}{% if dep_est_viewer_date and dep_est_local_date and dep_est_viewer_date != dep_est_local_date %} ({{ dep_est_viewer_date }}){% endif %}"
                  "{%- endif -%}"
                  "{%- if dep_act_local -%}, A: {{ dep_act_local }} {{ dep_tz_short }} {%- endif -%}"
                  "{%- if dep_tz_short and dep_tz_short != viewer_tz_short and dep_act_viewer -%}"
                    " · {{ dep_act_viewer }} {{ viewer_tz_short }}{% if dep_act_viewer_date and dep_act_local_date and dep_act_viewer_date != dep_act_local_date %} ({{ dep_act_viewer_date }}){% endif %}"
                  "{%- endif -%}"

                  "\nArr: "
                  "{%- if arr_sched_local -%} S: {{ arr_sched_local }} {{ arr_tz_short }}{% if arr_sched_local_date and dep_base_local_date and arr_sched_local_date != dep_base_local_date %} ({{ arr_sched_local_date }}){% endif %}{%- endif -%}"
                  "{%- if arr_tz_short and arr_tz_short != viewer_tz_short and arr_sched_viewer -%}"
                    " · {{ arr_sched_viewer }} {{ viewer_tz_short }}{% if arr_sched_viewer_date and arr_sched_local_date and arr_sched_viewer_date != arr_sched_local_date %} ({{ arr_sched_viewer_date }}){% endif %}"
                  "{%- endif -%}"
                  "{%- if arr_est_local -%}, E: {{ arr_est_local }} {{ arr_tz_short }}{% if arr_est_local_date and dep_base_local_date and arr_est_local_date != dep_base_local_date %} ({{ arr_est_local_date }}){% endif %}{%- endif -%}"
                  "{%- if arr_tz_short and arr_tz_short != viewer_tz_short and arr_est_viewer -%}"
                    " · {{ arr_est_viewer }} {{ viewer_tz_short }}{% if arr_est_viewer_date and arr_est_local_date and arr_est_viewer_date != arr_est_local_date %} ({{ arr_est_viewer_date }}){% endif %}"
                  "{%- endif -%}"
                  "{%- if arr_act_local -%}, A: {{ arr_act_local }} {{ arr_tz_short }}{% if arr_act_local_date and dep_base_local_date and arr_act_local_date != dep_base_local_date %} ({{ arr_act_local_date }}){% endif %}{%- endif -%}"
                  "{%- if arr_tz_short and arr_tz_short != viewer_tz_short and arr_act_viewer -%}"
                    " · {{ arr_act_viewer }} {{ viewer_tz_short }}{% if arr_act_viewer_date and arr_act_local_date and arr_act_viewer_date != arr_act_local_date %} ({{ arr_act_viewer_date }}){% endif %}"
                  "{%- endif -%}"

                  "{%- if f.aircraft_type -%}"
                  "\nAircraft: {{ f.aircraft_type }}"
                  "{%- endif -%}"

                  "{%- if f.travellers -%}"
                  "\nPax: {{ f.travellers | join(', ') }}"
                  "{%- endif -%}" ,

                "multiline_secondary": "true",
                "tap_action": {
                  "action": "call-service",
                  "service": "select.select_option",
                  "target": { "entity_id": "select.flight_dashboard_selected_flight" },
                  "data": { "option": "{{ f.flight_key }}" }
                }
              }{{ "," if not loop.last else "" }}
            {%- endfor -%} ]

### Manage Flights Dashboard (full)
```yaml
title: Manage Flights
views:
  - title: Manage
    path: manage
    cards:
      - type: vertical-stack
        cards:
          - type: custom:mushroom-title-card
            title: Add a flight
            subtitle: Enter airline + number, preview, then confirm
          - type: entities
            show_header_toggle: false
            entities:
              - entity: input_text.fd_airline
                name: Airline code (e.g. EK)
              - entity: input_text.fd_flight_number
                name: Flight number (e.g. 236)
              - entity: input_datetime.fd_flight_date
                name: Date
              - entity: input_text.fd_dep_airport
                name: Departure airport (optional, e.g. AMD)
              - entity: input_text.fd_travellers
                name: Travellers (optional)
              - entity: input_text.fd_notes
                name: Notes (optional)
          - type: custom:mushroom-template-card
            picture: >
              {% set p = state_attr('sensor.flight_dashboard_add_preview','preview') or {} %}
              {% set f = p.get('flight') or {} %}
              {% if f.get('airline_logo_url') %}
                {{ f.get('airline_logo_url') }}
              {% else %}
                https://pics.avs.io/64/64/{{ (f.get('airline_code') or '') | upper }}.png
              {% endif %}
            primary: >
              {% set p = state_attr('sensor.flight_dashboard_add_preview','preview') or {} %}
              {% set f = p.get('flight') or {} %}
              {% set dep = f.get('dep') or {} %}
              {% set arr = f.get('arr') or {} %}
              {% set dep_air = dep.get('airport') or {} %}
              {% set arr_air = arr.get('airport') or {} %}
              {% set dep_t = dep.get('scheduled_local') or dep.get('scheduled') %}
              {% set arr_t = arr.get('scheduled_local') or arr.get('scheduled') %}
              {% set dep_hm = dep_t and dep_t[11:16] %}
              {% set arr_hm = arr_t and arr_t[11:16] %}
              {% set dep_date = dep_t and dep_t[0:10] %}
              {% set arr_date = arr_t and arr_t[0:10] %}
              {% set dep_date_fmt = dep_date and (as_datetime(dep_date) | timestamp_custom('%d %b', false)) %}
              {% set arr_date_fmt = arr_date and (as_datetime(arr_date) | timestamp_custom('%d %b', false)) %}
              {{ f.get('airline_code','—') }} {{ f.get('flight_number','—') }} ·
              {{ dep_air.get('iata') or '—' }} ({{ dep_hm or '—' }} {{ dep_air.get('tz_short') or '' }})
              → {{ arr_air.get('iata') or '—' }} ({{ arr_hm or '—' }} {{ arr_air.get('tz_short') or '' }}{% if arr_date_fmt and dep_date_fmt and arr_date_fmt != dep_date_fmt %} · {{ arr_date_fmt }}{% endif %})
            secondary: >
              {% set p = state_attr('sensor.flight_dashboard_add_preview','preview') or {} %}
              {% set f = p.get('flight') or {} %}
              {% set airline_name = f.get('airline_name') or f.get('airline_code') or '—' %}
              {% if p.get('hint') %}
                ❗ {{ p.get('hint') }}
              {% elif p.get('warning') %}
                ⚠️ {{ p.get('warning') }}
              {% elif p.get('error') %}
                ❌ {{ p.get('error') }}
              {% else %}
                Run Preview
              {% endif %} · Airline: {{ airline_name }} · Ready: {{ p.get('ready') }}
            icon: mdi:airplane
            layout: horizontal
            multiline_secondary: true
          - type: horizontal-stack
            cards:
              - type: custom:mushroom-entity-card
                entity: script.fd_preview_flight
                name: Preview
                icon: mdi:magnify
                tap_action:
                  action: call-service
                  service: script.turn_on
                  target:
                    entity_id: script.fd_preview_flight
              - type: custom:mushroom-entity-card
                entity: script.fd_confirm_add
                name: Add
                icon: mdi:content-save
                tap_action:
                  action: call-service
                  service: script.turn_on
                  target:
                    entity_id: script.fd_confirm_add
              - type: custom:mushroom-entity-card
                entity: script.fd_clear_preview
                name: Clear
                icon: mdi:close-circle
                tap_action:
                  action: call-service
                  service: script.turn_on
                  target:
                    entity_id: script.fd_clear_preview

      - type: entities
        title: Remove a flight
        show_header_toggle: false
        entities:
          - entity: select.flight_dashboard_remove_flight
            name: Select flight to remove
          - entity: button.flight_dashboard_remove_selected_flight
            name: Remove selected flight

      - type: vertical-stack
        cards:
          - type: entities
            title: Flight Dashboard Diagnostics
            show_header_toggle: false
            entities:
              - entity: sensor.flight_dashboard_fr24_usage
                name: FR24 usage (credits in last period)
              - entity: sensor.flight_dashboard_upcoming_flights
                name: Upcoming flights (summary)
              - entity: sensor.flight_dashboard_provider_blocks
                name: Provider blocks
              - entity: button.flight_dashboard_refresh_now
                name: Refresh now
              - entity: button.flight_dashboard_remove_landed_flights
                name: Remove arrived flights
          - type: markdown
            title: Provider Blocks Detail
            content: >
              {% set p = state_attr('sensor.flight_dashboard_provider_blocks','providers') or {} %}
              {% if p %}
              {% for name, info in p.items() %}
              {% set until_dt = info.until and as_datetime(info.until) %}
              - **{{ name }}** blocked until
                {{ until_dt and (as_timestamp(until_dt) | timestamp_custom('%d %b %H:%M', true)) or info.until }}
                ({{ info.seconds_remaining }}s) · {{ info.reason }}
              {% endfor %}
              {% else %}
              No providers blocked ✅
              {% endif %}

### Individual Cards

#### Add Flight (preview + confirm)
Use this **Add Flight** card with the Tailwind preview panel:

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-title-card
    title: Add a flight
    subtitle: Enter airline + number, preview, then confirm
  - type: entities
    show_header_toggle: false
    entities:
      - entity: input_text.fd_airline
        name: Airline code (e.g. EK)
      - entity: input_text.fd_flight_number
        name: Flight number (e.g. 236)
      - entity: input_datetime.fd_flight_date
        name: Date
      - entity: input_text.fd_dep_airport
        name: Departure airport (optional, e.g. AMD)
      - entity: input_text.fd_travellers
        name: Travellers (optional)
      - entity: input_text.fd_notes
        name: Notes (optional)

  - type: custom:tailwindcss-template-card
    content: >
      {% set p = state_attr('sensor.flight_dashboard_add_preview','preview') or {} %}
      {% set f = p.get('flight') %}
      {% if not f %}
      <div class='rounded-2xl bg-[rgba(255,255,255,0.04)] p-4'>
        <div class='text-sm opacity-80'>Enter airline + number, then tap Preview.</div>
      </div>
      {% else %}

      {% set dep = f.get('dep') or {} %}
      {% set arr = f.get('arr') or {} %}
      {% set dep_air = dep.get('airport') or {} %}
      {% set arr_air = arr.get('airport') or {} %}

      {% set dep_code = (dep_air.get('iata') or '—') | upper %}
      {% set arr_code = (arr_air.get('iata') or '—') | upper %}

      {% set dep_label_raw = dep_air.get('city') or dep_air.get('name') or dep_code %}
      {% set arr_label_raw = arr_air.get('city') or arr_air.get('name') or arr_code %}

      {% set dep_label = dep_label_raw | title %}
      {% set arr_label = arr_label_raw | title %}

      {% set dep_sched_dt = dep.get('scheduled_local') and as_datetime(dep.get('scheduled_local')) %}
      {% set dep_est_dt = dep.get('estimated_local') and as_datetime(dep.get('estimated_local')) %}
      {% set dep_act_dt = dep.get('actual_local') and as_datetime(dep.get('actual_local')) %}

      {% set arr_sched_dt = arr.get('scheduled_local') and as_datetime(arr.get('scheduled_local')) %}
      {% set arr_est_dt = arr.get('estimated_local') and as_datetime(arr.get('estimated_local')) %}
      {% set arr_act_dt = arr.get('actual_local') and as_datetime(arr.get('actual_local')) %}

      {% set dep_sched = dep_sched_dt and dep_sched_dt.strftime('%H:%M') %}
      {% set dep_est = dep_est_dt and dep_est_dt.strftime('%H:%M') %}
      {% set dep_act = dep_act_dt and dep_act_dt.strftime('%H:%M') %}

      {% set arr_sched = arr_sched_dt and arr_sched_dt.strftime('%H:%M') %}
      {% set arr_est = arr_est_dt and arr_est_dt.strftime('%H:%M') %}
      {% set arr_act = arr_act_dt and arr_act_dt.strftime('%H:%M') %}

      {% set dep_tz = dep_air.get('tz_short') or '' %}
      {% set arr_tz = arr_air.get('tz_short') or '' %}
      {% set viewer_tz = now().strftime('%Z') %}

      {% set dep_viewer_dt = dep.get('scheduled') and (as_datetime(dep.get('scheduled')) | as_local) %}
      {% set arr_viewer_dt = arr.get('scheduled') and (as_datetime(arr.get('scheduled')) | as_local) %}
      {% set dep_viewer = dep_viewer_dt and dep_viewer_dt.strftime('%H:%M') %}
      {% set arr_viewer = arr_viewer_dt and arr_viewer_dt.strftime('%H:%M') %}

      {% set dep_est_or_act = dep_act or dep_est %}
      {% set arr_est_or_act = arr_act or arr_est %}

      {% set dep_changed = dep_est_or_act and dep_sched and dep_est_or_act != dep_sched %}
      {% set arr_changed = arr_est_or_act and arr_sched and arr_est_or_act != arr_sched %}

      {% set dep_date = dep_sched_dt and dep_sched_dt.strftime('%d %b') or '—' %}

      {% set airline_logo = f.get('airline_logo_url') or ("https://pics.avs.io/64/64/" ~ (f.get('airline_code','') | upper) ~ ".png") %}

      <div class='rounded-2xl bg-[rgba(255,255,255,0.04)] p-4 space-y-2'>
        <div class='flex items-center gap-3'>
          <img src='{{ airline_logo }}' class='h-6 w-6 object-contain rounded' />
          <div class='flex-1'>
            <div class='text-lg font-semibold'>
              {{ f.get('airline_code','—') }} {{ f.get('flight_number','—') }} · {{ dep_code }} → {{ arr_code }} · {{ dep_date }}
            </div>
            <div class='text-sm opacity-80'>
              {{ f.get('airline_name') or '' }}{% if f.get('aircraft_type') %} · {{ f.get('aircraft_type') }}{% endif %}
            </div>
          </div>
        </div>

        <div class='grid grid-cols-2 gap-3 text-sm'>
          <div>
            <div class='font-semibold'>{{ dep_label }} ({{ dep_code }})</div>
            <div>
              {% if dep_changed %}
                <span class='line-through opacity-60'>{{ dep_sched }}</span>
                <span class='font-semibold'>{{ dep_est_or_act }}</span>
              {% else %}
                <span>{{ dep_est_or_act or dep_sched or '—' }}</span>
              {% endif %} {{ dep_tz }}
            </div>
            {% if dep_tz and dep_tz != viewer_tz and dep_viewer %}
              <div class='opacity-70'>{{ dep_viewer }} {{ viewer_tz }}</div>
            {% endif %}
          </div>
          <div>
            <div class='font-semibold'>{{ arr_label }} ({{ arr_code }})</div>
            <div>
              {% if arr_changed %}
                <span class='line-through opacity-60'>{{ arr_sched }}</span>
                <span class='font-semibold'>{{ arr_est_or_act }}</span>
              {% else %}
                <span>{{ arr_est_or_act or arr_sched or '—' }}</span>
              {% endif %} {{ arr_tz }}
            </div>
            {% if arr_tz and arr_tz != viewer_tz and arr_viewer %}
              <div class='opacity-70'>{{ arr_viewer }} {{ viewer_tz }}</div>
            {% endif %}
          </div>
        </div>

        <div class='text-sm opacity-80'>
          {% if p.get('hint') %}
            ❗ {{ p.get('hint') }}
          {% elif p.get('warning') %}
            ⚠️ {{ p.get('warning') }}
          {% elif p.get('error') %}
            ❌ {{ p.get('error') }}
          {% endif %} Ready to Add Flight: {{ p.get('ready') }}
        </div>
      </div>
      {% endif %}

  - type: horizontal-stack
    cards:
      - type: custom:mushroom-entity-card
        entity: script.fd_preview_flight
        name: Preview Flight
        icon: mdi:magnify
        tap_action:
          action: call-service
          service: script.turn_on
          target:
            entity_id: script.fd_preview_flight
      - type: custom:mushroom-entity-card
        entity: script.fd_confirm_add
        name: Add Flight
        icon: mdi:content-save
        tap_action:
          action: call-service
          service: script.turn_on
          target:
            entity_id: script.fd_confirm_add
      - type: custom:mushroom-entity-card
        entity: script.fd_clear_preview
        name: Clear
        icon: mdi:close-circle
        tap_action:
          action: call-service
          service: script.turn_on
          target:
            entity_id: script.fd_clear_preview
```

#### Flight Status List
Use this **Tailwind Flight List** card (sorted by departure time). Requires
`custom:tailwindcss-template-card` and `custom:auto-entities`.

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-title-card
    title: Flight List
  - type: custom:auto-entities
    card:
      type: vertical-stack
    card_param: cards
    filter:
      template: >
        {% set flights = state_attr('sensor.flight_dashboard_upcoming_flights','flights') or [] %}
        {% set flights = flights | sort(attribute='dep.scheduled') %}
        [
        {%- for f in flights -%}

          {%- set dep = f.dep or {} -%}
          {%- set arr = f.arr or {} -%}
          {%- set dep_air = dep.airport or {} -%}
          {%- set arr_air = arr.airport or {} -%}

          {%- set dep_code = (dep_air.iata or '—') | upper -%}
          {%- set arr_code = (arr_air.iata or '—') | upper -%}

          {%- set dep_label_raw = dep_air.city or dep_air.name or dep_code -%}
          {%- set arr_label_raw = arr_air.city or arr_air.name or arr_code -%}

          {%- set dep_label = dep_label_raw | title -%}
          {%- set arr_label = arr_label_raw | title -%}

          {%- set dep_sched_dt = dep.scheduled_local and as_datetime(dep.scheduled_local) -%}
          {%- set dep_est_dt = dep.estimated_local and as_datetime(dep.estimated_local) -%}
          {%- set dep_act_dt = dep.actual_local and as_datetime(dep.actual_local) -%}

          {%- set arr_sched_dt = arr.scheduled_local and as_datetime(arr.scheduled_local) -%}
          {%- set arr_est_dt = arr.estimated_local and as_datetime(arr.estimated_local) -%}
          {%- set arr_act_dt = arr.actual_local and as_datetime(arr.actual_local) -%}

          {%- set dep_sched = dep_sched_dt and dep_sched_dt.strftime('%H:%M') -%}
          {%- set dep_est = dep_est_dt and dep_est_dt.strftime('%H:%M') -%}
          {%- set dep_act = dep_act_dt and dep_act_dt.strftime('%H:%M') -%}

          {%- set arr_sched = arr_sched_dt and arr_sched_dt.strftime('%H:%M') -%}
          {%- set arr_est = arr_est_dt and arr_est_dt.strftime('%H:%M') -%}
          {%- set arr_act = arr_act_dt and arr_act_dt.strftime('%H:%M') -%}

          {%- set dep_tz = dep_air.tz_short or '' -%}
          {%- set arr_tz = arr_air.tz_short or '' -%}
          {%- set viewer_tz = now().strftime('%Z') -%}

          {%- set dep_viewer_dt = dep.scheduled and (as_datetime(dep.scheduled) | as_local) -%}
          {%- set arr_viewer_dt = arr.scheduled and (as_datetime(arr.scheduled) | as_local) -%}
          {%- set dep_viewer = dep_viewer_dt and dep_viewer_dt.strftime('%H:%M') -%}
          {%- set arr_viewer = arr_viewer_dt and arr_viewer_dt.strftime('%H:%M') -%}

          {%- set dep_est_or_act = dep_act or dep_est -%}
          {%- set arr_est_or_act = arr_act or arr_est -%}

          {%- set dep_changed = dep_est_or_act and dep_sched and dep_est_or_act != dep_sched -%}
          {%- set arr_changed = arr_est_or_act and arr_sched and arr_est_or_act != arr_sched -%}

          {%- set delay = (f.get('delay_status') or 'Unknown') -%}
          {%- set time_color = 'text-emerald-300' if delay == 'On Time' else ('text-red-300' if delay == 'Delayed' else 'text-gray-300') -%}

          {%- set raw_state = (f.get('status_state') or 'Unknown') -%}
          {%- set raw_state_lc = raw_state | lower -%}
          {%- set dep_state_dt = dep.scheduled and as_datetime(dep.scheduled) -%}
          {%- set is_future = dep_state_dt and dep_state_dt > now() -%}
          {%- set state = 'Scheduled' if (raw_state_lc == 'unknown' and is_future) else (raw_state | title) -%}

          {%- set badge = 'bg-gray-600 text-white' -%}
          {%- if state == 'Scheduled' -%}
            {%- set badge = 'bg-yellow-600 text-black' -%}
          {%- elif state == 'Active' -%}
            {%- set badge = 'bg-blue-600 text-white' -%}
          {%- elif state == 'Arrived' -%}
            {%- set badge = 'bg-emerald-700 text-white' -%}
          {%- elif state == 'Cancelled' -%}
            {%- set badge = 'bg-red-700 text-white' -%}
          {%- elif state == 'Diverted' -%}
            {%- set badge = 'bg-orange-600 text-white' -%}
          {%- endif -%}

          {%- set dep_date = dep_sched_dt and dep_sched_dt.strftime('%d %b') or '—' -%}
          {%- set pax = (f.travellers | join(', ')) if f.travellers else '' -%}

          {
            "type": "custom:tailwindcss-template-card",
            "content": "<div class='rounded-2xl bg-[rgba(255,255,255,0.04)] p-4 space-y-2'><div class='flex items-center gap-3'><img src='{{ f.airline_logo_url }}' class='h-6 w-6 object-contain rounded' /><div class='flex-1'><div class='text-lg font-semibold'>{{ f.airline_code }} {{ f.flight_number }} · {{ dep_code }} → {{ arr_code }} · {{ dep_date }}</div><div class='text-sm opacity-80'>{{ f.airline_name or '' }}{% if f.aircraft_type %} · {{ f.aircraft_type }}{% endif %}</div></div><span class='text-xs px-2 py-1 rounded-full {{ badge }}'>{{ state }}</span></div><div class='grid grid-cols-2 gap-3 text-sm'><div><div class='font-semibold'>{{ dep_label }} ({{ dep_code }})</div><div>{% if dep_changed %}<span class='line-through opacity-60'>{{ dep_sched }}</span> <span class='{{ time_color }} font-semibold'>{{ dep_est_or_act }}</span>{% else %}<span>{{ dep_est_or_act or dep_sched or '—' }}</span>{% endif %} {{ dep_tz }}</div>{% if dep_tz and dep_tz != viewer_tz and dep_viewer %}<div class='opacity-70'>{{ dep_viewer }} {{ viewer_tz }}</div>{% endif %}<div class='opacity-70'>T {{ dep.terminal or '—' }} / G {{ dep.gate or '—' }}</div></div><div><div class='font-semibold'>{{ arr_label }} ({{ arr_code }})</div><div>{% if arr_changed %}<span class='line-through opacity-60'>{{ arr_sched }}</span> <span class='{{ time_color }} font-semibold'>{{ arr_est_or_act }}</span>{% else %}<span>{{ arr_est_or_act or arr_sched or '—' }}</span>{% endif %} {{ arr_tz }}</div>{% if arr_tz and arr_tz != viewer_tz and arr_viewer %}<div class='opacity-70'>{{ arr_viewer }} {{ viewer_tz }}</div>{% endif %}<div class='opacity-70'>T {{ arr.terminal or '—' }} / G {{ arr.gate or '—' }}</div></div></div>{% if pax %}<div class='text-sm opacity-80'>Pax: {{ pax }}</div>{% endif %}</div>"
          }{{ "," if not loop.last else "" }}

        {%- endfor -%}
        ]
```

#### Diagnostics
Use the **Diagnostics** stack from the Manage Flights dashboard above.
## Services
### `flight_dashboard.preview_flight`
Preview a flight before saving it.

### `flight_dashboard.confirm_add`
Confirm and save the current preview.

### `flight_dashboard.add_flight`
Add a flight directly using minimal inputs.

### `flight_dashboard.clear_preview`
Clear the preview.

### `flight_dashboard.add_manual_flight`
Add a flight with full manual inputs.

### `flight_dashboard.remove_manual_flight`
Remove a manual flight by flight_key.

### `flight_dashboard.clear_manual_flights`
Clear all manual flights.

### `flight_dashboard.refresh_now`
Force a refresh of upcoming flights and status updates.

### `flight_dashboard.prune_landed`
Remove past flights (arrival time older than cutoff). Optional `hours` delay after arrival.

## Notes
- Schedule and status timestamps are stored as ISO strings (typically UTC). Convert at display time.
- Manual flights are editable; provider-sourced flights are read-only.

## Data Model (Flight Schema v3)

This integration exposes a single *upcoming flights* sensor whose `flights` attribute is a list of flight objects. Each flight uses the normalized schema below.

### Top-level fields

- `flight_key` (string): Stable unique identifier (`AIRLINE-FLIGHT-DEP-YYYY-MM-DD`). Used for selection and dedupe.
- `source` (string): `manual`, `tripit`, or provider-derived.
- `airline_code` (string): IATA airline code (e.g., `EK`, `AI`, `6E`).
- `flight_number` (string): Flight number as string (e.g., `"2"`, `"6718"`).
- `airline_name` (string|null): Airline display name (from directory or provider).
- `airline_logo_url` (string|null): Logo URL (best effort).
- `aircraft_type` (string|null): Normalized aircraft type name.
- `travellers` (list<string>): Passenger names (optional).
- `notes` (string|null): User notes (optional).
- `editable` (bool): True for manual/tripit flights.

### Status & timing (normalized)

- `status_state` (string): Canonical status: `Scheduled`, `En Route`, `Arrived`, `Cancelled`, `Diverted`, `Unknown`.
- `delay_status` (string): `on_time`, `delayed`, `cancelled`, `unknown` (computed).
- `delay_status_key` (string): Snake_case version of `delay_status` (for UI coloring).
- `delay_minutes` (int|null): Minutes vs scheduled (arrival preferred when available).
- `status_updated_at` (ISO string|null): When status was last refreshed.
- `diverted_to_iata` (string|null): Diversion airport IATA when `status_state=Diverted`.
- `diverted_to_airport` (object|null): Diversion airport details (iata/name/city/tz/tz_short).

### Duration fields (computed)

- `duration_scheduled_minutes` (int|null): Scheduled duration.
- `duration_estimated_minutes` (int|null): Estimated duration (if estimates exist).
- `duration_actual_minutes` (int|null): Actual duration (if actuals exist).
- `duration_minutes` (int|null): Best available duration (actual → estimated → scheduled).

### Departure/Arrival blocks

Each flight has `dep` and `arr` objects. Each block contains:

- `airport`:
  - `iata` (string|null)
  - `name` (string|null)
  - `city` (string|null)
  - `tz` (string|null): IANA TZ name (e.g., `Europe/Paris`)
  - `tz_short` (string|null): Short TZ label (e.g., `CET`, `+04`)
- `scheduled` / `estimated` / `actual` (ISO string|null): UTC timestamps.
- `scheduled_local` / `estimated_local` / `actual_local` (ISO string|null): Local timestamps (airport TZ) when available.
- `terminal` (string|null)
- `gate` (string|null)

### Position (optional)

- `position`:
  - `lat` / `lon` (float)
  - `alt` (int|null)
  - `gspeed` (int|null)
  - `track` (int|null)
  - `timestamp` (ISO string|null)
  - `source` (string|null)
  - `provider` (string|null)

### Raw provider status (normalized subset)

- `status` (object|null): Best-effort normalized provider status payload. This is **not** a raw passthrough; it is a normalized subset to help debugging.
  - `provider` (string): Provider name.
  - `provider_state` (string|null): Provider’s original state string.
  - `dep_scheduled` / `dep_estimated` / `dep_actual` (string|null): Provider timestamps (normalized to UTC).
  - `arr_scheduled` / `arr_estimated` / `arr_actual` (string|null): Provider timestamps (normalized to UTC).
  - `dep_iata` / `arr_iata` (string|null)
  - `aircraft_type` (string|null)
  - `terminal_dep` / `gate_dep` (string|null)
  - `terminal_arr` / `gate_arr` (string|null)
  - `position` (object|null): Provider position (if available).
  - `position_provider` (string|null)
