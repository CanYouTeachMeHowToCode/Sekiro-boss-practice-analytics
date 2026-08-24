# Sekiro-boss-practice-analytics
A web app for tracking *Sekiro: Shadows Die Twice* boss attempts, mistakes, and player improvement over time.

### Why This Tool
Sekiro players often struggling on various bosses (Genichiro, Isshin, Owl (Father), Corrupted Monk, etc.), yet most players don't have a structured way to understand:
- which boss attacks/skills cause the most deaths
- whether they are actually improving
- which phase is the main bottleneck
- how many attempts it takes to defeat each boss

This tool serves as an analysis on user's attempts on each boss fights in Sekiro. Specifically, the tool analyses user's action performance during the boss fights and provide targeted identification of the user's strengths and weaknesses regarding the boss's moveset.

#### V1
V1 is a manual boss-attempt tracking and failure analytics tool: players record how far they reached and what ended each attempt, and the app identifies their most common failure moves and bottleneck phases.

### Core Features

- Browse Sekiro bosses
- Record boss attempts
- Record the attack/mistake causing failure
- View attempt history
- View progress analytics
- View failure breakdown by boss move


### Tech Stack (V1.0)

- Backend: FastAPI
- ~~Database: PostgreSQL~~ Version 1 only focus on a few specific bosses' attacks/skills, should be <1000 data rows, json files enough to hold (will possibly add database to framework in V2)
- Frontend: React + TypeScript
- Deployment: Docker