---
name: pptx
description: >
  Creates a PowerPoint presentation (.pptx) from a topic description.
  Use when the user asks to "make a presentation", "create slides", or mentions .pptx.
  Trigger with "create a presentation about X", "make slides for Y", or /pptx.

parameters:
  required:
    - name: topic
      description: "Main subject or title of the presentation"
  optional:
    - name: slides
      description: "Number of slides to generate"
      default: "10"
    - name: audience
      description: "Target audience (e.g. executives, engineers, students)"
---

## Instructions

Create a complete, well-structured PowerPoint presentation based on the parameters provided.

1. Use `topic` as the central theme — research it if needed before outlining
2. Generate exactly `slides` slides (default 10 if not specified)
3. Tailor language, depth and examples to `audience` (default: general audience)
4. Structure: title slide → agenda → content slides → summary/CTA
5. Each slide: clear heading, 3–5 concise bullet points, speaker notes

Deliver the final file as a `.pptx` using the pptx skill toolchain.

---

## Parameters

**Required**
- `topic` — Main subject or title of the presentation

**Optional**
- `slides` — Number of slides to generate (default: 10)
- `audience` — Target audience: executives | engineers | students | general (default: general)

---

## Example invocations

```
/pptx topic="AI Trends 2025"
/pptx topic="Q3 Sales Review" slides="8" audience="executives"
/pptx topic="Intro to Python" slides="12" audience="students"
```
