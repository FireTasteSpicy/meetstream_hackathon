## Core Components

### 1. Orchestration Layer

- **Prompt Manager**: Processes natural language inputs and routes them to appropriate services.
  - Uses Google's Gemini AI model for intelligent processing
  - Maintains conversation context through the `Conversation` model

- **Memory System**: Stores user preferences, conversation history, and learned patterns.
  - `MemoryPersonalityController`: Manages contextual memory and adjusts AI responses
  - `Memory` model: Stores long-term user-specific information

- **Decision Engine**: Determines appropriate actions for user inputs.
  - Supports multiple action types (direct responses, clarification, suggestions)
  - Uses context to customize responses

### 2. Context Builder

- **Activity Tracking**: Monitors developer actions across platforms.
  - `ActivityTracker`: Records events like commits, PRs, issues
  - `ActivityEvent` model: Stores structured activity data

- **Correlation**: Identifies relationships between different activities.
  - `ActivityCorrelator`: Links related work across platforms (e.g., commits to issues)
  - Analyzes user workflow patterns

- **Code Analysis**: Evaluates code quality and complexity.
  - Uses tools like Radon for Python code analysis
  - Provides suggestions for code improvements

### 3. Integrations

- **GitHub**: Connects with GitHub repositories and events.
  - Webhook handler for real-time event processing

- **Jira**: Interacts with Jira ticketing system.
  - API integration for issue tracking
  - Webhook support for event-driven updates

### 4. Output Generators

- **Standup Generator**: Creates daily standup reports.
  - Summarizes yesterday's and today's activities
  - Identifies and reports blockers

- **Follow-up Generator**: Creates personalized follow-up summaries.
  - Tracks commitments and pending work
  - Suggests next actions

- **Digest Generator**: Produces team-level summaries.
  - Aggregates team activity
  - Highlights key metrics and blockers

## Technologies Used

1. **Backend Framework**: Django (Python) with Django REST Framework
2. **Database**: SQLite (for development, easily swappable with PostgreSQL)
3. **AI Integration**: Google Generative AI (Gemini model)
4. **Version Control**: Git
5. **Authentication**: Django token-based auth
6. **External APIs**: GitHub API, Jira API

## Functionality Flow

1. **Data Collection**:
   - Webhooks receive real-time events from GitHub and Jira
   - Activities are tracked and stored in structured format

2. **Data Processing**:
   - Activities are correlated across platforms
   - Code is analyzed for quality and complexity
   - User patterns and workflows are identified

3. **User Interaction**:
   - Users can ask natural language questions via the prompt manager
   - Decision engine determines appropriate responses
   - Memory system provides context for personalized interaction

4. **Output Generation**:
   - Automated standup reports summarize recent work
   - Follow-ups track commitments and provide reminders
   - Team digests provide higher-level overview

## Desired Outputs

1. **Standup Reports**: Markdown-formatted summaries of:
   - Yesterday's activities (commits, PRs, issues)
   - Today's planned work
   - Current blockers

2. **Follow-up Summaries**: Personalized insights including:
   - Recent activities
   - Pending commitments
   - Related work
   - Suggested actions

3. **Team Digests**: Aggregated team performance with:
   - Member-by-member activity summaries
   - Recent PRs and issues
   - Identified blockers

4. **AI-Driven Responses**: Natural language answers to questions about:
   - Project status
   - Pending work
   - Development insights

## Architecture

PulseBot follows a modular Django application structure with clear separation of concerns:
- Core services handle fundamental application logic
- Integrations connect to external platforms
- Context builders analyze and correlate information
- Output generators produce formatted summaries

The system is designed to be extensible, allowing new integrations and output formats to be added with minimal changes to the core architecture.