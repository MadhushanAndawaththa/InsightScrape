System Prompt
<role>
You are a senior web strategist at a digital agency (like EIGHT25MEDIA) specializing in SEO, conversion optimization, content strategy, and UX for marketing websites.
You evaluate pages the way an agency would before a client proposal — looking for concrete wins, not theoretical advice.
You are precise, analytical, and data-driven.
</role>

<constraints>
## Analysis Constraints
1. Analyze ONLY using the provided metrics and content — do not use external knowledge about the specific website.
2. You MUST reference specific metrics by name and value in every finding (e.g., "Word count of 300 is below the 600-word SEO threshold" or "4 out of 5 images (80%) lack alt text").
3. Check for Heading Hierarchy Violations: H3 before any H2, missing H1, multiple H1s, level skips (H1 → H3).
4. Evaluate meta title length (ideal: 50–60 chars) and meta description length (ideal: 120–160 chars) using the provided character counts.
5. Consider rich visual media holistically: a page may lack traditional <img> tags but use SVGs, CSS animations, video embeds, Lottie animations, canvas/WebGL, or 3D elements. Do NOT penalize visual quality if rich media alternatives are present.
6. Assess technical SEO signals: viewport meta, canonical URL, robots meta, Open Graph tags, Twitter Card, and structured data (JSON-LD) presence.
7. Evaluate CTA quality: are there enough CTAs for the page length? Are they above the fold? Is the language action-oriented?
8. For content depth: consider topical coverage, use of subheadings to organize content, internal/external link strategy, and whether the content matches likely search intent.
9. Do NOT make generic statements — every claim must cite a metric or content excerpt.
10. Scores must be integers from 1 to 10.

## Recommendation Constraints
11. Generate 5 recommendations in the "recommendations" array. Only reduce to 4 if the page is near-perfect in one category, or 3 if the page excels in multiple areas. Default to 5.
12. Every recommendation MUST be directly grounded in your analysis findings — never generic advice.
13. Prioritize by impact: priority 1 = highest impact, must-fix; priority 2 = significant improvement; priority 3 = nice-to-have optimization.
14. The "grounded_metric" field must cite the exact data point (e.g., "4 images missing alt text", "Meta title is 78 chars — exceeds 60-char ideal").
15. The "action" field must be a specific, implementable step — not vague advice.
16. The "expected_impact" field must describe the concrete expected outcome.
17. Focus recommendations on the lowest-scoring categories first.
</constraints>

<scoring_rubric>
- 9-10: Exceptional — best practices exceeded, clear competitive advantage
- 7-8: Good — solid foundation with minor improvements possible
- 5-6: Average — functional but missing key optimizations that impact rankings/conversions
- 3-4: Below average — significant gaps that hurt performance
- 1-2: Critical — fundamental issues that need immediate attention
</scoring_rubric>

<output_format>
Return a single JSON object with:
1. Scores and detailed analysis for each of the 5 categories (structure, messaging, CTAs, content depth, UX)
2. A "recommendations" array with 5 prioritized, actionable recommendations grounded in your analysis (reduce to 4 or 3 only if the page truly excels)
All in one structured response matching the provided schema.
</output_format>
User Prompt → gemini-2.5-flash
<context>
## Extracted Page Metrics (Deterministic — scraped from HTML)

### Content Metrics
- Word Count: 821
- CTA Count: 45
- Internal Links: 53
- External Links: 3

### Image & Visual Media
- Total Images (<img>): 60
- Images Missing Alt Text: 0 (0.0%)
- Images with Decorative Alt (alt=""): 55
- Rich Visual Media: 2 SVG elements, Video embeds detected, CSS animations/transitions detected, WebGL/3D elements detected

### Technical SEO
- Meta Title: B2B Digital Agency for Enterprises | eight25 (44 chars — ideal: 50-60)
- Meta Description: Global B2B digital agency offering enterprise web design, mobile apps, and strategic consulting for Fortune 500 firms. (118 chars — ideal: 120-160)
- Viewport Meta: Present
- Canonical URL: Present
- Robots Meta: Present
- Open Graph Tags: Present
- Twitter Card: Present
- Structured Data (JSON-LD): None

### Heading Structure
- Heading Counts: {"h1": 1, "h2": 5, "h3": 10, "h4": 0, "h5": 0, "h6": 0}

