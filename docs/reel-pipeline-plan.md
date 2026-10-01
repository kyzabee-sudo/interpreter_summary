# Interpreting Interpreter → Instagram Reel: Automated Pipeline Plan

> **Parked.** Planning only. This pipeline is not implemented, and this file is not a request to build it.
>
> **Decisions made after this plan was written:**
> - Target length is **90–120 seconds** (about **230–300 words** of script for the slower British voice). This replaces the 60–90 second / 160–230 word target in the TL;DR and in §3.1.
> - The free **Montserrat** font is approved for captions.
> - **Church artwork** should be preferred for images where possible.

*Research and plan only; nothing has been built yet. Prepared 1 Oct 2026 (MT) for Kyler Rasmussen.*
*Every price below comes from an official pricing page fetched on 1 Oct 2026, with the URL given. Anything I calculated is marked **(estimate)**.*

---

## 0. TL;DR

- **Recommended workflow:** The script bot writes a script. An LLM turns it into a **scene list** (about 8–10 scenes, each with narration, a caption, an image and a motion). **You review it.** ElevenLabs then generates the narration and returns per-character timestamps. Images come from the article PDF first, then public-domain art, with AI images only as a last resort. **You review the images.** Remotion renders the video: Ken Burns motion, word-synced boxed captions, the IF logo in the lower right and quiet music. **You watch the final cut.** Last, the pipeline drafts the post caption and hashtags. Everything can run on the box.
- **Option A, static images with motion:** about **$0.25–$1.50 in usage per video (estimate)** plus an ElevenLabs plan ($6/mo Starter or $22/mo Creator). About **20–30 minutes of your time per video (estimate)**.
- **Option B, custom per-video animations written by Claude Opus 5.5:** Option A plus about **$1–$6 of Opus 5.5 API usage per video (estimate, typically about $2)**. About **35–60 minutes of your time (estimate)**, because animations need closer review.
- **"Opus 5.5" is real.** Anthropic lists **Claude Opus 5.5 at $4 per million input tokens and $20 per million output tokens** ([docs.claude.com pricing](https://docs.claude.com/en/docs/about-claude/pricing), [anthropic.com/pricing](https://www.anthropic.com/pricing)).
- **Biggest format change:** your current videos run **86–109 s at about 190 words per minute** (about 320 words). A measured British narrator speaks more slowly (roughly 150–165 wpm, estimate). To hit 60–90 s, the script bot must aim for **about 160–230 words (about 1,000–1,450 characters)**.

---

## 1. What the current Interpreting Interpreter format actually looks like

**Sources:** the Interpreter Foundation YouTube channel (`@TheInterpreterFoundation`, Shorts tab listed with yt-dlp), public page metadata, YouTube's mid-video thumbnail frames (`hq1/hq2/hq3`, `oardefault`) for 7 recent episodes, transcripts, your OneDrive "Video Images" folders, and the `_TEMPLATE` script document. yt-dlp could list the channel, but YouTube's "confirm you're not a bot" check blocked video and metadata download from the box. So I could not download or step through a full sample video. The observations below come from still frames and page metadata.

| Attribute | Observed |
|---|---|
| Cadence | Weekly, **Fridays 11:00 PT (12:00 MT)**. Examples: Apostolic Scientists, 25 Sep 2026. Akish's Sumerian Oath, 18 Sep 2026. Sign of Cain, 27 Feb 2026. |
| Length | Apostolic Scientists **99 s**, Akish **104 s**, Sign of Cain **109 s**, Nephi's Temple Hymn **100 s**, Structuring Alma 16 **86 s**. Typical range is **86–109 s**. |
| Words / pace | Apostolic Scientists transcript: **317 words, about 1,970 characters, in 99 s ≈ 192 wpm**. |
| Scenes | The `_TEMPLATE` docx has a **"Video Script" table (# / Text / Image) with 10 rows**. Recent "Video Images" folders hold about 8–14 numbered images (e.g., 70_04 Squire has `01 - Ships` … `10 - Conclusion`, and some scenes have two images such as `04 - Elements1/2`). That works out to **about 10 scenes, about 8–11 s each**. |
| Layout | 1080×1920. A full-bleed background image fills the frame between **thin black bars at top and bottom (about 100 px each)**. You appear green-screened over the lower half. |
| Images | Classic religious paintings, archival portraits, screenshots of the article's title page, crops of scripture verses, diagrams and charts from the article (e.g., "Chiasmus in Alma 36"), and some AI-looking illustrative art. Annotation overlays (`Red Arrow.png`, `Red Outline.png`) are in the template folder. |
| Captions | **Short 2–4 word chunks, ALL CAPS, heavy bold sans-serif**, centred around 40–48% of frame height. They are usually **white with a black stroke or shadow**. Some episodes put them on a **near-black box** (sampled ≈ #141414). **Key words are highlighted in cyan (sampled ≈ #10F0F0)** or yellow (e.g., "NEPHI **4**", "**WICKED**"). |
| Caption font | Not identifiable with confidence from thumbnails. It looks like a heavy grotesque or geometric sans (Montserrat ExtraBold/Black-like). **Needs confirming with you.** |
| Logo | The **white IF sunburst icon** (`if-icon-white.png`), about 250 px wide, **in the lower-right corner** over the bottom bar on every frame sampled. The full wordmark does not appear in the frames. |
| Intro | No separate title card in sampled frames. Episodes open cold with a hook: "Did you know that Nephi had a psalm?" or "Modern apostles are almost always interesting figures…". |
| Outro | A spoken CTA: "Check out [Author]'s full article, *[Title]*, let me know what you think, and I'll see you next time/week." No outro card was visible. |
| Description | "An introduction to "[Title]" by [Author] in Volume [N] of Interpreter: A Journal of Latter-day Saint Faith and Scholarship. You can find Kyler's summary at [IF summary URL] and the full article at [journal URL]." Then a fixed hashtag block (#thechurchofjesuschristoflatterdaysaints #mormon #lds #churchofjesuschrist #ldschurch #latterdaysaints … plus topic tags). |

**What changes for the voiceover version:** with no presenter, the image fills the full frame and the captions move to the lower-middle, around 58–68% of the height, safely above Instagram's bottom UI. The boxed captions and the lower-right logo stay. The CTA becomes a short spoken line plus a 2–3 s end card with the article title and the IF logo (optional).

---

## 2. Brand assets (OneDrive, read only; nothing was changed)

Account: kyzabee@hotmail.com. Root path: `/The Box/Church/Interpreter/`.

### 2a. "Video Images" folders
There is **one per article** under `Summary Articles/<VV_AA (MmmYY) Author>/Video Images`, about 35 of them, from 60_10 (Feb24) to 70_04 (Oct26). Others sit under `Book Reviews/…/Video` and `Other Videos/…`. The master copy is in **`Summary Articles/_TEMPLATE/Video Images`** (8 files), and those files are copied into each new article folder:

| File | Format | Size (px) | Purpose (inferred) |
|---|---|---|---|
| `if-icon-white.png` | PNG, transparent | 1024×1024 | **The logo used in videos** (white sunburst) |
| `blue background.jpg` | JPEG | 1360×768 | Brand-teal background / title card |
| `blue background - video.mp4` | MP4 | n/a | Animated teal background |
| `yellow background.jpg` | JPEG | 512×315 | Accent background |
| `blank-white-background-….jpg` | JPEG | 1920×1124 | White background for text and verse cards |
| `pure black.png` | PNG | 1980×1080 | Black background |
| `Red Arrow.png` | PNG, transparent | 3000×1704 | Annotation overlay |
| `Red Outline.png` | PNG, transparent | 335×185 | Annotation overlay (highlight box) |

The same folder also holds `Author Meme.pptx` and the script template `VV_AA (MmmYY) Author.docx`. The template's sections are: Title, The Takeaway, The Q&A, The Summary, and a **Video Script table (#, Text, Image × 10)**.

Per-article images are numbered by scene (`01 - …`, `02 - …`). Formats are mixed (PNG, JPG, WEBP), and many are small (400–1100 px). **Small images will look soft when zoomed to 1080×1920.** The pipeline should upscale or blur-pad them (see §3.4).

### 2b. Logo files: `Summary Articles/Interpreter Logos/`
| File | Format | Size (px) | Notes |
|---|---|---|---|
| `if-icon-white.png` | PNG, transparent | 1024×1024 | Sunburst only, white |
| `if-icon-black.png` | PNG, transparent | 1024×1024 | Sunburst only, black |
| `if-icon-blue.png` | PNG, transparent | 1024×1024 | Sunburst only, dark teal |
| `if-logo-white.png` | PNG | 1600×530 | **Primary lockup** (sunburst + "The Interpreter Foundation") in white |
| `if-logo-white (transparent).png` | PNG, transparent | 1600×530 | Same, transparent |
| `if-logo-blue.png` | PNG, transparent | 1600×530 | Primary lockup in dark teal (#113439) |
| `if-logo-black.png` | PNG | 226×75 | Small, low resolution |
| `if-logo-white.jpg` | JPEG | 272×90 | Small, low resolution |

There is **no SVG or vector logo**. 1600 px PNGs are enough for 1080-wide video. The website also uses a yellow version (`if-logo-yellow-800x800`) that is not in OneDrive.

> ⚠️ **Decision for you:** your brief says "primary logo", but your videos use the **icon only** (`if-icon-white.png`). The full lockup at a legible size takes about 300×100 px of the corner. My recommendation is to keep the icon for consistency with your channel. The plan supports either.

### 2c. Website palette and fonts (interpreterfoundation.org CSS, fetched 1 Oct 2026)
| Token | Hex | Use on site |
|---|---|---|
| Dark teal ("fontBlue") | **#103439** (logo: #113439) | Primary brand colour and backgrounds |
| Light teal ("fontLightBlue") | **#93BCC0** | Headings and accents |
| Muted teal | #4C676B / #3D5558 | Secondary text |
| Cream | #FDF5EB | Light backgrounds |
| Tan | #C3B199 | Accent |
| White | #FFFFFF | Text on teal |

- **Fonts:** the site's main typeface is **PP Neue Montreal** (Pangram Pangram, a commercial font, so a licence is needed for video use; I did not verify its terms). There is also a Cerebri Sans Pro fallback, Noto Sans for Hebrew, Arabic and Coptic, and Georgia for serif.
- **Recommended video caption style:** a heavy free sans such as **Montserrat ExtraBold/Black** (SIL OFL, free for commercial use) in white ALL CAPS on a **dark-teal box, #103439 at about 85% opacity**, with highlight words in **light teal #93BCC0** or your existing **cyan**. Rounded corners about 12 px. Alternatively, match your current near-black box with cyan highlights for continuity.

---

## 3. Pipeline design

```
[Article PDF] → (existing script bot) → script.md
      │
      ▼
 ① Scene planner (LLM) → scenes.json ──► ⓗ HUMAN REVIEW #1 (script + scene list)
      │
      ▼
 ② ElevenLabs TTS /with-timestamps → narration.mp3 + alignment.json → words.json
      │
      ▼
 ③ Image acquisition (PDF figures → public domain → AI) → images/NN.png + credits.json
      │                                                    ──► ⓗ HUMAN REVIEW #2 (images)
      ▼
 ④ Render (Remotion) — Ken Burns + captions + logo + music + end card → reel.mp4
      │                                                    ──► ⓗ HUMAN REVIEW #3 (final watch)
      ▼
 ⑤ Post caption + hashtags + alt text → post.txt   (you post manually; nothing auto-publishes)
```

Each run lives in its own folder, e.g. `/workspace/reels/70_04-squire/`, so every stage can be re-run on its own. Fix one caption, re-render. Swap one image, re-render. The narration stays the same.

### 3.1 Script (existing bot) → input contract
- The script bot already produces the scripts. Add two constraints to its prompt: **160–230 words** and no stage directions inside the narration.
- Pass-through metadata: article title, author, volume, journal URL, IF summary URL and the PDF path. These feed the end card and the post caption.
- Spoken style for the British narrator: third person ("Clark argues…"). Drop first-person lines like "the scientist in me" and "I'll see you next time", because a generic narrator saying them as Kyler would be odd. Close with something like *"The full article, 'Scientist Apostles', is in Interpreter. Link in bio."*

### 3.2 Scene planner (step ①)
An LLM call (Claude Sonnet 5.5 is enough; Opus is not required) converts the script into `scenes.json`:

```json
{
  "meta": {"title": "Scientist Apostles", "author": "David L. Clark", "volume": 70,
           "article_url": "...", "summary_url": "...", "pdf": "article.pdf"},
  "voice": {"voice_id": "<chosen>", "model_id": "<eleven model>", "speed": 0.95},
  "scenes": [
    {"id": 1,
     "narration": "Modern apostles are almost always interesting figures.",
     "caption_emphasis": ["APOSTLES"],
     "image": {"source": "pdf_figure|pdf_page_crop|public_domain|ai|kyler_folder",
               "query_or_prompt": "James E. Talmage portrait, c. 1911",
               "pdf_page": null, "crop": null, "credit": null},
     "motion": {"type": "zoom_in|zoom_out|pan_left|pan_right|pan_up|pan_down|static",
                "focus": [0.5, 0.35], "scale_from": 1.0, "scale_to": 1.12, "ease": "inOutSine"},
     "overlay": null}
  ]
}
```

- The rules match your format: **8–10 scenes**, one image per scene, roughly one scene per sentence or clause (about 6–10 s), and motion that suits the content. Portraits get a slow zoom toward the face. Wide paintings get a lateral pan. Verse or text images get a slow pan down. Diagrams get a gentle zoom to the key element, optionally with the existing `Red Outline.png` overlay.
- Captions are **not** written by hand. They come from the narration and are chunked automatically into 2–4 word groups (§3.5). The planner only marks which words get highlighted.
- **ⓗ Review #1:** you approve or edit `scenes.json`, or a rendered Markdown table of it, together with the script. A 5–10 minute read is the cheapest place to catch mistakes.

### 3.3 ElevenLabs TTS with timestamps (step ②)
- **Endpoint:** `POST /v1/text-to-speech/{voice_id}/with-timestamps`. It returns `audio_base64` plus `alignment` and `normalized_alignment` with **per-character start and end times** ([API docs](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)).
- **Generate the whole script in one request** for natural prosody. Then group the characters into words, and map words to scenes by character offset. Scene boundaries equal the start time of each scene's first word, which gives exact timing for image cuts.
- Use `previous_text`/`next_text` or `previous_request_ids` only when re-generating a single sentence to splice in. Use `seed` for reproducibility. Use a **pronunciation dictionary** (up to 3 per request) for names like Widtsoe, Moroni, Akish, Shazer and Zelph. That dictionary is a one-time setup that grows over time.
- **Format:** `mp3_44100_128` works on all paid plans. **192 kbps MP3 needs Creator or above; 44.1 kHz WAV/PCM needs Pro or above.** 128 kbps is fine for Instagram.
- **Voice settings for "austere":** high stability (about 0.6–0.75), style 0, speed about 0.92–0.98.
- **Model:** Eleven v3 / v4 (expressive) or Multilingual v2 (stable for long-form). Not verified: whether `/with-timestamps` returns alignment for every model, v3 and v4 in particular. Test this on day one. Fallbacks are ElevenLabs Forced Alignment or local WhisperX alignment of the finished MP3.
- **Voice choice** (you should audition 3–4; none verified by listening):
  - Voice Library candidates described as British and serious: **"Older Joe"** (older RP male, "classic newsreader / documentary narrator" gravitas), **"Nathaniel C."** (deep, rich, mature British), **"James – Serious & Grim"** (very low, raspy UK, probably too grim), **"Johnny Kid – Serious"** (young British, calm). Sources: [ElevenLabs narrator voices](https://elevenlabs.io/voice-library/narrator-voices), [old-male](https://elevenlabs.io/voice-library/old-male), [serious](https://elevenlabs.io/voice-library/serious).
  - ⚠️ **Avoid the built-in "Default" voices** (e.g., the familiar British "Daniel"/"George"). ElevenLabs says **"All our Default voices will expire on December 31, 2026"** ([Voices docs](https://elevenlabs.io/docs/overview/capabilities/voices)).
  - **Voice Library voices are not available via the API on the free tier** (same page).
  - **Most durable option:** use **Voice Design** to create your own voice from a prompt, e.g. "older male, received pronunciation, austere, dry, measured, BBC documentary narrator, minimal emotion". You own it, so a library sharer cannot withdraw it. Pick one of the 3 previews and lock the voice ID.
- **Commercial use: a paid plan is required.** "The free plan does not include a commercial license and cannot be used for any commercial purpose… All paid plans include a commercial license." Free-tier output must also carry "elevenlabs.io" attribution in the title ([ElevenLabs help](https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform)). Interpreter is a non-profit, but posting branded content publicly is safest on **Starter or above**.

### 3.4 Images (step ③): sources and tradeoffs
Sources in order of preference, chosen per scene by `image.source`:

1. **The article PDF itself.** Figures are extracted with `pdfimages`/PyMuPDF, and pages are rendered with `pdftoppm -r 300`. That covers the title page, verse crops, charts and diagrams, matching what you already do with "Title page", "Verses 10 and 11" and "Elements1". This is free, perfectly on-topic, and Interpreter's own content. Some PDFs have few figures.
2. **Your existing folder.** If you have already gathered images for the article (the same images you use for the on-camera version), the pipeline takes `Video Images/NN - *.png` as scene NN. **This is the lowest-risk path, and it reuses work you already do.**
3. **Public-domain or open-licence art.** Wikimedia Commons (licence checked per file), The Met Open Access (CC0), Art Institute of Chicago (CC0), Library of Congress, Rijksmuseum. These suit portraits of early-1900s apostles, classic biblical paintings, maps and archaeology photos. The pipeline records attribution in `credits.json`. Downsides: searching takes time, quality varies, and LDS-specific subjects are thin.
4. **Church media and art** (e.g., Christus, apostle photos, Church paintings). You already use these. Their terms are the Church's, so this is your call. The pipeline can flag such images rather than decide.
5. **AI-generated images** (last resort, illustrative only):
   - Pros: unlimited, fast, a consistent look, exactly 9:16.
   - Cons: factual risk (anachronistic armour, wrong temple layouts, invented artefacts), sensitivity around depicting sacred figures, and a credibility cost for a scholarly brand if viewers spot "AI slop". Meta may also label AI content.
   - Rule: **never use AI for real people, real artefacts, scripture text or anything the article argues is historically specific.** Use it only for atmosphere: landscapes, generic ancient scenes, abstract backgrounds.
   - Price, Gemini 3.1 Flash Image ("Nano Banana 2"): **$0.067 per 1K image, $0.101 per 2K image**. Gemini 3 Pro Image: **$0.134 per 1K/2K image**. Batch pricing is half ([Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)).
   - OpenAI's gpt-image models are also an option, but I couldn't reliably extract per-image prices from their page, so they are left unpriced here.

**Pre-processing every image:** fit it to 1080×1920 with headroom for motion; render about 1.25× (1350×2400) so zooms stay sharp. If the source is smaller than about 1350 px tall, either (a) upscale with Real-ESRGAN (free, runs on CPU, slow but OK) or (b) use **blur-pad**: a blurred, darkened copy of the image fills the frame behind a sharp, centred copy. Blur-pad is the right treatment for landscape paintings and verse screenshots.

**ⓗ Review #2:** a contact sheet (one PNG grid of all scenes with their captions) for a quick approve or swap.

### 3.5 Captions from ElevenLabs alignment
- Characters become words (split on whitespace, carrying start and end times). Words become **chunks of 2–4 words**, broken at punctuation, never longer than about 1.2 s or 18 characters, and never crossing a scene boundary.
- Each chunk appears at its first word's start and disappears at its last word's end. Small gaps are padded so captions don't flicker.
- Style: ALL CAPS, bold sans, 64–76 px, white text on a rounded box (#103439 at 85%, or near-black). **Highlight words** come from `caption_emphasis`, automatically extended to names and numbers, coloured cyan or light teal. An optional per-word "active word" colour pop, timed to the word, is trivial in Remotion.
- Position: horizontally centred at about 60–66% of the height. That keeps captions inside Instagram's safe area and clear of the logo. (Instagram's UI overlay zones are general guidance; I didn't check them against an official spec.)
- Also export `captions.srt`, useful for YouTube Shorts cross-posting and accessibility.

### 3.6 Logo, music, end card
- **Logo:** `if-icon-white.png` at about 220–250 px wide, 40–48 px from the right and bottom edges, raised above the IG UI zone (about 1660–1700 px from the top). Opacity 90–100%, with a subtle drop shadow so it shows on light images. It stays on every frame, as you require.
- **Music:** a low ambient or choral-pad bed at about −24 to −28 LUFS under the voice, with auto-ducking via sidechain compression or simple volume automation driven by the word timestamps. Sources:
  - **ElevenLabs Music:** 900 credits/min. "Commercial use licensing on Starter+ plans" ([pricing/api](https://elevenlabs.io/pricing/api)). Generate one 90 s bed per video, or a small reusable library of 5–10 beds.
  - **A fixed royalty-free track you already license.**
  - **Instagram's in-app music:** added at posting time, so not baked in.
- **End card (optional, 2–3 s):** a dark-teal (#103439) background, the article title, "by [Author] · Interpreter, Vol. [N]" and the full white `if-logo-white (transparent).png` lockup.
- **Loudness/export:** H.264 High, 1080×1920, 30 fps, about 8–12 Mbps, AAC 48 kHz 192 kbps, loudness normalised to about −14 LUFS integrated.

### 3.7 Renderer: Remotion vs ffmpeg vs MoviePy

| | **Remotion** (React/TS) | **ffmpeg** (filtergraph + ASS subs) | **MoviePy** (Python) |
|---|---|---|---|
| Ken Burns | Easy and smooth (`interpolate`/`spring` on transform, sub-pixel) | `zoompan` judders unless you pre-upscale 4–8×; `crop`+`scale` expressions work but are fiddly | OK, but slow per-frame Python |
| Boxed, word-synced captions | Best: any CSS (rounded boxes, highlight words, active-word pop) | ASS subtitles (`BorderStyle=3` box, karaoke tags) are capable but awkward to style | Pillow text, workable, rough edges |
| Custom per-video animations (Option B) | **Native**: Opus writes React components | Impractical | Possible but clumsy |
| Speed on the box (8 vCPU, 15 GB RAM) | About 2–6 min per 90 s reel (estimate), headless Chrome | About 20–60 s (estimate) | About 3–10 min (estimate) |
| Dependencies | Node 20 (present), Chrome (present) | ffmpeg 7.1 (present) | pip install |
| Licence | **Free for individuals, companies with ≤3 employees and non-profits** ([remotion.dev/license](https://www.remotion.dev/license)) | LGPL/GPL, free | MIT, free |
| Preview | Remotion Studio in the browser, scrubbable | none | none |

**Recommendation: Remotion for both options,** with ffmpeg only for audio mixing, loudness and final muxing.
- Reasons: one template codebase, captions that match your style, and Option B is just "add a per-video component" on top of the same engine. You could watch and scrub drafts in Remotion Studio on the box's desktop.
- Licence: you as an individual, and the Interpreter Foundation as a non-profit (I believe it is one; please confirm), both fall under the free licence.
- An ffmpeg-only MVP is a viable cheaper first step if you just want something working in a day, but captions will look less polished.

### 3.8 Option B: custom per-video animations with Claude Opus 5.5
- **What it is:** for each video, Opus 5.5 gets the script, `scenes.json`, `words.json` (timings) and the images. It writes **one or more Remotion components** for scenes that benefit from motion graphics: an animated chiasm that builds A-B-C-B′-A′ line by line, a map with a route drawn on (e.g., Lehi's trail to Shazer), a timeline of three apostles, a Hebrew word that morphs into its English glosses, or a bar chart from the article.
- **Loop:** Opus writes code, the box renders still frames, Opus reviews screenshots (vision) and fixes problems, repeated 2–4 times. Then the full render goes to you.
- **Guardrails:** components must use a fixed **brand kit** (colours, fonts, logo-safe zone, caption layer untouched) and a whitelist of libraries. They must type-check and render without errors, or the scene falls back to Option A's Ken Burns. If animation breaks, the video still ships.
- **Motion Canvas** is an alternative to Remotion. Remotion is preferred because of the shared caption and template code and the stronger LLM familiarity with React.

### 3.9 Post caption drafting (step ⑤)
A cheap LLM call (Haiku 4.5 or Sonnet 5.5) produces a post draft in your existing YouTube-description style:
- a 1–2 line hook taken from the script
- "An introduction to "[Title]" by [Author] in Volume [N] of *Interpreter: A Journal of Latter-day Saint Faith and Scholarship*."
- "Full article and Kyler's summary: link in bio." (Instagram captions don't make URLs clickable.)
- the fixed hashtag block plus 3–6 topic tags
- alt text for accessibility

It is saved as `post.txt`. **Nothing is posted automatically.** You post from the app, or later via the Instagram Graph API, which would need a Business/Creator account linked to a Facebook Page and is out of scope here.

### 3.10 Human review points (summary)
| # | When | What you check | Time (estimate) |
|---|---|---|---|
| 1 | After the scene list | Script accuracy, tone, scene-to-image ideas, pronunciations | 5–10 min |
| 2 | After images | Contact sheet: wrong or unsafe images, licensing flags, AI images | 5–10 min |
| 3 | After render | Full watch: audio, caption sync, logo, end card (Option B: animation accuracy) | 3–5 min (B: +10–20 min) |
| 4 | Before posting | Post caption and hashtags | 2 min |

---

## 4. Pricing (official pages, fetched 1 Oct 2026)

### 4.1 ElevenLabs: [elevenlabs.io/pricing](https://elevenlabs.io/pricing) and [elevenlabs.io/pricing/api](https://elevenlabs.io/pricing/api)

| Plan | Price | Credits/mo | Notes |
|---|---|---|---|
| Free | $0 | 10k | **No commercial licence**; attribution required; no Voice Library voices via API |
| Starter | $6/mo | 30k | **Commercial licence**, Instant Voice Cloning, Music commercial use |
| Creator | $22/mo ($11 first month) | 121k | + Professional Voice Cloning, 192 kbps |
| Pro | $99/mo | 600k | + 44.1 kHz PCM via API |
| Scale / Business | $299 / $990 | 1.8M / 6M | Teams |

- **Credit rules:** "Text to Speech 1 credit per character", "Eleven Music 900 credits per minute". The FAQ notes discounted rates for Flash/Turbo models via API (0.5–1 credit per character). Unused credits roll over for up to two months on paid plans. Annual billing equals 10× the monthly price.
- **API pay-as-you-go list rates:** v3 and Multilingual v2 **$0.08 per 1K characters**, Flash/Turbo **$0.04 per 1K**. v4 is listed at $0.08 per 1K, currently **$0.022 promo until Oct 12**. Music costs **$0.15/min**. The API page's "characters included" figures per plan differ from the credit figures on the main pricing page (e.g., Starter is shown with 75,000 v3 characters). **Confirm in the dashboard which applies to API use on your plan.**

**Per-video ElevenLabs usage (estimate):**
| Item | Characters/credits |
|---|---|
| 60–90 s script at about 155 wpm ≈ 155–230 words ≈ 1,000–1,450 chars | ~1,000–1,450 per take |
| Allow about 3 takes and partial regenerations | ~3,000–4,500 |
| Optional 90 s music bed | ~1,350 |
| **Total per video** | **~3,000–6,000 credits** |

- **Starter ($6, 30k credits):** about 5 videos per month at the upper estimate. That covers weekly, but tightly. The amortised cost is about **$1.20–$1.50 per video**; the marginal cost is about $0.20 per 1k characters, so about **$0.20–$0.30 per narration take**.
- **Creator ($22, 121k credits):** plenty of headroom, and it adds 192 kbps. About $5 per video amortised at 4–5 videos per month.
- **API pay-as-you-go at $0.08 per 1K:** about **$0.08–$0.12 per take**. Check that pay-as-you-go use carries the commercial licence; the help page says "paid plans".
- **Recommendation:** start on **Starter**, and move to Creator if you regenerate a lot or want music generated per video.

### 4.2 Image generation (only if used): [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Gemini 3.1 Flash Image: **$0.067 per 1K image, $0.101 per 2K image** (batch $0.034 / $0.050).
- Gemini 3 Pro Image: **$0.134 per 1K/2K image**.
- 0–4 AI images per video ≈ **$0–$0.55 (estimate)**. Images from the PDF, your folder and public-domain sources cost $0.

### 4.3 "Opus 5.5" (verified): [docs.claude.com pricing](https://docs.claude.com/en/docs/about-claude/pricing) and [anthropic.com/pricing](https://www.anthropic.com/pricing)
**Claude Opus 5.5** is a current Anthropic model ("Daily driver for agentic coding and enterprise work"):

| Opus 5.5 rate | $/million tokens |
|---|---|
| Input | **$4** |
| Output | **$20** |
| 5-min cache write / 1-h cache write | $5 / $8 |
| Cache read | **$0.20** (0.05× input) |
| Batch input / output | $2 / $10 |
| Fast mode input / output | $8 / $40 |

For comparison, Sonnet 5.5 costs $2 / $10 and Haiku 4.5 costs $1 / $5. The docs note that newer models' tokenizer produces about 30% more tokens for the same text.

**Per-video estimate for Option B (estimate; token assumptions stated):**
| Step | Assumption | Cost |
|---|---|---|
| Initial context | ~30k tokens (brand kit + Remotion component library/docs excerpt + script + scenes + timings), written to cache | 30k × $5/M = $0.15 |
| First code pass | ~15k output tokens (components + reasoning) | 15k × $20/M = $0.30 |
| 3 review/fix rounds | each: 35k cached read ($0.007) + ~5k new text + ~12k of screenshot frames as input (~$0.07) + ~6k output ($0.12) | ≈ 3 × $0.20 = $0.60 |
| **Typical total** | ~80–100k input (mostly cached), ~35k output | **≈ $1.00–$1.50** |
| Heavy case | long agentic session (Claude Code-style): ~1M input, half uncached, ~100k output incl. thinking | ≈ $2 + $0.10 + $2 = **≈ $4–$6** |

So budget **about $2 per video, with a $6 ceiling (estimate)**. With prompt caching and a strict component library, a cap of about $3 per video is realistic. An alternative is running it through a Claude Pro/Max subscription (Claude Code is included; Pro is $20/mo billed monthly). That is a flat fee with usage limits instead of metered API use, suitable if you're already subscribed.

The scene planner and post caption add **about $0.03–$0.10 per video** on Sonnet 5.5 (e.g., 10k in plus 3k out ≈ $0.05) (estimate).

### 4.4 Per-video totals (estimate)
| | Option A: static + motion | Option B: + custom Opus 5.5 animation |
|---|---|---|
| ElevenLabs narration (marginal) | $0.10–$0.30 | $0.10–$0.30 |
| Music (ElevenLabs, optional) | $0–$0.25 | $0–$0.25 |
| Scene planner + post caption (Sonnet 5.5) | ~$0.05–$0.10 | ~$0.05–$0.10 |
| AI images (optional, 0–4) | $0–$0.55 | $0–$0.55 |
| Opus 5.5 animation code | n/a | ~$1–$6 (typ. ~$2) |
| Rendering | $0 (box) | $0 (box) |
| **Usage per video** | **≈ $0.25–$1.20** | **≈ $1.25–$7 (typ. ~$2.50)** |
| Fixed monthly | ElevenLabs Starter $6 (or Creator $22) | same |
| **All-in per video at 4.3 videos/mo, Starter** | **≈ $1.65–$2.60** | **≈ $2.65–$8.40** |

---

## 5. What you'd need

### 5.1 Accounts and API keys
| Need | For | Notes |
|---|---|---|
| **ElevenLabs paid plan (Starter+) + API key** | Narration, timestamps, optional music | Required for commercial licence and Voice Library voices via API |
| **Anthropic API key** (Console, prepaid credits) | Scene planner and captions (Sonnet 5.5); Option B (Opus 5.5) | Set a monthly spend limit |
| Google Gemini API key (paid tier), *optional* | AI images | Only if you want AI images; the free tier does not offer image models |
| OneDrive access (already connected, read only) | Pull article PDF, script docx and `Video Images`; optionally write the finished reel back | Writing back would need your OK |
| Instagram | You post manually | Graph API auto-posting needs a Business/Creator account plus a FB Page; not planned |
| Font licence, *optional* | Only if you want the brand font PP Neue Montreal | Otherwise use free Montserrat |

Keys go in a box-only `.env` (`ELEVENLABS_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`), never in OneDrive or the repo.

### 5.2 Hardware/compute
**The box is enough.** It has 8 vCPU, 15 GB RAM, 88 GB free disk, x86_64, ffmpeg 7.1, Node 20 and Google Chrome already installed. No GPU is needed: TTS, image generation and the LLMs are APIs, and Remotion renders on CPU. Optional local upscaling with Real-ESRGAN on CPU is slow but fine for 8–10 images. Nothing needs to run on your own computer.

### 5.3 One-time setup work (estimate)
| Task | Effort |
|---|---|
| Remotion project with brand template: frame, Ken Burns scene, blur-pad, caption layer, logo, end card, music ducking | 1–1.5 days (agent) |
| Python orchestrator: OneDrive fetch → planner → TTS + alignment → word/scene timing → images → render → post caption; per-run folders; re-run any step | 1 day |
| Image tools: PDF figure extraction and page crops, public-domain search helpers with credit capture, Gemini image fallback, contact sheet | 0.5–1 day |
| Voice audition (3–4 library voices + 1 Voice Design) and pronunciation dictionary seed (names from recent articles) | 30–60 min **of your time** |
| Style sign-off: render one past episode (e.g., Apostolic Scientists) both ways and compare against your on-camera version | 30 min **of your time** |
| *Option B only:* brand-kit component library (chiasm builder, timeline, map route, quote card, chart) + Opus prompt + render-check-fix loop + fallback | +1–2 days (agent) |

### 5.4 Per-video time (estimate)
| | Option A | Option B |
|---|---|---|
| Machine time | ~10–15 min (TTS ~1 min, images 1–5 min, render 2–6 min) | ~25–45 min (+ Opus loop 10–25 min, more renders) |
| **Your time** | **~20–30 min** (3 reviews + posting) | **~35–60 min** |

---

## 6. Open questions / not verified

1. **Logo:** the full "primary" lockup or the icon you currently use? (Recommendation: the icon.)
2. **Caption font and editor:** which font and app do you use now? I couldn't identify the font from thumbnails.
3. **Script length:** confirm the 60–90 s target, which means about 160–230 words. That is shorter than your current ~320-word scripts.
4. **Voice:** I haven't listened to any candidate. You need to audition. Also check whether a chosen Voice Library voice can be withdrawn by its sharer (Voice Design avoids the question).
5. **ElevenLabs details:** whether `/with-timestamps` returns alignment on v3/v4 (test on day one), and how API "characters included" relates to plan credits (the pricing pages differ).
6. **Church and Wikimedia image licensing:** your call per image. The pipeline only flags it.
7. **OpenAI image pricing:** I couldn't extract reliable per-image figures, so it is left unpriced.
8. **Full video sampling:** YouTube's bot check blocked yt-dlp video and metadata download from the box. I couldn't confirm intro/outro animations, transitions, music or exact caption timing. All observations come from frames and transcripts.
9. **Instagram safe zones:** the caption and logo positions follow common guidance, not an official Meta spec.
10. **Non-profit status:** I believe Interpreter Foundation is a non-profit, which matters for Remotion's free licence. You also qualify as an individual.

---

## Appendix: sources
- YouTube channel: https://www.youtube.com/@TheInterpreterFoundation (Shorts list via yt-dlp; episode pages for length and publish date; frames from i.ytimg.com)
- Sample episodes: Apostolic Scientists (TGc5-o3IDJw, 99 s), Akish's Sumerian Oath (nT2lp_oJVa4, 104 s), Sign of Cain (FPk3U6oyPc4, 109 s), Nephi's Temple Hymn (MnDd3tDqyMU, 100 s), Structuring Alma 16 (MZSB4I7Cw64, 86 s)
- ElevenLabs pricing: https://elevenlabs.io/pricing · API pricing: https://elevenlabs.io/pricing/api
- ElevenLabs timestamps API: https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps
- ElevenLabs voices (default-voice expiry, free-tier API limit): https://elevenlabs.io/docs/overview/capabilities/voices
- ElevenLabs commercial use: https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform
- ElevenLabs voice library: https://elevenlabs.io/voice-library/narrator-voices · /old-male · /serious
- Anthropic pricing: https://docs.claude.com/en/docs/about-claude/pricing · https://www.anthropic.com/pricing
- Gemini API pricing (image models): https://ai.google.dev/gemini-api/docs/pricing
- Remotion licence: https://www.remotion.dev/license
- Interpreter Foundation site CSS (colours, fonts): https://interpreterfoundation.org/
- Local working files on the box: `/workspace/reel-pipeline/samples/` (frames, montage), `/workspace/reel-pipeline/assets/` (downloaded logo copies, template docx), `/workspace/reel-pipeline/site/` (site CSS)
