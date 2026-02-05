# Quickstart

![site-nine facility](images/facility-2.png){ align=right width="400" }

Get up and running with site-nine in 5 minutes.

## The Director (You)

**The Director** is you - the human orchestrating AI personas to accomplish work. Throughout this documentation, when we say "The Director," we're referring to you and your role in managing and coordinating AI agents through site-nine.

**site-nine** is designed to work with [OpenCode](https://github.com/khulnasoft/opencode), an AI coding assistant. The Director interacts with specialized personas through natural conversation in OpenCode, while site-nine manages project coordination, tasks, and missions behind the scenes.

## Requirements

* Python 3.12 or later
* pip or uv for package installation
* [OpenCode](https://github.com/khulnasoft/opencode) - Install separately for the full persona experience


## Installation

### Install from PyPI

```bash
pip install site-nine
```

Or with uv:

```bash
uv pip install site-nine
```


## Initialize a Project

In your project directory, run:

```bash
s9 init
```

This launches an interactive wizard that asks:

- **Project name** (defaults to directory name)
- **Project type** (python, typescript, go, rust, other)
- **Project description**
- **Features to enable** (task management, mission tracking, etc.)
- **Persona roles to include**

### Using a Config File

Skip the wizard by providing a YAML config:

```yaml
# s9-config.yaml
project:
  name: my-project
  type: python
  description: My awesome project

features:
  pm_system: true
  session_tracking: true
  commit_guidelines: true
  daemon_naming: true

customization:
  personas_theme: mythology
  variables: {}
```

Then run:

```bash
s9 init --config s9-config.yaml
```


## Verify Installation

Check that the `.opencode` directory was created:

```bash
ls .opencode/
# personas/  data/  guides/  planning/  procedures/  missions/
```

View the dashboard:

```bash
s9 dashboard
```


## Next Steps

### Start Working with Personas

The Director (you) can summon personas in two ways:

#### Option 1: Direct Summon (Recommended)

Use the `s9 summon` command to launch OpenCode with a persona automatically:

```bash
s9 summon operator
```

This will start OpenCode and immediately initialize a mission with the specified role.

#### Option 2: Manual Summon via OpenCode Slash Commands

Launch OpenCode manually and use the `/summon` slash command:

```bash
opencode
```

Then execute the summon slash command to start a mission:

```
/summon
```

Or specify a role directly to skip the role selection step:

```
/summon operator
/summon engineer
/summon tester
```

This will guide the Director through selecting a persona name from mythology. Once summoned, the Director can talk to the persona naturally through conversation.

**OpenCode Slash Commands**: OpenCode provides several slash commands that the Director can use during a session, including `/summon` for starting missions. Type `/help` in OpenCode to see all available commands.


## Working with Your Persona in OpenCode

Once a mission starts, the Director interacts through natural conversation in the OpenCode terminal. Here are some common workflows:

### Creating Tasks

Simply ask the persona to create tasks:

**The Director (You):**
> Create a high-priority task for implementing user authentication

**Persona (Administrator - Ishtar):**
> I'll create that task for you.
> 
> ✓ Created task ENG-H-0001
>   Title: Implement user authentication
>   Priority: HIGH
>   Role: Engineer
>   Status: TODO
> 
> The task has been added to the project database and is ready to be claimed by an Engineer persona.

### Investigating Code

Ask personas to explore and explain the codebase:

**The Director (You):**
> What authentication libraries are we currently using?

**Persona (Inspector - Argus):**
> Let me search the codebase for authentication-related dependencies...
> 
> I found the following authentication libraries in your project:
> 
> **pyproject.toml:**
> - `fastapi-users` - Complete user authentication system
> - `passlib[bcrypt]` - Password hashing
> - `python-jose[cryptography]` - JWT token handling
> 
> **Usage:**
> - Main auth implementation: `src/auth/handlers.py`
> - User models: `src/models/user.py`
> - JWT configuration: `src/config/security.py`

### Building Features

Direct personas to implement functionality:

**The Director (You):**
> Implement a password reset endpoint

**Persona (Engineer - Goibniu):**
> I'll implement a password reset endpoint for you. Let me break this down:
> 
> **Plan:**
> 1. Create POST /auth/reset-password endpoint
> 2. Generate secure reset token
> 3. Add email notification (using existing email service)
> 4. Add token validation
> 
> Let me start by creating the endpoint...
> 
> ✓ Created `src/auth/reset_password.py`
> ✓ Updated `src/auth/router.py` with new endpoint
> ✓ Added tests in `tests/test_reset_password.py`
> 
> The password reset endpoint is now available at POST /auth/reset-password
> 
> Would you like me to test it or create a task for documentation?

### Running Tests

Ask personas to validate their work:

**The Director (You):**
> Run the authentication tests

**Persona (Tester - Ah-Puch):**
> Running authentication test suite...
> 
> ```
> ===== test session starts =====
> tests/test_auth.py::test_login ✓
> tests/test_auth.py::test_logout ✓
> tests/test_auth.py::test_reset_password ✓
> tests/test_auth.py::test_invalid_token ✓
> 
> ===== 4 passed in 0.82s =====
> ```
> 
> ✅ All authentication tests pass!

### Checking Project Status

Ask about tasks and progress:

**The Director (You):**
> What tasks are pending?

**Persona (Administrator - Marduk):**
> Let me check the task database...
> 
> **Pending Tasks (3):**
> 
> | ID         | Priority | Role   | Title                          |
> |------------|----------|--------|--------------------------------|
> | ENG-H-0001 | HIGH     | Engineer| Implement user authentication  |
> | DOC-M-0002 | MEDIUM   | Docs   | Add API documentation          |
> | TST-M-0003 | MEDIUM   | Tester | Add integration tests          |
> 
> Would you like me to claim one of these tasks?


## Getting Help

### Within OpenCode

Personas can help the Director understand available commands and workflows:

**The Director (You):**
> How do I see the dashboard?

**Persona:**
> You can view the project dashboard by running:
> ```bash
> s9 dashboard
> ```
> 
> This shows active personas, task summary, and recent activity.

For complete command reference, see the [CLI Reference](cli/overview.md) page.

## Next Steps

- **[Learn about the .opencode directory](structure.md)** - Understand what's inside and what you can safely edit
- **[Explore agent roles](agents/roles.md)** - See what each role specializes in
- **[Read the CLI reference](cli/overview.md)** - Learn advanced commands and workflows