# Daemons

In site-nine, every agent adopts a **daemon** — a unique character from ancient mythology. Daemons give each possession a distinctive identity and make it easy to track work across multiple concurrent sessions.

## What is a Daemon?

A daemon is a mythological figure that an agent assumes when starting a possession. When the Director summons an agent with `s9 summon`, site-nine selects an appropriate daemon for the chosen role, and the agent introduces itself using that daemon's name. The daemon becomes the agent's identity for the entire work session, appearing in commit messages, possession files, and conversation history.

For example, summoning a Documentarian might result in the agent introducing itself as Fukurokuju (Japanese god of wisdom), working under the possession codename "Operation silver-titan".

## Why Daemons?

Daemons serve both practical and experiential purposes.

### Practical Benefits

**Distinguish concurrent possessions.** Working on multiple tasks at once? Different daemons keep them straight — it's easy to identify which work session is which at a glance in logs, history, and conversation titles.

**Track work history.** Each daemon creates a distinct identity in the database. You can review what "Fukurokuju" worked on versus what "Thoth" worked on. Daemons can be reused across multiple possessions over time.

**Memorable references.** "The Kothar session" is easier to recall than "Possession #47". Daemon names are distinctive and easier to discuss in conversation.

### Experiential Benefits

**Personality and character.** Each daemon has a whimsical bio and backstory, adding flavor and making the agent feel more like a collaborator than a tool.

**Thematic alignment.** Daemons match their role's purpose. Documentarians get gods of wisdom and writing. Engineers get craftspeople and creators. Operators get primordial forces and maintainers.

**Cultural diversity.** The daemon pool draws from mythologies worldwide — Greek, Norse, Egyptian, Japanese, Celtic, Hindu, and more.

## How Daemon Selection Works

### Automatic Selection

When the Director runs `s9 summon`, site-nine automatically selects an appropriate daemon by filtering available names to match the chosen role, preferring daemons that haven't been recently used (3-day LRU threshold), and atomically claiming one from the pool. The selected daemon is then associated with the possession and the agent adopts that identity.

### Manual Selection

Directors can request a specific daemon when summoning:

```bash
s9 summon documentarian
# Then when prompted for daemon selection, specify the name
```

If the requested daemon doesn't exist yet, the system will walk through an invention process — providing the mythology type and description — and create it before starting the possession.

## Daemon Pool

Site-nine maintains a database of 256+ daemons across 9 roles:

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

Each role has approximately 25-30 daemons available, ensuring variety across many possessions.

## Daemon Information

### View Daemon Details

```bash
s9 daemon show <daemon-name>
```

Output includes:

- **Name** - The daemon's name
- **Role** - What role they represent
- **Mythology** - Cultural origin
- **Description** - Brief summary
- **Bio** - Whimsical first-person introduction (if available)

### Daemon Bios

Each daemon can have a **bio** — a whimsical 3-5 sentence first-person narrative about who they are and what they do.

Example bio for Fukurokuju (Documentarian):

> I am Fukurokuju, one of Japan's Seven Lucky Gods, easily recognized by my extraordinarily tall forehead — it's not just for show, it houses all the wisdom I've accumulated over my impossibly long lifespan! I carry a staff with a scroll containing the world's knowledge, though these days I'm thinking of migrating it to a proper documentation system with version control. As the deity of wisdom, wealth, and longevity, I've learned that good documentation is the true path to all three — wise teams build wealth, and well-documented systems live forever. When the other gods need something explained clearly, they call on me, because after thousands of years, I've mastered the art of turning cosmic complexity into comprehensible prose (though my crane companion still insists I could be more concise).

Bios are generated lazily when a daemon is first used, creating personality and context for each character.

## Working with Daemons

### In Commits

Agents reference their daemon in commit messages to trace work back to its source possession:

```bash
git commit -m "[Daemon: Fukurokuju - Documentarian] Add agent system documentation"
```

Alternatively, agents may use the possession codename:

```bash
git commit -m "[Operation: silver-titan] Update daemon documentation"
```

Both approaches help Directors understand which possession produced which commits.

### In Possession Files

Each possession file records the daemon identity in its header:

```markdown
# Possession: Operation silver-titan

**Daemon:** Fukurokuju - Documentarian
**Started:** 2026-02-04 14:16:24
```

This becomes part of the possession's permanent historical record.

### In Sessions

OpenCode sessions are automatically renamed to include the daemon and possession codename:

```
Operation silver-titan: Fukurokuju - Documentarian
```

This naming convention helps Directors quickly identify which session corresponds to which work stream when switching between tasks or reviewing conversation history.

## Daemon Reuse

Daemons can be assigned to multiple possessions over time. They are not exclusive to a single possession, though each active possession has only one daemon. As daemons are used across multiple possessions, they build up a work history that can be reviewed to see what that "character" accomplished.

When the Director summons a Documentarian in a future session, site-nine might assign Fukurokuju again, or select a different daemon like Thoth, Nabu, or Seshat depending on availability and recent usage patterns.

## Daemon Invention

If all daemons for a given role have been used within the last 3 days, site-nine will invent a new daemon. The invention process generates a new name, mythology source, description, and personality, then adds it to the database permanently before starting the possession. This ensures the pool never runs dry on active projects.

## Frequently Asked Questions

### Can Directors choose a specific daemon?

Yes. After running `s9 summon <role>`, you can specify the daemon you want during the possession initialization flow.

### Will the same daemon be assigned each time?

Not necessarily. Site-nine prefers to assign daemons that haven't been used in the last 3 days to add variety, but daemons can and will be reused across possessions over time.

### Can Directors create custom daemons?

Yes. Request a new daemon name during possession initialization, and the system will guide you through creating it if it doesn't already exist.

### What if the assigned daemon doesn't fit the work?

Daemons are purely for identity and tracking — they don't affect agent behavior. The agent's capabilities are determined by its role, not its daemon name. Directors can end a possession and start a new one to get a different daemon assignment, or manually specify a preferred daemon during initialization.

### Do daemons change how agents behave?

No. Daemons are purely for identity, tracking, and adding character to the workflow. Agent behavior and capabilities are determined entirely by the role (Documentarian, Engineer, etc.), not by the daemon name.

## Next Steps

Learn how daemons fit into the broader [possession workflow](possessions.md), explore which daemons represent each [agent role](roles.md), or dive into the [CLI reference](../cli/overview.md) to see all available daemon management commands. Ready to try it out? Follow the [quickstart guide](../quickstart.md) to start your first possession and meet your first daemon.
