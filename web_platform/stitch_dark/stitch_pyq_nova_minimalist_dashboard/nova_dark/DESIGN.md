---
name: Nova Dark
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#c1c6d6'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#8b909f'
  outline-variant: '#414754'
  surface-tint: '#adc7ff'
  primary: '#adc7ff'
  on-primary: '#002e68'
  primary-container: '#1a73e8'
  on-primary-container: '#ffffff'
  inverse-primary: '#005bc0'
  secondary: '#40e56c'
  on-secondary: '#003912'
  secondary-container: '#02c953'
  on-secondary-container: '#004d1b'
  tertiary: '#c0c1ff'
  on-tertiary: '#1000a9'
  tertiary-container: '#6265f0'
  on-tertiary-container: '#ffffff'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc7ff'
  on-primary-fixed: '#001a41'
  on-primary-fixed-variant: '#004493'
  secondary-fixed: '#69ff87'
  secondary-fixed-dim: '#3ce36a'
  on-secondary-fixed: '#002108'
  on-secondary-fixed-variant: '#00531e'
  tertiary-fixed: '#e1e0ff'
  tertiary-fixed-dim: '#c0c1ff'
  on-tertiary-fixed: '#07006c'
  on-tertiary-fixed-variant: '#2f2ebe'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-max: 1280px
  gutter: 24px
  margin-desktop: 40px
  margin-mobile: 20px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

This design system is a high-fidelity, dark-mode evolution focused on depth, precision, and technological sophistication. It targets a modern, tech-forward audience who values focus and visual comfort during extended usage sessions.

The style is **Corporate / Modern** with a slight lean into **Glassmorphism**. It utilizes a deep slate palette to reduce eye strain while employing "Electric Blue" and "Success Green" as high-energy focal points. The aesthetic is defined by its expansive 24px corner radii, creating a soft, approachable silhouette that contrasts against the sharp, technical nature of the typography and the deep background. The overall emotional response should be one of "calm authority" and "premium performance."

## Colors

The palette is anchored in a deep charcoal/slate environment to provide maximum contrast for functional elements.

- **Background & Surface:** The base layer is `#0F172A`. Content surfaces and cards use `#1E293B` to create a clear visual hierarchy.
- **Primary:** "Electric Blue" (`#1A73E8`) is used for primary actions and brand presence. In this dark context, it acts as a luminous beacon.
- **Success:** `#00C853` is reserved for positive states and completion indicators, echoing the green found in the logo.
- **Typography:** Headlines and primary labels use pure white (`#FFFFFF`) for maximum legibility. Secondary information uses a muted silver-gray (`#94A3B8`) to establish clear information hierarchy.

## Typography

This design system exclusively uses **Plus Jakarta Sans** to maintain a modern and optimistic feel. The type scale is designed for high readability against dark backgrounds, using generous line heights to prevent text "crowding."

- **Hierarchy:** Use `Bold` (700) for large headlines to emphasize the brand's geometric personality. `SemiBold` (600) is preferred for UI labels and button text to ensure they stand out against the deep surface colors.
- **Accessibility:** Never use a font weight lighter than 400 for body text on dark backgrounds to avoid "thining" effects caused by light bleed.
- **Scaling:** On mobile devices, `headline-lg` should downscale to 24px to ensure headers do not wrap excessively.

## Layout & Spacing

The design system utilizes a **Fixed Grid** model for desktop and a **Fluid** model for mobile.

- **Grid:** A 12-column grid is standard for desktop (1280px max-width).
- **Rhythm:** An 8px base unit drives all spacing decisions.
- **Breakpoints:**
  - **Mobile:** < 600px (4 columns, 20px margins).
  - **Tablet:** 600px - 1024px (8 columns, 32px margins).
  - **Desktop:** > 1024px (12 columns, 40px margins).
- **Sidebar:** The navigation sidebar is fixed at 280px on desktop, utilizing the `surface` color to separate it from the main `background` canvas.

## Elevation & Depth

In this dark-mode environment, depth is communicated through **Tonal Layering** supplemented by subtle **Luminous Glows** rather than traditional black shadows.

- **Level 1 (Base):** `#0F172A` - The primary canvas.
- **Level 2 (Cards/Sidebar):** `#1E293B` - Elevated surfaces. These should include a subtle 1px inner border (stroke) of `#334155` to define edges against the background.
- **Level 3 (Popovers/Modals):** `#334155` - Floating elements. These utilize a soft ambient glow: `0px 10px 30px rgba(0, 0, 0, 0.5)` with a very subtle primary-tinted outer glow `0px 0px 15px rgba(26, 115, 232, 0.1)`.
- **Interactions:** Hover states on cards should slightly brighten the surface color and increase the intensity of the blue-tinted outer glow.

## Shapes

The signature of this design system is its generous, friendly roundedness.

- **Main Components:** Cards, Modals, and Sidebar containers use a **24px (1.5rem)** corner radius (`rounded-xl`).
- **Interactive Elements:** Buttons and Input fields use a **12px (0.75rem)** radius to maintain a distinct but related language.
- **Small Elements:** Tooltips and tags use a **6px (0.375rem)** radius.
- **Visual Harmony:** The 24px radius on large containers creates a "bubble" effect that softens the technical nature of the dark UI.

## Components

- **Buttons:** Primary buttons use a solid Electric Blue (`#1A73E8`) background with White text. Secondary buttons use a ghost style with a `#334155` border and White text.
- **Input Fields:** Use the Surface color (`#1E293B`) for the fill, with a 1px border of `#334155`. On focus, the border transitions to Electric Blue with a subtle outer glow.
- **Cards:** Cards must feature the 24px corner radius and a 1px subtle border. Content inside cards should follow the 24px padding rule to match the corner radius.
- **Chips/Tags:** Use Success Green (`#00C853`) with 10% opacity for backgrounds and 100% opacity for text to create a high-contrast, accessible "Success" state.
- **Sidebar Navigation:** Active states should be indicated by a vertical Electric Blue bar on the left edge and a subtle background tint (`rgba(26, 115, 232, 0.1)`).
- **Logo Integration:** The PYQ Nova logo should be placed in the top-left of the sidebar. In dark mode, ensure the "Nova" text portion is white to maintain contrast against the slate sidebar.