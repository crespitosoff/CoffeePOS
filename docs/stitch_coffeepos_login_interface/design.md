# Design System Document: The Elevated Harvest

## 1. Overview & Creative North Star
This design system is built to transform the transactional nature of a POS into a sensory experience that mirrors the craftsmanship of "Tiendas de Promisión Huila." We move away from the rigid, sterile grids of legacy retail software toward a **"High-Altitude Editorial"** aesthetic. 

Our Creative North Star is **The Organic Curator**. The UI should feel like a premium coffee journal—tactile, warm, and spacious. We achieve this by breaking the traditional "box-in-a-box" layout, utilizing intentional asymmetry, overlapping elements that mimic stacked paper, and a typography scale that prioritizes readability without sacrificing elegance. Every interaction must feel as smooth and intentional as a slow-pour extraction.

---

## 2. Colors: Tonal Depth & The "No-Line" Rule
The palette is rooted in the rich soils and vibrant cherries of Huila. We use color not just for decoration, but as the primary architectural tool.

*   **Primary (`#9b4100`):** Our roasted espresso tone. Use this for high-impact actions and brand presence.
*   **Secondary (`#7a5730`):** A warm caramel used for functional accents and secondary navigation.
*   **The "No-Line" Rule:** To maintain a high-end feel, **1px solid borders are strictly prohibited** for sectioning. Structural boundaries must be defined solely through background color shifts. For example, a `surface-container-low` section should sit directly against a `surface` background to create a "carved" look.
*   **Surface Hierarchy & Nesting:** Treat the UI as a physical stack of materials. 
    *   Use `surface-container-lowest` for the base canvas.
    *   Use `surface-container-high` for interactive elements like order cards.
    *   Nested containers must always move toward "lighter" or "higher" tones to indicate proximity to the user.
*   **The Glass & Gradient Rule:** For floating modals or "quick-view" overlays, utilize **Glassmorphism**. Apply `surface-variant` with a 60% opacity and a `20px` backdrop-blur. 
*   **Signature Textures:** Main CTAs (e.g., "Complete Sale") should use a subtle linear gradient from `primary` to `primary-container`. This adds a "backlit" soul to the button that flat colors cannot replicate.

---

## 3. Typography: The Editorial Voice
We utilize a sophisticated pairing of **Plus Jakarta Sans** for character and **Inter** for precision.

*   **Display & Headlines (Plus Jakarta Sans):** These are our "Brand Moments." Use `display-lg` for welcome screens and `headline-md` for category titles. The generous x-height feels modern and friendly.
*   **Body & Labels (Inter):** Reserved for technical data—SKUs, prices, and quantities. Inter provides the legibility required for high-speed POS environments.
*   **Hierarchy as Identity:** Use a high-contrast scale. A large `headline-lg` paired with a significantly smaller `label-md` creates an editorial look that feels designed, not just "inputted."

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are often messy. In this system, we convey hierarchy through **Tonal Layering** first, and light second.

*   **The Layering Principle:** Place a `surface-container-lowest` card on a `surface-container-low` section. The slight shift in hex value creates a "soft lift" that is easier on the eyes than a shadow.
*   **Ambient Shadows:** When a floating effect is necessary (e.g., a dragged item), use extra-diffused shadows. 
    *   *Spec:* `0px 12px 32px rgba(21, 28, 39, 0.06)`. 
    *   The shadow should never be pure black; it must be a tinted version of the `on-surface` color.
*   **The Ghost Border:** If accessibility requires a stroke (e.g., in high-glare environments), use a "Ghost Border": `outline-variant` at **15% opacity**.
*   **Tactile Feedback:** Because this is a POS, "Depth" also applies to touch. When a button is pressed, it should "sink" by shifting from `surface-container-high` to `surface-container-low`, simulating a physical mechanical switch.

---

## 5. Components: Tactile-First primitives

### Buttons (The "Touch-Target" Standard)
*   **Primary:** `primary` fill, `on-primary` text. `xl` roundedness (`3rem`). Minimum height: `64px` for ergonomic thumb-tapping.
*   **Secondary:** `secondary-container` fill. Used for "Add-on" items (e.g., Extra Milk, Syrup).
*   **Tertiary:** No fill, `title-md` typography in `primary`. Used for "Cancel" or "Back" actions.

### Coffee Selection Cards
*   **Design:** Forbid divider lines. Use `surface-container` shifts to separate the product image from the description.
*   **Layout:** Use asymmetrical padding (e.g., `2rem` on the left, `1.5rem` on the right) to give the product list a modern, catalog feel.

### The "Order Tray" (List Component)
*   Instead of lines between items, use **Vertical White Space**. Items are grouped by a shared `surface-container-lowest` background. 
*   **Leading Elements:** Use `lg` roundedness (`2rem`) for item thumbnails to mimic the soft shape of a coffee bean.

### Input Fields
*   **Style:** Minimalist. No bottom line. Use a `surface-container-high` background with `md` roundedness. 
*   **Focus State:** Instead of a thick border, use a subtle `2px` glow using the `primary` color at 30% opacity.

---

## 6. Do’s and Don’ts

### Do
*   **Do** use "Breathing Room." Specialty coffee is about the pause; the UI should reflect that with generous margins.
*   **Do** lean into `xl` roundedness for buttons to make the POS feel approachable and "soft."
*   **Do** use `title-lg` for pricing. Money should be legible and prominent.

### Don’t
*   **Don’t** use pure black `#000000`. Use `on-background` (`#151c27`) to maintain the earthy, organic softness.
*   **Don’t** use standard "Information Blue" for alerts. Use the `tertiary` or `secondary` tokens to keep the palette grounded in the brand's world.
*   **Don’t** crowd the screen. If a screen feels full, use a "Glassmorphic" scroll fade at the bottom to indicate more content without adding heavy UI furniture.