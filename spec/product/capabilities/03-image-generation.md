# Capability: Image Generation

## What It Does

Generates a cover image for a blog post using the Gemini Imagen API, saves it to the output directory, and records the file path in the post record.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|---------|
| post_title | str | Post generation output | yes |
| post_topic | str | Topic discovery output | yes |
| blog_niche | str | Blog config | yes |
| output_dir | str | Blog config | yes |
| post_id | int | Post record | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| cover_image_path | str | Post record (relative path, e.g. "images/post-42-cover.png") |
| cover_image_prompt | str | Post record (stored for debugging/auditing) |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini Imagen API | Generate 1 image from a derived prompt | Use a placeholder SVG; post still published without a real image |

## Image Prompt Derivation

The image prompt is constructed programmatically (not by another LLM call):

```
"A high-quality blog header image for a post titled '{post_title}'. 
 Subject: {post_topic}. Style: clean, modern, editorial photography. 
 No text or typography in the image."
```

## Business Rules

- One cover image per post
- Image saved as PNG to `{output_dir}/images/post-{id}-cover.png`
- If Imagen API fails or is unavailable: write a placeholder SVG at the same path (a simple gradient with the blog niche as text) so the HTML post still renders correctly
- Image dimensions: 1200×630px (standard blog open-graph size) — request this size from the API
- The image file must exist on disk before the HTML renderer writes the post page

## Success Criteria

- [ ] A file exists at `{output_dir}/images/post-{id}-cover.png` after generation
- [ ] The cover_image_path in the post record matches the actual file path
- [ ] On Imagen API failure, a placeholder SVG is created at the expected path and the run continues
- [ ] The generated image (or placeholder) renders correctly when the HTML post is opened in a browser
