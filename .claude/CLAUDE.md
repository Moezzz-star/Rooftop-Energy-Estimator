# Rooftop Energy Estimator — Project Instructions

## /pipeline shortcut

When the user types `/pipeline` without additional text, execute the following automatically:

1. Read `prompt.md` from the project root.
2. Invoke the `engineering-manager` agent with the content below as the prompt.

Use this exact invocation template — do NOT pass the raw `prompt.md` to every sub-agent.
Instead, pass the **Section Manifest** so the engineering manager can slice context per agent.

---

## Engineering Manager Invocation Template

```
You are running the autonomous engineering pipeline for the Rooftop Energy Estimator project.

The full specification is in `prompt.md` at the project root.
Do NOT paste the full spec into every agent prompt — it is 1876 lines and will exhaust the token budget.

## Token optimization rules (MANDATORY)

1. Read `prompt.md` once at the start. Build a section index in memory.
2. When delegating to any agent, pass ONLY the sections listed in the Section Manifest below for that agent type.
3. Reference sections by their heading (e.g. "Section 4 – Technology stack") and paste only that section's text.
4. Never paste the full spec into any agent prompt.
5. Agents that need cross-cutting context (security, architecture) get their own sections + Section 5 (Architecture principles) only.
6. For progress reports, use the compact format from Section 36 of the spec.
7. Read only files relevant to the current phase — use grep/glob before opening files.
8. Patch files; never regenerate a complete file when a diff suffices.

## Section Manifest

### product-manager
Sections: 1 (Core objective), 7 (Primary user workflow), 31 (Implementation phases), 32 (Scope prioritization), 34 (Definition of done)

### product-analyst
Sections: 1, 8 (UI/UX), 9 (Required screens), 7

### business-analyst
Sections: 1, 2 (Existing ML pipeline), 3 (Zero-cost constraint), 12 (Geospatial correctness), 15 (Solar calculations), 16 (Shading), 22 (Privacy), 33 (Anti-overengineering)

### solution-architect
Sections: 3, 4 (Tech stack), 5 (Architecture principles), 6 (Repository structure), 17 (Async orchestration), 26 (Local development), 27 (CI/CD), 28 (Deployment)

### software-architect
Sections: 4, 5, 6, 13 (Inference pipeline), 14 (Training pipeline), 15, 18 (Database model), 19 (REST API), 36 (Token/execution efficiency)

### backend-engineer
Sections: 4, 5, 13, 14, 15, 17, 18, 19, 21 (Auth/security), 23 (Observability), 30 (Performance)

### frontend-engineer
Sections: 4, 8, 9, 10 (Maps/geocoding), 24 (Testing — frontend), 30

### python-engineer
Sections: 2, 4, 13, 14, 15, 16, 36

### database-engineer
Sections: 4, 12, 17, 18

### api-engineer
Sections: 4, 19, 21

### uiux-engineer
Sections: 8, 9, 10

### devops-engineer
Sections: 4, 26, 27, 28

### security-engineer
Sections: 11 (Imagery handling), 21, 22, 23

### qa-engineer
Sections: 24 (Testing), 25 (Sample demo), 34

### performance-engineer
Sections: 13, 17, 30

### observability-engineer
Sections: 23, 26

### documentation-engineer
Sections: 29 (Documentation), 34, 37 (Final report)

### release-manager
Sections: 26, 27, 28, 34, 37

## Existing repository state

The repository already contains:
- Jupyter notebooks for SR, segmentation training, inference, and PV estimation
- Trained model: `unet_buildings.keras`
- Training config: `segmentation_training_config.json`
- `threshold_search.csv`

Start with Phase 1 (repository assessment) by reading the notebooks and model config,
then proceed through the phases defined in Section 31 of the spec.

Do not ask for confirmation between phases unless a genuine blocker exists.
```
