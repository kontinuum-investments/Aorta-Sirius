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

## CI/CD Pipeline
## Required Repository Secrets
- `CODECOV_TOKEN`
- `PYPI_ACCESS_TOKEN`
- `QODANA_TOKEN`