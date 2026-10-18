# Landing rasters

`orbit/f_001.webp` .. `f_081.webp` are every third frame of one generated clip, cropped to the centre 1000x1080 and scaled to 800x864.

- Source still: Magnific `images_generate`, 16:9, two uploaded style references (dark isometric layer-stack diagrams, used for style only). Prompt: exploded isometric stack of five wireframe layers (data sources, grid plane, network graph plane, table plane, dashboard plane) with a rising curved arrow, hairline white linework on near-black, no text.
- Clip: Magnific `video_generate`, Seedance 2.5, 10 s, 1080p, start frame = the still above. Prompt: slow 50 degree orbit left while descending, layers rigid and parallel, pale blue pulses travelling up through the layers, no new objects, no text.
- Generated 2026-10-18. No Palantir artwork is reused; the references set style only.
- Frames: `ffmpeg select=not(mod(n,3)), crop=1000:1080:460:0, scale=800:-2`, then graded (hue saturation 0.7, black point lifted to cut bloom) and `cwebp -q 62`.

`strait-2400.webp`, `strait-1200.webp`: Magnific `images_generate` (auto model, 2:1), then Magnific `images_upscale` 2x (creative, NatureAndLandscapes, subtle). Prompt: night satellite view of the Strait of Malacca and Singapore from low orbit, city lights, faint shipping lanes as thin luminous lines across dark water, cloud wisps, near-black and deep steel-blue tones, documentary realism, no text. It is a generated image, not a satellite photograph, and the page says so.

`geo/countries.json`: Natural Earth 1:110m admin-0 countries (public domain), coordinates rounded to 0.01 degrees, joined by ISO code to the reference layer's FATF, EU and Basel fields.

`ai-builder-cup.webp`: the official AI Builder Cup logo (Google Cloud x Hack2skill) from the event site, cropped to the wordmark, black converted to alpha. Entrant credit, added at the owner's request.

`workstation-aml.webp`, `workstation-exec.webp`: screenshots of the real workstations (production build, local engine gateway, synthetic client data, demo operator), 2026-10-18.

`push/f_001.webp` .. `f_065.webp`: every third frame of a second generated clip, the push-in used before the closing call to action. Still: Magnific `images_generate` (auto, 16:9, two variants, the second used). Clip: Magnific `video_generate`, Seedance 2.5, 8 s, 1080p, start frame = that still, no audio. Prompt: slow continuous push-in, camera glides forward and rises over the layers until the top dashboard plane fills the frame, layers rigid, pale blue pulses travel up the arrow, no new objects, no text. Frames scaled to 1280 px, black point lifted, saturation 0.7, `cwebp -q 60`. Generated 2026-10-18. The map on the dashboard plane is generated art, not a real region.
