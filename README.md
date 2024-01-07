# Aorta-Sirius

The Global Python SDK for the Central Finite Curve

[![codecov](https://codecov.io/gh/kontinuum-investments/Aorta-Sirius/branch/production/graph/badge.svg?token=TYY4X666XE)](https://codecov.io/gh/kontinuum-investments/Aorta-Sirius)

# Installation

## Required Environment Variables
- `ENVIRONMENT` - Determines which environment it is currently in; either `Production`, `Test`, `Development` or `CI/CD Pipeline`
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_SECRET` - [Documentation](https://learn.microsoft.com/en-us/azure/industry/training-services/microsoft-community-training/frequently-asked-questions/generate-new-clientsecret-link-to-key-vault)
- `AZURE_KEY_VAULT_URL`

## Discord
1. Create a Discord server with the same name as the value for the key vault secret `APPLICATION-NAME`
2. Add the Discord bot to the server - [Documentation](https://discordjs.guide/preparations/adding-your-bot-to-servers.html#creating-and-using-your-invite-link)
   1. Grant following permissions to the bot:
      1. `Administrator` _(To be reviewed later)_
3. Add the bot to a list of members who can add each channel created _(this will be automated in the future)_
   1. Go to `Edit Channel` -> `Permissions` -> `Add members of roles`

## Azure
### Key Vault
1. Create a KeyVault
2. Assign appropriate role to the App Registration
   1. `Key Vault Secrets User` - If you only need read permissions
   2. `Key Vault Secrets Officer` - If you need both read and write permissions

### Required Key Vault Secrets
- `APPLICATION-NAME` _(Used as the default Discord Server Name)_
- `DISCORD-BOT-TOKEN`
- `SENTRY-URL`
- `WISE-PRIMARY-ACCOUNT-API-KEY`
- `WISE-SECONDARY-ACCOUNT-API-KEY`
- `MONGO-DB-CONNECTION-STRING`
- `ENTRA-ID-CLIENT-ID`
- `ENTRA-ID-TENANT-ID`
- `TWILIO-AUTH-TOKEN`
- `TWILIO-ACCOUNT-SID`
- `TWILIO-WHATSAPP-NUMBER`
- `TWILIO-SMS-NUMBER`
- `OPEN-AI-API-KEY`

## CI/CD Pipeline
## Required Repository Secrets
- `CODECOV_TOKEN`
- `PYPI_ACCESS_TOKEN`
- `QODANA_TOKEN`