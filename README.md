# Frigate Deep Links

A small Home Assistant custom integration that exposes the one thing Frigate's
dashboard cards need but the official integration does not provide: **event and
review IDs** (plus ready-made deep links) for recent detections.

It is deliberately not a card. Rendering stays with whatever card you already
trust — `FrigateViewCard`, `advanced-camera-card`, or anything else that
understands `?event=…`, `?review=…`, `?camera=…`, `?media=clip|snapshot`.

## Why

Frigate's `image.<camera>_<label>` entity holds the latest snapshot but no event
ID, so dashboards cannot link to the clip behind a thumbnail. Building those
links by hand means MQTT plumbing, rolling JSON lists and template gymnastics.

This integration keeps that state where it belongs: in entities and services.

## What you get

| Entity | Purpose |
|---|---|
| `event.<camera>_last_<label>_event` | Fires `detection` on every new event; attributes carry `event_id`, `review_id`, `deep_link`, media paths |
| `sensor.<camera>_recent_events` | Count of recent events; `events` attribute is the list (id, label, start, review_id, thumbnail_path, deep_link) |

| Service | Returns |
|---|---|
| `frigate_deeplinks.url` | `{path, url, event_id, review_id, camera, media, thumbnail_path, snapshot_path, clip_path}` |

Attributes on the event entity:

```yaml
event_id: "1794295311.536169-1g7rxn"
review_id: "1794295311.536169-abc123"
camera: terassenkamera
label: cat
start: "2026-11-10T07:21:51+00:00"
end: "2026-11-10T07:22:06+00:00"
duration: 15.2
has_clip: true
has_snapshot: true
deep_link: /dashboard-zuhause/kamera?camera=terassenkamera&event=1794295311.536169-1g7rxn&media=clip
deep_link_snapshot: /dashboard-zuhause/kamera?camera=terassenkamera&event=1794295311.536169-1g7rxn&media=snapshot
thumbnail_path: /api/frigate/notifications/1794295311.536169-1g7rxn/thumbnail.jpg
snapshot_path: /api/frigate/notifications/1794295311.536169-1g7rxn/snapshot.jpg
clip_path: /api/frigate/notifications/1794295311.536169-1g7rxn/clip.mp4
```

The media paths are served by the official Frigate integration's notification
proxy, which is why they also work in notification attachments and markdown
cards.

## Install

### HACS (custom repository)

1. HACS → three-dot menu → *Custom repositories*
2. Add this repository URL, category **Integration**
3. Install, then restart Home Assistant
4. Settings → Devices & services → *Add integration* → **Frigate Deep Links**

### Manual

Copy `custom_components/frigate_deeplinks` into your `config/custom_components`
folder and restart.

## Configuration

| Field | Default | Notes |
|---|---|---|
| Frigate URL | `http://ccab4aaf-frigate:5000` | Add-on hostname, LAN IP, or hostname |
| Username / Password | empty | Only needed if Frigate auth is enabled |
| Poll interval | `15` s | 5–300 s |
| Dashboard path | `lovelace` | Used when building links, e.g. `dashboard-zuhause` |
| View path | `camera` | Used when building links, e.g. `kamera` |
| Labels | empty | Empty follows Frigate's own `objects.track` per camera |

Cameras with detection disabled, and labels Frigate does not track, are skipped
automatically.

## Examples

### Notification that opens the clip

```yaml
action: notify.mobile_app_iphone
data:
  title: "Katze an der Terrasse"
  message: "Neues Ereignis"
  data:
    url: >-
      /dashboard-zuhause/kamera?camera=terassenkamera&event={{
        state_attr('event.terassenkamera_last_cat_event', 'event_id')
      }}&media=clip
```

### Build a link in an automation

```yaml
- action: frigate_deeplinks.url
  data:
    event_id: "{{ state_attr('event.terassenkamera_last_person_event', 'event_id') }}"
    media: clip
  response_variable: link
- action: notify.mobile_app_iphone
  data:
    message: "Clip öffnen"
    data:
      url: "{{ link.path }}"
```

### Thumbnail row for a dashboard

```yaml
type: markdown
text_only: true
content: >-
  {% for e in state_attr('sensor.terassenkamera_recent_events', 'events') or [] -%}
  [![{{ e.label }}]({{ e.thumbnail_path }})]({{ e.deep_link }})
  {%- endfor %}
```

Add `card_mod` to turn the paragraph into a horizontal scroller with square
crops.

### Trigger on a new detection

```yaml
trigger:
  - trigger: state
    entity_id: event.terassenkamera_last_person_event
  - trigger: event
    event_type: frigate_deeplinks_detection
```

The `event` platform is the cheapest trigger — the entity's state changes to the
fire timestamp on every detection.

## Limitations

- History is in-memory and limited to the last 48 h (200 events). Deep links only
  ever point at recent clips, so this is intentional.
- Review IDs are resolved by polling `/api/review`; if a review is created after
  the event was polled, the next refresh fills it in.
- No own UI and no own media proxy: media is served through the Frigate
  integration. Without the Frigate integration installed, the media paths 404.
- Polling, not push. Live MQTT updates via `frigate/events` are the next step.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -r requirements_dev.txt
.venv/bin/pytest -q
```

`hassfest` and the HACS validation action run in CI (see `.github/workflows`).