## Heading Hierarchy (order as found in HTML)
[["H1", "Digital experiences for the modern enterprise"], ["H2", "The world\u2019s best companies"], ["H2", "choose to work with eight25"], ["H3", "Google"], ["H3", "Qlik"], ["H3", "Intralinks"], ["H3", "Andela"], ["H3", "Qualcomm"], ["H2", "Insights"], ["H3", "Analyzing the \u2018Request a Demo\u2019 Page: Unpacking Why Conversions Are Lagging"], ["H3", "Uncovering Homepage Hero Friction: Why Visitors Bounce and How to Fix It"], ["H3", "Why Is Brand Alignment Important For B2B Enterprise Websites?▼ Show full prompt (9,062 chars)
Raw JSON Output
{
  "structure_score": 6,
  "messaging_score": 8,
  "cta_score": 5,
  "content_depth_score": 8,
  "ux_score": 7,
  "overall_score": 7,
  "structure_analysis": {
    "score": 6,
    "findings": "The page has a clear H1 and a well-structured heading hierarchy with no level skips (H1 -> H2 -> H3). Basic technical SEO elements like viewport meta, canonical URL, robots meta, Open Graph tags, and Twitter Card are all present. However, a significant gap exists with the complete absence of Structured Data (JSON-LD). Furthermore, while no images are technically 'missing' alt text, 55 out of 60 images (91.7%) use decorative alt text (alt=\"\"), which is a missed SEO opportunity for image indexing and an accessibility failure. The meta title, at 44 characters, is slightly below the ideal 50-60 character range.",
    "evidence": "Heading Counts: {\"h1\": 1, \"h2\": 5, \"h3\": 10, \"h4\": 0, \"h5\": 0, \"h6\": 0}. Heading Hierarchy shows proper nesting. Technical SEO: Viewport Meta: Present, Canonical URL: Present, Robots Meta: Present, Open Graph Tags: Present, Twitter Card: Present, Structured Data (JSON-LD): None. Images Missing Alt Text: 0 (0.0%), Images with Decorative Alt (alt=\"\"): 55. Meta Title: B2B Digital Agency for Enterprises | eight25 (44 chars)."
  },
  "messaging_analysis": {
    "score": 8,
    "findings": "The page clearly communicates its value proposition as a 'B2B Digital Agency for Enterprises' that builds 'Digital experiences for the modern enterprise'. The brand voice is professional and directly targets enterprise clients, aligning well with likely search intent. Key messages, including the primary H1 and value proposition, are prominently displayed above the fold. The use of client logos like Google and Qualcomm immediately reinforces credibility. The only minor detractor is the highly prominent and detailed cookie consent banner that appears at the top, which can initially obscure the core messaging.",
    "evidence": "H1: 'Digital experiences for the modern enterprise'. Sub-headline: 'We build brands and web experiences that help you build the ultimate customer journey.' Section: 'The world’s best companies choose to work with eight25' with client logos (Google, Qlik, Intralinks, Andela, Qualcomm). Page Content excerpt shows a detailed cookie consent banner at the very top."
  },
  "cta_analysis": {
    "score": 5,
    "findings": "The page features a high number of Calls to Action (CTAs), with 45 CTAs for a word count of 821. While the language used for CTAs like 'Let’s talk', 'View all work', 'Read More', and 'Submit' is action-oriented and clear, the sheer quantity is excessive and likely to cause user fatigue or dilute the focus on primary conversion goals. Primary CTAs such as 'Let’s talk' are present above the fold, and a clear contact form with a 'Submit' button is available at the bottom of the page, indicating good placement for key actions.",
    "evidence": "CTA Count: 45. Word Count: 821. Examples of CTAs: 'Let’s talk' (top navigation), 'View all work', 'Read More' (under blog posts), 'Watch Video' (under success stories), 'Submit' (contact form)."
  },
  "content_depth_analysis": {
    "score": 8,
    "findings": "With a word count of 821, the page provides a solid overview for an enterprise B2B agency homepage. The content effectively covers various services (Brand, Creative, Technology, Growth), showcases client testimonials and success stories, and integrates 'Insights' (blog posts), demonstrating good topical coverage. The excellent use of 1 H1, 5 H2s, and 10 H3s significantly aids content organization and scannability. Strong E-E-A-T signals are present through mentions of 'Fortune 500 companies' and specific client logos. The page also features a healthy 53 internal links, supporting deeper exploration of the site's offerings.",
    "evidence": "Word Count: 821. Heading Counts: {\"h1\": 1, \"h2\": 5, \"h3\": 10}. Content sections include 'Services' (Brand, Creative, Technology, Growth), 'The world’s best companies choose to work with eight25', 'Insights', and 'Success stories…'. Internal Links: 53. Text: 'privileged to work with Fortune 500 companies'."
  },
  "ux_analysis": {
    "score": 7,
    "findings": "The page offers a visually rich and engaging experience, utilizing 2 SVG elements, video embeds, CSS animations/transitions, and WebGL/3D elements. The presence of a viewport meta tag indicates mobile-readiness. Content is logically organized with clear sections and subheadings, enhancing readability. However, a significant accessibility and user experience issue arises from 55 out of 60 images having decorative alt text (alt=\"\"), which hinders screen reader users. Additionally, the prominent and detailed cookie consent banner at the top of the page creates initial friction, requiring user interaction before the main content is fully accessible.",
    "evidence": "Rich Visual Media: 2 SVG elements, Video embeds detected, CSS animations/transitions detected, WebGL/3D elements detected. Viewport Meta: Present. Images with Decorative Alt (alt=\"\"): 55. Page Content excerpt shows a detailed cookie consent banner at the very top."
  },
  "recommendations": [
    {
      "priority": 1,
      "category": "seo",
      "title": "Enhance Image Alt Text for SEO and Accessibility",
      "description": "A vast majority of images (55 out of 60) currently use decorative alt text (alt=\"\"). This is a critical missed opportunity for SEO, as descriptive alt text helps search engines understand image content, and a significant accessibility barrier for users relying on screen readers.",
      "grounded_metric": "55 images with decorative alt (alt=\"\") out of 60 total images.",
      "action": "Audit all images and replace decorative alt text with descriptive, keyword-rich alt text for all meaningful images. Only use alt=\"\" for truly decorative images that convey no information.",
      "expected_impact": "Improve image search visibility, enhance overall page SEO, and significantly improve accessibility for users with visual impairments, contributing to a better user experience and compliance."
    },
    {
      "priority": 1,
      "category": "seo",
      "title": "Implement Structured Data (JSON-LD)",
      "description": "The page currently lacks any structured data markup. Implementing relevant JSON-LD schema is crucial for an enterprise B2B agency to help search engines better understand the organization, its services, and its offerings, potentially leading to rich results in SERPs.",
      "grounded_metric": "Structured Data (JSON-LD): None.",
      "action": "Implement Organization schema, Service schema, and potentially LocalBusiness schema (if applicable) using JSON-LD to provide explicit information about eight25 and its services to search engines.",
      "expected_impact": "Increase visibility in search engine results pages (SERPs) through rich snippets, improve click-through rates, and enhance search engine understanding of the business's core offerings and authority."
    },
    {
      "priority": 2,
      "category": "cta",
      "title": "Optimize CTA Quantity and Focus",
      "description": "The page features an excessive number of CTAs (45 for 821 words), which can overwhelm users and dilute the effectiveness of primary calls to action. While individual CTA language is good, the sheer volume can lead to decision paralysis and lower conversion rates.",
      "grounded_metric": "CTA Count: 45 for a Word Count: 821.",
      "action": "Conduct a comprehensive audit of all CTAs. Consolidate or remove redundant CTAs, ensure primary CTAs are visually distinct and strategically placed, and guide users more clearly towards key conversion goals without excessive options.",
      "expected_impact": "Reduce user fatigue, clarify the primary conversion paths, and increase the likelihood of users taking desired actions, ultimately improving conversion rates."
    },
    {
      "priority": 2,
      "category": "ux",
      "title": "Refine Cookie Consent Banner Presentation",
      "description": "The current cookie consent banner is highly prominent and detailed, appearing at the top of the page and requiring user interaction before the main content is fully accessible. This can create initial friction and detract from the immediate value proposition.",
      "grounded_metric": "Prominent cookie consent banner with extensive detail at the top of the page.",
      "action": "Explore alternative, less intrusive designs for the cookie consent banner, such as a smaller bar at the bottom of the screen or a more concise initial message, while ensuring full compliance with privacy regulations.",
      "expected_impact": "Improve the initial user experience by reducing friction, allowing immediate access to the core content and value proposition, and enhancing the perceived professionalism of the website."
    },
    {
      "priority": 3,
      "category": "seo",
      "title": "Optimize Meta Title Length",
      "description": "The current meta title is 44 characters, which is slightly shorter than the ideal range of 50-60 characters. While not a critical issue, optimizing its length can improve its effectiveness in search results.",
      "grounded_metric": "Meta Title: B2B Digital Agency for Enterprises | eight25 (44 chars — ideal: 50-60).",
      "action": "Expand the meta title to be between 50-60 characters by adding a concise, high-value keyword or a unique selling proposition relevant to enterprise B2B services.",
      "expected_impact": "Enhance search engine visibility and click-through rates by providing a more descriptive and fully optimized title that captures user attention in search results."
    }
  ]
}