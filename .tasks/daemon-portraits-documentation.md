# Task: Incorporate Daemon Portraits Throughout Documentation

**Priority:** High  
**Status:** Pending  
**Assigned To:** Documentarian (Nabu)  
**Created:** 2026-02-02

---

## Objective

Incorporate the 9 daemon agent portraits throughout the site-nine documentation with appropriate captions. Each portrait should appear only once. The front page (index.md) should only display the site-nine logo.

---

## Background

All 9 daemon portraits have been generated and are ready for integration:

| Image File | Daemon Name | Role | Description |
|------------|-------------|------|-------------|
| `argus.png` | Argus | Inspector | Watchful, analytical guardian with multiple glowing eyes - performs code reviews and security audits |
| `azazel.png` | Azazel | Builder | Creative craftsperson with circuit patterns - implements features and writes code |
| `mephistopheles.png` | Mephistopheles | Administrator | Commanding strategist with obsidian horns - coordinates projects and manages delegation |
| `kothar.png` | Kothar | Architect | Powerful designer with geometric tattoos - creates system designs and technical decisions |
| `eris.png` | Eris | Tester | Mischievous chaos-bringer with heterochromatic eyes - finds bugs and edge cases |
| `astarte.png` | Astarte | Designer | Elegant creator with shimmering eyes - designs UI/UX and user experiences |
| `nammu.png` | Nammu | Operator | Calm infrastructure maintainer with oceanic energy - handles deployment and operations |
| `nabu.png` | Nabu | Documentarian | Scholarly recorder with cuneiform patterns - writes documentation and guides |
| `mimir.png` | Mimir | Historian | Wise elderly scholar with ice-blue eyes - tracks history and maintains changelog records |

**Image Location:** All images are in `docs/source/images/` with **lowercase filenames** ✅

---

## Requirements

### 1. Front Page (index.md)
- **Add site-nine logo** as a header image
- **Do NOT add daemon portraits** - keep the front page clean and professional
- Logo file: `images/site-nine.png`

### 2. Daemon Portrait Placement
Each of the 9 daemon portraits must be incorporated **exactly once** throughout the documentation.

**Captions Must Include:**
- Daemon name (e.g., "Argus")
- Role (e.g., "Inspector")
- Very short description (1-2 sentences max)

**Caption Format Example:**
```markdown
![Argus - Inspector](images/argus.png){ width=300 }

*Argus, the Inspector daemon - Watchful guardian with multiple eyes who performs code reviews and security audits.*
```

### 3. Image Syntax
- Use standard Markdown: `![Alt text](images/filename.png)`
- Include sizing: `{ width=300 }` or `{ width=400 }` (attr_list extension is enabled)
- Center images when appropriate using figure tags
- Add italic caption text below each image

### 4. Placement Strategy

**Option A: Integrate into Existing Pages** (Recommended if brief)
- Spread portraits across usage.md, features.md, reference.md
- Place each portrait near where that role is discussed
- Keep captions brief (1-2 sentences)

**Option B: Create New Agent Roles Page** (Recommended if comprehensive)
- Create `docs/source/roles.md`
- Dedicate a section to each of the 8 primary roles (not Historian)
- Place Historian (Mimir) in reference.md near changelog section
- Provide detailed guidance on when to use each role
- Add to `mkdocs.yaml` navigation

### 5. Consistency
- Use consistent image sizing throughout (suggest `width=300` or `width=400`)
- Use consistent caption formatting
- Ensure all captions follow the pattern: `[Name], the [Role] daemon - [Description].`

---

## Recommended Implementation

### Step 1: Add Logo to Front Page
Add the site-nine logo to `docs/source/index.md` as a header image.

### Step 2: Choose Placement Strategy
Decide between Option A (scattered) or Option B (dedicated page). 

**Recommendation:** Create a dedicated `roles.md` page for a more comprehensive and visually appealing presentation.

### Step 3: Create Agent Roles Page (if using Option B)
Create `docs/source/roles.md` with sections for each role:

