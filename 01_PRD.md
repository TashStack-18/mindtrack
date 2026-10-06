# MindTrack — Product Requirements Document

## 1. Product vision
MindTrack helps people privately record how they feel and what happened, then turns those records into understandable patterns and guided reflection.

## 2. Problem statement
Existing mood and wellness products commonly focus on one or more of:
- fast mood tracking
- journaling
- generic wellness exercises
- conversational AI
- charts and statistics

MindTrack combines these capabilities around a different core: **explainable, user-controlled reflection from the user's own journal data**.

Users should be able to answer:
- How have I been feeling?
- What topics or contexts appear when my mood changes?
- What does my recent journal data suggest?
- What can I reflect on?
- What information do I want to take to a counselor?

## 3. Goals
### Product goals
- Make daily journaling easy.
- Make mood history understandable.
- Provide explainable, non-diagnostic insights.
- Protect sensitive journal content.
- Encourage reflection rather than dependence on AI.
- Give users control over report/export content.

### Academic goals
Demonstrate:
- Python programming
- Flask web development
- database operations
- file/data handling
- sentiment analysis
- encryption
- visualization
- PDF generation
- authentication
- testing

## 4. Non-goals
MindTrack is NOT:
- a therapist
- a diagnostic system
- a crisis-response service
- a medical prediction engine
- a replacement for professional care
- an automatic data-sharing system

## 5. User stories

### Authentication
- As a user, I can create an account.
- As a user, I can log in securely.
- As a user, I can log out.
- As a user, I can delete my account and associated data.

### Journal
- As a user, I can create a journal entry.
- I can select a mood from 1–5.
- I can select an optional mood label.
- I can add optional context tags.
- I can edit and delete my own entries.
- I can search/filter entries.

### Analysis
- I can see sentiment polarity for an entry.
- I can see a human-readable sentiment label.
- I can see detected themes/tags.
- I can understand why an insight was generated.

### Analytics
- I can view mood trends.
- I can view sentiment trends.
- I can compare optional contexts with mood averages.
- I can view weekly reflections.

### Reflection
- I can receive a reflection prompt based on my selected mood and journal context.
- I can write a private reflection.
- I can dismiss a prompt.

### Reports
- I can select a date range.
- I can select what information is included.
- I can preview the report.
- I can export the report as PDF.
- Journal text must never be exported without explicit user selection.

## 6. Functional requirements

### FR-01 Authentication
Implement registration, login, logout, password hashing and session management.

### FR-02 Journal CRUD
Create, read, update and delete journal entries.

### FR-03 Mood capture
Mood score must be 1–5. Mood label is optional.

### FR-04 Context tags
Allow optional tags such as:
- Academics
- Sleep
- Friends
- Family
- Work
- Exercise
- Social
- Finance
- Other

Users may add custom tags.

### FR-05 Sentiment analysis
Run TextBlob on journal text and store:
- polarity
- subjectivity
- label

Do not present polarity as a clinical measurement.

### FR-06 Theme detection
For MVP, use a transparent keyword/category approach rather than an opaque model. Allow future replacement with an ML/NLP model.

### FR-07 Insight generation
Generate rule-based insights from:
- mood history
- sentiment history
- recurring tags
- recent entries

Insights must use cautious wording such as:
- "You mentioned..."
- "Your entries show..."
- "There appears to be an association..."
Never:
- "You have..."
- "You are suffering from..."
- "This proves..."

### FR-08 Reflection prompts
Select prompts based on mood/context. Prompts are reflection aids, not treatment.

### FR-09 Encryption
Journal content should be encrypted before storage. Encryption key must not be hard-coded into source code.

### FR-10 Analytics
Provide:
- daily/weekly mood trend
- sentiment trend
- mood distribution
- context vs mood summary

### FR-11 Counselor report
Generate a PDF containing only user-selected sections.

### FR-12 Data control
Provide:
- export
- delete entry
- delete account
- clear analytics/history

## 7. Non-functional requirements
- Responsive design
- Clear error states
- Accessible color contrast
- No sensitive data in logs
- Passwords never stored in plaintext
- Encryption secrets stored outside source code
- Server-side authorization on every private endpoint
- Basic test coverage for core services

## 8. Success criteria
MVP is complete when a user can:
1. Register.
2. Log in.
3. Create an encrypted journal entry.
4. Select a mood and context.
5. Receive TextBlob sentiment analysis.
6. See the entry in history.
7. View a mood chart.
8. Receive a reflection prompt.
9. Generate a user-selected PDF report.
10. Log out and log back in without losing data.

## 9. Future enhancements
- Better NLP theme extraction
- multilingual sentiment
- optional local/offline processing
- counselor portal with explicit consent
- advanced trend detection
- notification system
- PWA/mobile support
