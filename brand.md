# Brand: TauNet

Status: active. Direction supplied by the user: Industrial.

The website is a continuous cool-grey instrument chassis. Raised navigation keys and controls surround recessed dark displays. Small orange details indicate actions; real outcomes retain semantic green, red, and slate, always with text labels. Decorative hardware remains still and subordinate to the content.

## Typography

Host Grotesk, locally served as Industrial Host, for headings and reading. IBM Plex Mono, locally served as Industrial Plex, for brief labels and metadata. Headings use tight tracking and compact leading. Body text uses 16px or 17px with comfortable line spacing.

## Palette

- Chassis: #cbd0d2
- Raised: #e7eaeb
- Well: #b6bec2
- Ink: #181e22
- Labels: #414b52
- Field: #20272b
- On field: #f2f4f4
- Muted on field: #d8dee1
- Accent: #f15b22

Authoritative CSS variables and compatibility aliases live in web/src/tokens.css. The cool-grey chassis stays consistent across system color preferences, with dark surfaces reserved for inset displays. Maintain AA contrast, visible focus, keyboard interaction, responsive layouts, and reduced motion.

## Voice

Preserve the existing product copy. Describe actual robot tasks, replay verification, and data clearly. Do not fabricate operational states or network numbers.

## References and media

Layout reference: https://axisrobotics.ai/

web/public/media/teleoperation.mp4 is reference footage downloaded from https://axisrobotics.ai/media/bottleneck-card-2.mp4 at the user's direction. Its local grayscale poster is derived from the same clip. The landing page identifies the footage as a reference and credits Axis Robotics; it does not represent the TauNet simulator. Playback is user initiated.

The HTML pitch deck in docs/deck/project/slides/verification.html references image and video blobs that are absent from the repository. Replace the reference film and poster with original presentation media once available, keeping dimensions, subject containment, captions, and accessible controls.

Fonts are locally hosted from Google Fonts. Their SIL Open Font License files are included in web/public/fonts.
