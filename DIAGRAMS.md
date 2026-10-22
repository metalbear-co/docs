# Diagram style

All diagrams in the docs use one style. Write each diagram as a hand-written SVG file in `docs/.gitbook/assets/`. Do not export diagrams from Excalidraw, D2, draw.io, or Figma, and do not add PNG diagrams. Screenshots of the product are not diagrams, and this guide does not apply to them.

Two diagrams show the style well. Copy from them when you start a new one:

- `docs/.gitbook/assets/api-gateway-traffic.svg`
- `docs/.gitbook/assets/header-propagation.svg`

## File

- Root element: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" width="W" height="H" font-family="Inter, Helvetica, Arial, sans-serif" role="img" aria-labelledby="t d">`.
- Width: 960 to 1200. GitBook scales the image down to the page width, so a wider image makes the text too small.
- Put a `<title id="t">` and a `<desc id="d">` first. The `desc` tells the full flow in words, for screen readers.
- Put a white background as the first shape: `<rect x="0" y="0" width="W" height="H" fill="#ffffff"/>`. GitBook dark mode needs it.
- Keep the file small and readable. Use plain `rect`, `line`, `path`, `polyline`, `circle`, `ellipse`, and `text`. Do not embed fonts, raster images, or base64 data. Add a short comment before each group of shapes.

## Colors

| Use | Fill | Text |
|-----|------|------|
| Neutral component (client, service, queue, database) | `#ffffff` | `#232141` |
| mirrord component (agent, operator, layer, CLI, forwarder) | `#756DF3` | `#ffffff` |
| Your local process or your machine | `#756DF3` | `#ffffff` |
| The deployed workload or the original target | `#E4E3FD` | `#232141` |
| Gateway, broker, or other infrastructure to highlight | `#FFCB7D` | `#232141` |
| Temporary resource that mirrord creates | `#F5F4FE`, dashed `#756DF3` stroke, `stroke-dasharray="8 6"` | `#232141` |
| Boundary (cluster, machine, namespace) | `#F5F4FE`, dashed `#756DF3` stroke, `stroke-dasharray="8 6"` | label `#4a44b8` |
| Inactive or dropped path | none | `#8a8a99` |

- Outline every box with `stroke="#232141" stroke-width="2"`. A boundary is the one exception.
- Secondary text inside boxes uses `#333344` (or `#ffffff` on a purple box).
- Do not use other colors. Do not use red, green, or blue to show "match" and "no match". Use the purple path for the mirrord route and the dark path for the normal route.

## Shapes

- Box: `rx="12"`. A box inside a box: `rx="8"` to `rx="10"`.
- Database: a cylinder (an `ellipse` top on a `path` body), same stroke and colors as a box.
- Queue or topic: a box with three thin vertical lines at the right end, or a plain box with the type in the secondary text.
- Do not draw icons, logos, mascots, laptops, clouds, or hand-drawn shapes. Put the kind of thing in the text: "Kubernetes cluster", "Your machine".

## Text

- Box title: `font-size="16" font-weight="700"`. Smaller boxes may use 14.
- Secondary text: `font-size="12.5"`.
- Boundary label: `font-size="15" font-weight="700" fill="#4a44b8"`, top-left inside the boundary.
- Arrow label: `font-size="12.5"`, `#4a44b8` for the mirrord route, `#333344` for others.
- Code, headers, queue names, and resource names: `font-family="Menlo, Consolas, monospace"`.
- Do not put a title in the image. The page caption (the alt text) is the title.
- Use sentence case. Text must not touch a box edge or another text line. Keep at least 10px of space.

## Arrows

- Normal route: `stroke="#232141" stroke-width="2.5"` with `marker-end="url(#arrow)"`.
- mirrord route (traffic that mirrord sends to you): `stroke="#756DF3"` with `marker-end="url(#arrow-purple)"`.
- Dropped or inactive route: `stroke="#ACACAC" stroke-dasharray="6 5"` with `marker-end="url(#arrow-grey)"`.
- Define the markers once in `<defs>`:

```xml
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
  <path d="M0 0 L10 5 L0 10 z" fill="#232141"/>
</marker>
<marker id="arrow-purple" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
  <path d="M0 0 L10 5 L0 10 z" fill="#756DF3"/>
</marker>
<marker id="arrow-grey" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
  <path d="M0 0 L10 5 L0 10 z" fill="#ACACAC"/>
</marker>
```

- Use straight lines or right-angle `polyline`s. Do not use curves. Arrows must not cross boxes or labels.
- Flow goes left to right, or top to bottom.

## Check a diagram

Render the file and look at it before you open a PR:

```sh
rsvg-convert -w 1200 -b white docs/.gitbook/assets/<name>.svg -o /tmp/<name>.png
```
