# Documentation Image Generation Prompts
## Task: DES-M-0110
## Mission: dark-nexus (Aine - Designer)
## Date: 2026-02-28

---

## Style Guidelines

Based on existing site-nine imagery:

- **Color palette**: Purple (#8B5CF6 / similar), white, black, gray accents
- **Tech aesthetic**: Modern, clean, professional
- **Logo style**: Flat design, badge-like, tech-forward
- **Diagram style**: Clean flowcharts with purple accents, dark backgrounds
- **Consistency**: Match existing s9 logo visual language

---

## Image 1: Epic Lifecycle Diagram

**Filename**: `epic-lifecycle.png`

**Target Documentation**: `docs/source/epics.md` (Epic statuses section)

**Purpose**: Visualize how epic statuses transition based on subtask states

**Prompt**:
```
Create a professional flowchart diagram showing epic status transitions for a software project management system. Use a dark background with purple (#8B5CF6) and white elements matching a modern tech aesthetic.

Show 4 status nodes in rounded rectangles:
- TODO (📋 icon, blue-gray color)
- UNDERWAY (🚧 icon, purple color) 
- COMPLETE (✅ icon, green color)
- ABORTED (❌ icon, red color)

Connect with labeled arrows showing transitions:
- TODO → UNDERWAY: "Any subtask starts"
- UNDERWAY → COMPLETE: "All subtasks complete"
- UNDERWAY → TODO: "All active tasks done, only TODO remain"
- Any status → ABORTED: "Manual abort" (dashed line)

Add note: "COMPLETE and ABORTED are terminal states (no transitions out)"

Style: Clean, minimal, professional diagram with purple accent color (#8B5CF6), dark background, clear typography, technical documentation quality.
```

---

## Image 2: Mission Lifecycle Diagram

**Filename**: `mission-lifecycle.png`

**Target Documentation**: `docs/source/agents/missions.md` (Mission Lifecycle section)

**Purpose**: Show the complete lifecycle of an agent mission from start to end

**Prompt**:
```
Create a horizontal timeline flowchart showing an agent mission lifecycle for an AI-powered development system. Use dark background with purple (#8B5CF6) and white elements.

Show 5 main stages from left to right:

1. **START** (circle node, purple glow)
   - Label: "Summon Agent"
   - Details: "Select role, assign persona, generate codename"

2. **ACTIVE** (rounded rectangle, bright purple)
   - Label: "Mission Active" 
   - Details: "Work on tasks, document progress"
   - Icon: 🎯

3. **IDLE** (rounded rectangle, dimmed purple)
   - Label: "Mission Idle"
   - Details: "Paused, waiting for continuation"
   - Icon: ⏸️
   - Bidirectional arrow to ACTIVE: "Resume/Pause"

4. **HANDOFF** (diamond decision node, yellow/orange)
   - Label: "Hand Off?"
   - Two paths: "Yes" → creates handoff document, "No" → proceeds to end

5. **COMPLETE** (circle node, green)
   - Label: "Mission Complete"
   - Details: "Document outcomes, close session"
   - Icon: ✅

Style: Modern tech flowchart, purple accents (#8B5CF6), dark background, clean arrows, professional typography, matches site-nine branding.
```

---

## Image 3: Agent System Overview

**Filename**: `agent-system-overview.png`

**Target Documentation**: `docs/source/agents/overview.md` (The Agent System section)

**Purpose**: Illustrate how missions, roles, and personas interconnect

**Prompt**:
```
Create a conceptual diagram showing the three-tier agent system architecture. Use dark background with purple (#8B5CF6) gradients and white text, modern tech aesthetic.

Show three overlapping circular sections forming a Venn diagram style:

**Left Circle - MISSIONS** (Purple glow)
- Icon: 📋
- Label: "Missions"
- Text: "Discrete work sessions"
- Sub-text: "Operation silver-titan"
- Sub-text: "Unique codename"

**Right Circle - ROLES** (Blue-purple glow)
- Icon: 👤
- Label: "Roles" 
- Text: "Specialized expertise"
- List: "Engineer, Architect, Tester..."

**Bottom Circle - PERSONAS** (Pink-purple glow)
- Icon: 🎭
- Label: "Personas"
- Text: "Mythological identities"
- Examples: "Hephaestus, Thoth, Athena..."

**Center Intersection** (Bright white glow):
- Large icon: ⚡
- Text: "Active Agent Session"
- Example: "Fukurokuju (Documentarian) on Operation silver-titan"

Add connecting lines showing relationships between all three elements.

Style: Modern, glowing tech visualization, purple color scheme (#8B5CF6), dark background, professional and clean, suitable for technical documentation.
```

---

## Image 4: Directory Structure Visualization

**Filename**: `opencode-directory-tree.png`

**Target Documentation**: `docs/source/structure.md` (Directory Overview section)

**Purpose**: Visual representation of .opencode directory structure with color-coded safety indicators

**Prompt**:
```
Create a clean directory tree visualization for technical documentation. Dark background with purple (#8B5CF6) accents and monospace font.

Show file tree structure with color-coded safety indicators:

.opencode/
├── 📄 README.md [GREEN - Safe to edit]
├── 📁 data/ [RED - Do not touch]
│   └── project.db [RED indicator]
├── 📁 guides/ [GREEN - Safe to edit]
│   └── PERSONAS.md
├── 📁 procedures/ [GREEN - Safe to edit]
│   ├── COMMIT_GUIDELINES.md
│   └── TASK_WORKFLOW.md
├── 📁 missions/ [YELLOW - Read-only]
├── 📁 tasks/ [YELLOW - Read-only]
└── 📁 work/ [YELLOW - Auto-managed]
    └── missions/

Include legend at bottom:
🟢 GREEN - Safe to edit (customize for your team)
🟡 YELLOW - Read-only (view but don't edit)
🔴 RED - Do not touch (database files)

Style: Clean monospace tree diagram, purple accent color (#8B5CF6), dark background, clear color coding with legend, technical documentation quality, matches site-nine aesthetic.
```

---

## Next Steps

1. **Review with Director**: Present these prompts for approval and refinement
2. **Generate images**: Use approved prompts with AI image generation tools (Gemini, ChatGPT, etc.)
3. **Refine if needed**: Iterate based on generated output quality
4. **Add to docs**: Place in `docs/source/images/` with descriptive filenames
5. **Update markdown**: Add image references to relevant documentation pages

---

## Notes

- All prompts emphasize purple (#8B5CF6) to match site-nine branding
- Dark backgrounds consistent with existing logo design
- Professional, clean aesthetic suitable for technical documentation
- Each image serves a specific educational purpose in the docs