```markdown
# Agent Roles

Site-nine provides specialized agent roles, each represented by a daemon from ancient mythology. Choose the appropriate role for your task to leverage specialized knowledge and capabilities.

---

## Administrator

![Mephistopheles - Administrator](images/mephistopheles.png){ width=400 }

*Mephistopheles, the Administrator daemon - Commanding strategist who coordinates projects and manages delegation.*

The Administrator role is perfect for:
- Project coordination and planning
- Team management and task delegation
- Strategic decision-making
- Workflow orchestration

[Continue with examples, best practices...]

---

## Architect

![Kothar - Architect](images/kothar.png){ width=400 }

*Kothar, the Architect daemon - Master designer who creates system architectures and technical decisions.*

[Continue pattern for all 8 primary roles...]
```

### Step 4: Add Historian to Reference
Place Mimir (Historian) portrait in `docs/source/reference.md` near the `s9 changelog` command section (around line 101-154).

### Step 5: Update Navigation
Add the new roles page to `mkdocs.yaml`:

```yaml
nav:
  - Home: index.md
  - Quickstart: quickstart.md
  - Agent Roles: roles.md  # NEW
  - Usage Guide: usage.md
  - Features: features.md
  - CLI Reference: reference.md
```

### Step 6: Test Build
Run `mkdocs serve` to preview changes and verify:
- All images load correctly
- Sizing is consistent
- Captions are properly formatted
- Navigation works
- Mobile responsiveness looks good

---

## Daemon Descriptions for Captions

Use these short descriptions in your captions:

1. **Argus (Inspector):** Watchful guardian with multiple eyes who performs code reviews and security audits.

2. **Azazel (Builder):** Creative craftsperson with circuit patterns who implements features and writes code.

3. **Mephistopheles (Administrator):** Commanding strategist with obsidian horns who coordinates projects and manages delegation.

4. **Kothar (Architect):** Master designer with geometric tattoos who creates system architectures and technical decisions.

5. **Eris (Tester):** Mischievous chaos-bringer with heterochromatic eyes who finds bugs and edge cases through creative testing.

6. **Astarte (Designer):** Elegant creator with shimmering eyes who designs beautiful user interfaces and experiences.

7. **Nammu (Operator):** Calm infrastructure maintainer with oceanic energy who handles deployment and operations.

8. **Nabu (Documentarian):** Scholarly recorder with cuneiform patterns who writes comprehensive documentation and guides.

9. **Mimir (Historian):** Wise elderly scholar with ice-blue eyes who tracks project history and maintains changelog records.

---

## Files to Modify

- `docs/source/index.md` - Add site-nine logo
- `docs/source/roles.md` - **CREATE NEW** - Agent roles page with 8 primary daemon portraits
- `docs/source/reference.md` - Add Mimir (Historian) portrait to changelog section
- `mkdocs.yaml` - Add roles.md to navigation

---

## Success Criteria

- ✅ Front page (index.md) displays site-nine logo only
- ✅ All 9 daemon portraits appear exactly once throughout documentation
- ✅ Each portrait has a caption with daemon name, role, and short description
- ✅ Images are consistently sized
- ✅ Documentation builds without errors
- ✅ Images display correctly in both light and dark modes
- ✅ Navigation includes the new roles page (if created)
- ✅ Mobile responsiveness is maintained

---

## Notes

- All image filenames are **lowercase** ✅
- Images are located in `docs/source/images/`
- MkDocs Material theme supports attr_list extension for image sizing
- Standard Markdown syntax is used throughout
- Consider adding hover effects or lightbox functionality for images (optional enhancement)

---

## Questions for User

- Do you prefer Option A (scattered throughout existing docs) or Option B (dedicated roles page)?
- Should each role section include usage examples and best practices?
- Any specific styling preferences for the image presentations?

---

**Ready to implement!** Let the documentarian know if you have any preferences or additional requirements.
