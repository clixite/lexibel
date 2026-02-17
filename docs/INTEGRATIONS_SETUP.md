# LexiBel - Integrations Setup Guide

This guide explains how to configure all third-party integrations for LexiBel.

---

## 📋 Table of Contents

1. [Google OAuth (Gmail + Calendar)](#google-oauth)
2. [Microsoft OAuth (Outlook + Calendar)](#microsoft-oauth)
3. [Ringover (Telephony)](#ringover)
4. [Plaud.ai (Transcription)](#plaudai)
5. [OpenAI (AI Services)](#openai)
6. [OAuth Encryption](#oauth-encryption)

---

## 1. Google OAuth (Gmail + Calendar) {#google-oauth}

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project: "LexiBel Integration"
3. Enable APIs:
   - Gmail API
   - Google Calendar API

### Step 2: Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Select **Internal** (if Google Workspace) or **External**
3. Fill in:
   - App name: `LexiBel`
   - User support email: your email
   - Developer contact: your email
4. Add scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/calendar.readonly`
5. Save

### Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ CREATE CREDENTIALS → OAuth client ID**
3. Application type: **Web application**
4. Name: `LexiBel Web`
5. Authorized redirect URIs:
   - `http://localhost:3000/api/auth/callback/google` (dev)
   - `https://lexibel.clixite.cloud/api/auth/callback/google` (prod)
6. Click **CREATE**

### Step 4: Copy Credentials to .env

```bash
GOOGLE_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret-here
GOOGLE_REDIRECT_URI=http://localhost:3000/api/auth/callback/google
```

### Testing

```bash
# Test OAuth flow
curl -X POST http://localhost:8000/api/v1/admin/integrations/google/connect \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# This will return an authorization URL
# Navigate to it in your browser to authorize
```

---

## 2. Microsoft OAuth (Outlook + Calendar) {#microsoft-oauth}

### Step 1: Register App in Azure

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Microsoft Entra ID (formerly Azure AD) → App registrations**
3. Click **+ New registration**
4. Fill in:
   - Name: `LexiBel`
   - Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
   - Redirect URI:
     - Platform: **Web**
     - URI: `http://localhost:3000/api/auth/callback/microsoft` (add production URI later)
5. Click **Register**

### Step 2: Configure API Permissions

1. Go to **API permissions**
2. Click **+ Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Add permissions:
   - `Mail.Read`
   - `Calendars.Read`
6. Click **Add permissions**
7. Click **Grant admin consent** (if you're an admin)

### Step 3: Create Client Secret

1. Go to **Certificates & secrets**
2. Click **+ New client secret**
3. Description: `LexiBel Backend`
4. Expires: 24 months
5. Click **Add**
6. **IMPORTANT**: Copy the secret value immediately (it won't be shown again)

### Step 4: Copy Credentials to .env

```bash
MICROSOFT_CLIENT_ID=12345678-1234-1234-1234-123456789abc
MICROSOFT_CLIENT_SECRET=your-secret-value-here
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=http://localhost:3000/api/auth/callback/microsoft
```

### Testing

```bash
# Test OAuth flow
curl -X POST http://localhost:8000/api/v1/admin/integrations/microsoft/connect \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 3. Ringover (Telephony) {#ringover}

### Step 1: Get API Key

1. Log in to [Ringover Dashboard](https://dashboard.ringover.com/)
2. Go to **Settings → API**
3. Click **Generate API Key**
4. Copy the key

### Step 2: Configure Webhook

1. In Ringover Dashboard, go to **Settings → Webhooks**
2. Click **+ Add Webhook**
3. URL: `https://lexibel.clixite.cloud/api/v1/webhooks/ringover`
4. Secret: Generate a random string (e.g., `openssl rand -hex 32`)
5. Events to subscribe:
   - Call answered
   - Call missed
   - Voicemail received
6. Save

### Step 3: Copy Credentials to .env

```bash
RINGOVER_API_KEY=rg_live_your_api_key_here
RINGOVER_API_BASE_URL=https://public-api.ringover.com/v2
RINGOVER_WEBHOOK_SECRET=your-webhook-secret-here
```

### Testing

```bash
# Test webhook endpoint
curl -X POST http://localhost:8000/api/v1/webhooks/ringover \
  -H "X-Ringover-Signature: signature-here" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "call.answered",
    "call_id": "test-123",
    "tenant_id": "your-tenant-id",
    "direction": "inbound",
    "caller_number": "+32470123456",
    "duration_seconds": 154
  }'
```

---

## 4. Plaud.ai (Transcription) {#plaudai}

### Step 1: Get API Key

1. Go to [Plaud.ai](https://plaud.ai/)
2. Sign up / Log in
3. Navigate to **Settings → API Keys**
4. Click **Create New API Key**
5. Copy the key

### Step 2: Configure Webhook (optional)

If Plaud.ai supports webhooks for completed transcriptions:

1. Webhook URL: `https://lexibel.clixite.cloud/api/v1/webhooks/plaud`
2. Secret: Generate with `openssl rand -hex 32`

### Step 3: Copy Credentials to .env

```bash
PLAUD_API_KEY=plaud_your_api_key_here
PLAUD_API_BASE_URL=https://api.plaud.ai/v1
PLAUD_WEBHOOK_SECRET=your-webhook-secret
```

### Testing

```bash
# Test transcription upload
curl -X POST http://localhost:8000/api/v1/ai/transcribe \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "audio=@/path/to/audio.mp3" \
  -F "case_id=your-case-id"
```

---

## 5. OpenAI (AI Services) {#openai}

### Step 1: Get API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up / Log in
3. Navigate to **API Keys**
4. Click **+ Create new secret key**
5. Name: `LexiBel`
6. Copy the key

### Step 2: Set Usage Limits (recommended)

1. Go to **Settings → Billing → Limits**
2. Set monthly budget cap (e.g., €100)
3. Enable email alerts

### Step 3: Copy Key to .env

```bash
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
```

### Testing

```bash
# Test AI summarization
curl -X POST http://localhost:8000/api/v1/ai/summarize \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "your-case-id",
    "prompt": "Summarize this case"
  }'
```

---

## 6. OAuth Encryption {#oauth-encryption}

OAuth tokens are stored encrypted in the database using **Fernet** (symmetric encryption).

### Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output to `.env`:

```bash
OAUTH_ENCRYPTION_KEY=your-generated-fernet-key-here
```

### Security Notes

- ⚠️  **NEVER** commit this key to Git
- 🔒 Store it in a secrets manager (e.g., AWS Secrets Manager, Azure Key Vault)
- 🔄 Rotate the key periodically (requires re-encrypting all tokens)

---

## 📝 Full .env Example

```bash
# Copy .env.example to .env and fill in these values:

# Google OAuth
GOOGLE_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/api/auth/callback/google

# Microsoft OAuth
MICROSOFT_CLIENT_ID=12345678-1234-1234-1234-123456789abc
MICROSOFT_CLIENT_SECRET=your-secret
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=http://localhost:3000/api/auth/callback/microsoft

# Ringover
RINGOVER_API_KEY=rg_live_your_key
RINGOVER_WEBHOOK_SECRET=your-webhook-secret

# Plaud.ai
PLAUD_API_KEY=plaud_your_key
PLAUD_WEBHOOK_SECRET=your-webhook-secret

# OpenAI
OPENAI_API_KEY=sk-proj-your-key

# OAuth Encryption
OAUTH_ENCRYPTION_KEY=your-fernet-key
```

---

## ✅ Verification Checklist

After configuration, verify each integration:

- [ ] Google OAuth: Can authorize and fetch emails/calendar
- [ ] Microsoft OAuth: Can authorize and fetch emails/calendar
- [ ] Ringover: Webhooks arrive and create call records
- [ ] Plaud.ai: Audio files are transcribed successfully
- [ ] OpenAI: AI features work (summarization, transcription)
- [ ] OAuth tokens are encrypted in database

---

## 🛡️ Security Best Practices

1. **Never commit secrets to Git**
   - Use `.env` (already in `.gitignore`)
   - Use environment variables in production

2. **Use a secrets manager in production**
   - AWS Secrets Manager
   - Azure Key Vault
   - HashiCorp Vault

3. **Rotate keys regularly**
   - OAuth secrets: Every 6-12 months
   - API keys: Every 12 months
   - Encryption keys: With re-encryption script

4. **Audit OAuth access**
   - Review granted permissions monthly
   - Revoke unused integrations
   - Log all OAuth token usage

---

**Questions?** Contact support@lexibel.be

