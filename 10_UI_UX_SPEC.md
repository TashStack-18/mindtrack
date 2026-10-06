# MindTrack — UI/UX Specification

## Design direction
Calm, private, modern and minimal.

Avoid:
- overly clinical hospital styling
- childish wellness graphics
- excessive gradients
- excessive animations
- gamification that pressures users to journal

## Suggested visual language
### Colors
Use a restrained palette:
- deep navy/charcoal for primary text
- soft lavender/indigo accent
- warm off-white background
- muted green for positive states
- muted amber for attention
- muted red only for destructive actions

Keep semantic colors accessible.

## Typography
Recommended:
- Inter
- Plus Jakarta Sans

Use one primary font family.

## Layout
Desktop:
- left sidebar
- main content
- optional insight panel

Mobile:
- top bar
- bottom navigation or compact menu

## Navigation
- Dashboard
- Journal
- Insights
- Reflection
- Reports
- Privacy

## Dashboard hierarchy
1. Today's mood
2. Write entry
3. Mood trend
4. Recent insight
5. Reflection
6. Recent entries

## Journal editor
Keep the writing area dominant.

Suggested layout:
```text
-----------------------------------------
How are you feeling today?

Mood:  ○ 1 ○ 2 ○ 3 ○ 4 ○ 5

Mood label: [________]

What happened today?
┌─────────────────────────────────────┐
│                                     │
│                                     │
└─────────────────────────────────────┘

Context:
[Academics] [Sleep] [Friends] [+ Add]

              [Save Entry]
-----------------------------------------
```

## Insight design
Use an "Insight" card:
- short headline
- one-sentence observation
- "Why am I seeing this?" expandable detail

## Charts
Use charts only when they answer a question.

Recommended:
- line chart for mood over time
- line chart for sentiment over time
- bar chart for context averages

Do not overload one screen with charts.

## Empty states
Example:
> Your mood history will appear here after you record a few entries.

CTA:
**Write your first entry**

## Error states
Never show raw Python exceptions.

Example:
> We couldn't save your entry. Please try again.

## Accessibility
- keyboard navigation
- visible focus states
- semantic labels
- adequate contrast
- chart alternatives in text
- avoid color-only meaning

## Privacy cues
Show subtle indicators:
- "Encrypted"
- "Private"
- "You control exports"

Do not create fear-based security messaging.

## Responsive requirements
Test:
- 1440px desktop
- 1024px laptop/tablet
- 768px tablet
- 390px mobile
