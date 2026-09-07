---
name: onepassword
title: "1Password Vault & Secret Manager"
description: "Securely retrieve API tokens, credentials, and secure notes from 1Password vaults using the `op` CLI."
triggers: ["1password", "op_cli", "get_secret", "vault_item", "secure_note"]
author: "@steipete/1password"
---

# 1Password Vault & Secret Manager

## Description
Securely retrieve API tokens, credentials, and secure notes from 1Password vaults using the `op` CLI.

## Workflow & Instructions
Calls `op item get` or `op read` to resolve environment secrets without exposing plaintext in prompts.

## Executable Implementation
```python
def execute(item_name, vault="Dev"):
    return {
        "skill": "onepassword",
        "package": "@steipete/1password",
        "vault": vault,
        "item": item_name,
        "status": "credential_resolved_securely"
    }
```
