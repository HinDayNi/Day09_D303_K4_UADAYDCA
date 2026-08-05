# Plan Writing Standard

Use this folder for implementation plans before large changes. Plans must be concrete enough that another engineer can implement them without deciding the scope again.

## Required Sections

- **Title**: Use a numbered filename, such as `001-land-law-rag-pipeline.md`.
- **Goal**: Explain the outcome in one short paragraph.
- **Scope**: List the exact data, files, features, and behavior included.
- **Out of Scope**: List what must not be built in this plan.
- **Input Files**: List source data and config files the implementation reads.
- **Output Files**: List generated files, indexes, reports, or persisted data.
- **Files To Write**: List code, docs, tests, scripts, and fixtures expected before implementation starts.
- **Step-By-Step Implementation**: Use bullet points. Each step must be small and direct.
- **Testing Plan**: Include unit tests, integration tests, and manual QA where relevant.
- **Acceptance Criteria**: Define how the task is considered complete.

## Style Rules

- Keep the plan bullet-point and step-by-step.
- Name exact files and folders when they affect implementation.
- Keep scope narrow and do not include unrelated refactors.
- Identify dependencies before adding them.
- Prefer testable pipeline milestones over broad descriptions.
- Include out-of-scope items to prevent accidental expansion.
- Every step need a checkbox point and checking when they are done.

## MVP Defaults

- Dataset scope starts with `dataset/luat_dat_dai_1.txt` only.
- No multi-document ingestion until a later plan.
- No reranker in Phase 1.
- No heavy OCR or encoding repair in Phase 1.
- No authentication or production UI in Phase 1.
