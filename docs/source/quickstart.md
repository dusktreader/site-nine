# Quickstart

![site-nine facility](images/facility-2.png){ align=right width="400" }

Get up and running with site-nine in 5 minutes.

**site-nine** is designed to work with [OpenCode](https://github.com/khulnasoft/opencode), an AI coding assistant. You'll interact with specialized agents through natural conversation in OpenCode, while site-nine manages project coordination, tasks, and sessions behind the scenes.

## Requirements

* Python 3.12 or later
* pip or uv for package installation
* [OpenCode](https://github.com/khulnasoft/opencode) - Install separately for the full agent experience


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
- **Features to enable** (task management, session tracking, etc.)
- **Agent roles to include**

### Using a Config File

Skip the wizard by providing a YAML config:

```yaml
# s9.yaml
project:
  name: my-project
  type: python
  description: My awesome project

features:
  pm_system: true
  session_tracking: true
  commit_guidelines: true
  daemon_naming: true

agent_roles:
  - name: Administrator
    enabled: true
  - name: Builder
    enabled: true
  - name: Tester
    enabled: true
```

Then run:

```bash
s9 init --config s9.yaml
```


## Verify Installation

Check that the `.opencode` directory was created:

```bash
ls .opencode/
# agents/  data/  guides/  planning/  procedures/  sessions/
```

View the dashboard:

```bash
s9 dashboard
```


## Next Steps

### Start Working with Agents in OpenCode

Now that site-nine is initialized, launch OpenCode in your project directory:

```bash
opencode
```

Then execute the summon command to start an agent session:

```
/summon
```

This will guide you through selecting an agent role (Builder, Tester, Architect, etc.) and choosing a daemon name from mythology. Once summoned, you can talk to your agent naturally through conversation.


## Working with Your Agent in OpenCode

Once your agent session starts, you interact through natural conversation in the OpenCode terminal. Here are some common workflows:

### Creating Tasks

Simply ask your agent to create tasks:

**You:**
> Create a high-priority task for implementing user authentication

**Agent (Administrator - Ishtar):**
> I'll create that task for you.
> 
> ✓ Created task BLD-H-0001
>   Title: Implement user authentication
>   Priority: HIGH
>   Role: Builder
>   Status: TODO
> 
> The task has been added to the project database and is ready to be claimed by a Builder agent.

### Investigating Code

Ask agents to explore and explain your codebase:

**You:**
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

**You:**
> Implement a password reset endpoint

**Agent (Builder - Goibniu):**
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

**You:**
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

**You:**
> What tasks are pending?

**Agent (Administrator - Marduk):**
> Let me check the task database...
> 
> **Pending Tasks (3):**
> 
> | ID         | Priority | Role   | Title                          |
> |------------|----------|--------|--------------------------------|
> | BLD-H-0001 | HIGH     | Builder| Implement user authentication  |
> | DOC-M-0002 | MEDIUM   | Docs   | Add API documentation          |
> | TST-M-0003 | MEDIUM   | Tester | Add integration tests          |
> 
> Would you like me to claim one of these tasks?


## Getting Help

### Within OpenCode

Your agent can help you understand available commands and workflows:

**You:**
> How do I see the dashboard?

**Agent:**
> You can view the project dashboard by running:
> ```bash
> s9 dashboard
> ```
> 
> This shows active agents, task summary, and recent activity.

For complete command reference, see the [CLI Reference](reference.md) page.

## Next Steps

- **[Learn about the .opencode directory](structure.md)** - Understand what's inside and what you can safely edit
- **[Explore agent roles](roles.md)** - See what each agent type specializes in
- **[Read the usage guide](usage.md)** - Learn advanced workflows and patterns