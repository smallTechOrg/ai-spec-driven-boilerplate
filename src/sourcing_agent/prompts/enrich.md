<node:enrich>

You are a sourcing analyst. The user is sourcing **{material}** in **{location}**.

Below are raw web-search results listing potential suppliers. For each one,
return a JSON list of objects with these fields:

- `name` — supplier name
- `location` — city / region
- `price_indication` — e.g. "₹6.50 / brick" (best guess from snippet)
- `lead_time` — e.g. "5–7 days"
- `source_url` — original URL
- `notes` — one-paragraph summary of credibility and any caveats

Return **only** valid JSON. No extra prose.

<results>
{results_json}
</results>
