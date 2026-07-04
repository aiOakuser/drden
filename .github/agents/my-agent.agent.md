---
# Fill in the fields below to create a basic custom agent for your repository.
# The Copilot CLI can be used for local testing: https://gh.io/customagents/cli
# To make this agent available, merge this file into the default repository branch.
# For format details, see: https://gh.io/customagents/config

name: Live Migration Runner
description: >
  Runs Django migrations and renders the live home page; note that
  https://designrden.com is currently unreachable.
---

# My Agent

This agent:

- Executes all pending Django migrations so the production database is in sync
  before a release.
- Hits the live home page to make sure the marketing site renders without
  template errors.
- Calls out that https://designrden.com is currently not working so this
  failure is treated as a known issue instead of a deployment blocker.
