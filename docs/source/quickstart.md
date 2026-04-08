# Quickstart

![site-nine facility](images/facility-2.png){ align=right width="400" }

Get up and running with site-nine in 5 minutes.

## The Director (You)

**The Director** is you - the human orchestrating AI personas to accomplish work. Throughout this documentation, when we say "The Director," we're referring to you and your role in managing and coordinating AI agents through site-nine.

**site-nine** is designed to work with [OpenCode](https://github.com/khulnasoft/opencode), an AI coding assistant. The Director interacts with specialized agents through natural conversation in OpenCode, while site-nine manages project coordination, tasks, and possessions behind the scenes.

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
- **Features to enable** (task management, possession tracking, etc.)
- **Daemon roles to include**

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
# docs/  data/  skills/  work/
```

View the dashboard:

```bash
s9 dashboard
```


## Next Steps

### Start Working with Agents

The Director (you) summons agents using the `s9 summon` command:

#### Option 1: Direct Summon (Recommended)

Use the `s9 summon` command to launch OpenCode with an agent automatically:

```bash
s9 summon operator
```

This starts OpenCode and immediately initializes a possession with the specified role. The `possession-start` skill runs automatically, selects a daemon, and renames the session to `Operation <codename>: <Daemon> - <Role>`.

#### Option 2: Manual Launch

Launch OpenCode directly, then ask the agent to load the `possession-start` skill:

```bash
opencode
```

Once a possession starts, you can talk to the agent naturally through conversation.


## Working with Your Agent in OpenCode

Once a possession starts, the Director interacts through natural conversation in the OpenCode terminal. Here are some common workflows:

### Creating Tasks

Simply ask the agent to create tasks:

**The Director (You):**
> Create a high-priority task for implementing user authentication

**Agent (Administrator - Ishtar):**
> I'll create that task for you.
> 
> ✓ Created task ENG-H-0001
>   Title: Implement user authentication
>   Priority: HIGH
>   Role: Engineer
>   Status: TODO
> 
> The task has been added to the project database and is ready to be claimed by an Engineer.

### Investigating Code

Ask agents to explore and explain the codebase:

**The Director (You):**
> What authentication libraries are we currently using?

**Agent (Inspector - Argus):**
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

Direct agents to implement functionality:

**The Director (You):**
> Implement a password reset endpoint

**Agent (Engineer - Goibniu):**
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

Ask agents to validate their work:

**The Director (You):**
> Run the authentication tests

**Agent (Tester - Ah-Puch):**
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

**Agent (Administrator - Marduk):**
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

Agents can help the Director understand available commands and workflows:

**The Director (You):**
> How do I see the dashboard?

**Agent:**
> You can view the project dashboard by running:
> ```bash
> s9 dashboard
> ```
> 
> This shows active possessions, task summary, and recent activity.

For complete command reference, see the [CLI Reference](cli/overview.md) page.

## Next Steps

- **[Learn about the .opencode directory](structure.md)** - Understand what's inside and what you can safely edit
- **[Explore agent roles](agents/roles.md)** - See what each role specializes in
- **[Read the CLI reference](cli/overview.md)** - Learn advanced commands and workflows