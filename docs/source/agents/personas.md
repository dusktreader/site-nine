# Personas

In site-nine, every agent adopts a **persona** - a unique character from ancient mythology. Personas give each mission a distinctive identity and make it easy to track work across multiple concurrent sessions.

## What is a Persona?

A persona is a mythological figure that an agent assumes when starting a mission. When the Director starts a mission with `/summon`, site-nine selects an appropriate persona for the chosen role, and the agent introduces itself using that persona's name. The persona becomes the agent's identity for the entire work session, appearing in commit messages, mission files, and conversation history.

For example, summoning a Documentarian might result in the agent introducing itself as Fukurokuju (Japanese god of wisdom), working under the mission codename "Operation silver-titan".

## Why Personas?

Personas serve both practical and experiential purposes:

### Practical Benefits

**Distinguish concurrent missions**
- Working on multiple tasks? Different personas keep them straight
- Easy to identify which work session is which
- Clear in logs, history, and conversation titles

**Track work history**
- Each persona creates a distinct identity in the database
- Review what "Fukurokuju" worked on vs what "Thoth" worked on
- Personas can be reused across multiple missions over time

**Memorable references**
- "The Kothar session" is easier to remember than "Mission #47"
- Persona names are distinctive and easier to discuss
- Creates natural conversation about work

### Experiential Benefits

**Personality and character**
- Each persona has a whimsical bio and backstory
- Adds flavor and fun to your workflow
- Makes the agent feel more like a collaborator

**Thematic alignment**
- Personas match their role's purpose
- Documentarians get gods of wisdom and writing
- Engineers get craftspeople and creators
- Operators get primordial forces and maintainers

**Cultural diversity**
- 256+ personas from mythologies worldwide
- Greek, Norse, Egyptian, Japanese, Celtic, Hindu, and more
- Exposure to diverse cultural traditions

## How Persona Selection Works

### Automatic Selection

When the Director starts a mission with `/summon`, site-nine automatically selects an appropriate persona by filtering available personas to match the chosen role, preferring personas that haven't been recently used, and randomly selecting from the available pool. The selected persona is then associated with the mission and the agent adopts that identity.

### Manual Selection

Directors can request a specific persona when summoning:

```bash
/summon documentarian --persona=thoth
```

If the requested persona exists for that role, it will be assigned. If the persona doesn't exist yet, the agent will guide the Director through creating it interactively during the summon process.

### Creating New Personas

The typical way to create a custom persona is simply to request it during summoning:

```bash
/summon operator --persona=scooby-doo
```

If "scooby-doo" doesn't exist as an Operator persona, the agent will walk the Director through providing the mythology type and description, then create it and start the mission. This interactive approach is simpler than using CLI commands and happens naturally as part of starting work.

## Persona Pool

Site-nine maintains a database of 256+ personas across 9 roles:

### By Mythology

- **Greek** - 40+ figures (Zeus, Athena, Hephaestus, etc.)
- **Norse** - 30+ figures (Odin, Thor, Loki, etc.)
- **Egyptian** - 30+ figures (Thoth, Anubis, Isis, etc.)
- **Japanese** - 20+ figures (Amaterasu, Susanoo, Inari, etc.)
- **Hindu** - 20+ figures (Brahma, Vishnu, Shiva, etc.)
- **Celtic** - 20+ figures (Brigid, Morrigan, Dagda, etc.)
- **Mesopotamian** - 20+ figures (Enki, Inanna, Marduk, etc.)
- **And more** - Chinese, Aztec, Maya, Yoruba, Slavic, etc.

### By Role Distribution

Each role has approximately 25-30 personas available, ensuring variety across many missions.

## Persona Information

### View Persona Details

See information about a persona:

```bash
s9 persona show <persona-name>
```

Output includes:
- **Name** - The persona's name
- **Role** - What role they represent
- **Mythology** - Cultural origin
- **Description** - Brief summary
- **Bio** - Whimsical first-person introduction (if available)

### Persona Bios

Each persona can have a **bio** - a whimsical 3-5 sentence first-person narrative about who they are and what they do.

Example bio for Fukurokuju (Documentarian):

> I am Fukurokuju, one of Japan's Seven Lucky Gods, easily recognized by my extraordinarily tall forehead - it's not just for show, it houses all the wisdom I've accumulated over my impossibly long lifespan! I carry a staff with a scroll containing the world's knowledge, though these days I'm thinking of migrating it to a proper documentation system with version control. As the deity of wisdom, wealth, and longevity, I've learned that good documentation is the true path to all three - wise teams build wealth, and well-documented systems live forever. When the other gods need something explained clearly, they call on me, because after thousands of years, I've mastered the art of turning cosmic complexity into comprehensible prose (though my crane companion still insists I could be more concise).

Bios are generated lazily when a persona is first used, creating personality and context for each character.

## Working with Personas

### In Commits

Agents reference their persona in commit messages to trace work back to its source mission:

```bash
git commit -m "[Persona: Fukurokuju - Documentarian] Add agent system documentation"
```

Alternatively, agents may use the mission codename:

```bash
git commit -m "[Mission: silver-titan] Update persona documentation"
```

Both approaches help Directors understand which mission produced which commits.

### In Missions

Each mission file records the persona identity in its header:

```markdown
# Mission: Operation silver-titan

**Persona:** Fukurokuju - Documentarian
**Started:** 2026-02-04 14:16:24
```

This becomes part of the mission's permanent historical record.

### In Sessions

OpenCode sessions are automatically renamed to include the persona and mission codename:

```
Operation silver-titan: Fukurokuju - Documentarian
```

This naming convention helps Directors quickly identify which session corresponds to which work stream when switching between tasks or reviewing conversation history.

## Persona Reuse

Personas can be assigned to multiple missions over time. They are not exclusive to a single mission, though each active mission has only one persona. As personas are used across multiple missions, they build up a work history that can be reviewed to see what that "character" accomplished.

When the Director summons a Documentarian in a future session, site-nine might assign Fukurokuju again, or select a different persona like Thoth, Nabu, or Seshat depending on availability and recent usage patterns.

## Frequently Asked Questions

### Can Directors choose a specific persona?

Yes. Use the `--persona=` flag when summoning:

```bash
/summon documentarian --persona=thoth
```

### Will the same persona be assigned each time?

Not necessarily. Site-nine prefers to assign unused personas to add variety, but personas can and will be reused across missions over time.

### Can Directors create custom personas?

Yes. Simply request a new persona name when summoning (e.g., `/summon operator --persona=scooby-doo`), and the agent will guide you through creating it interactively if it doesn't already exist.

### What if the assigned persona doesn't fit the work?

Personas are purely for identity and tracking - they don't affect agent behavior. The agent's capabilities are determined by its role, not its persona name. That said, Directors can end a mission and start a new one to get a different persona assignment, or manually specify a preferred persona using `--persona`.

### Are personas shared across team members?

Personas exist in the shared site-nine database. Multiple Directors working on the same project could potentially have different missions using the same persona name (though at different times or for different work streams).

### Do personas change how agents behave?

No. Personas are purely for identity, tracking, and adding character to the workflow. Agent behavior and capabilities are determined entirely by the role (Documentarian, Engineer, etc.), not by the persona name.

## Next Steps

Learn how personas fit into the broader [mission workflow](missions.md), explore which personas represent each [agent role](roles.md), or dive into the [CLI reference](../cli/overview.md) to see all available persona management commands. Ready to try it out? Follow the [quickstart guide](../quickstart.md) to start your first mission and meet your first persona.
