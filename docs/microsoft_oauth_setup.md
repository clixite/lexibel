# Microsoft OAuth Setup Guide

## Vue d'ensemble

Ce guide explique comment configurer et utiliser l'intégration Microsoft OAuth2 pour synchroniser Outlook emails et Microsoft Calendar.

## Architecture

### Services créés

1. **microsoft_oauth_service.py** - Gestion du flow OAuth2 Azure AD
   - Génération d'URL d'autorisation
   - Échange du code d'autorisation contre des tokens
   - Rafraîchissement automatique des tokens expirés
   - Stockage chiffré des tokens via `oauth_encryption_service`

2. **microsoft_outlook_sync_service.py** - Synchronisation des emails Outlook
   - Récupération des messages via Microsoft Graph API
   - Création/mise à jour des `EmailThread` et `EmailMessage`
   - Gestion des participants, pièces jointes, métadonnées

3. **microsoft_calendar_service.py** - Synchronisation du calendrier Microsoft
   - Récupération des événements via Microsoft Graph API
   - Création/mise à jour des `CalendarEvent`
   - Gestion des participants, localisations, métadonnées

### Endpoints API

#### OAuth Flow

**GET /api/v1/integrations/microsoft/auth-url**
- Génère l'URL d'autorisation Microsoft
- Retourne: `{auth_url: string, state: string}`

**POST /api/v1/integrations/microsoft/callback**
- Échange le code d'autorisation contre des tokens
- Body: `{code: string}`
- Retourne: `{status: "success", message: string}`

**DELETE /api/v1/integrations/microsoft/disconnect**
- Révoque et supprime les tokens OAuth
- Retourne: `{status: "success", message: string}`

#### Synchronisation

**POST /api/v1/integrations/microsoft/sync/outlook**
- Synchronise les emails Outlook
- Query params:
  - `since_date` (optional): ISO datetime, emails après cette date
  - `max_results` (default: 50): nombre max d'emails
- Retourne: `{status, threads_created, messages_created, messages_updated, total_processed}`

**POST /api/v1/integrations/microsoft/sync/calendar**
- Synchronise le calendrier Microsoft
- Query params:
  - `start_time` (optional): ISO datetime, événements après
  - `end_time` (optional): ISO datetime, événements avant
  - `max_results` (default: 100): nombre max d'événements
- Retourne: `{status, events_created, events_updated, total_processed}`

## Configuration Azure AD

### 1. Créer une application Azure AD

1. Aller sur [Azure Portal](https://portal.azure.com)
2. Naviguer vers **Azure Active Directory** > **App registrations**
3. Cliquer **New registration**
4. Remplir:
   - **Name**: LexiBel
   - **Supported account types**: Accounts in any organizational directory and personal Microsoft accounts
   - **Redirect URI**: `http://localhost:3000/api/auth/callback/microsoft` (dev) ou votre URL de production

### 2. Configurer les permissions

1. Dans l'application créée, aller à **API permissions**
2. Cliquer **Add a permission** > **Microsoft Graph** > **Delegated permissions**
3. Ajouter les permissions suivantes:
   - `Mail.Read` - Lire les emails de l'utilisateur
   - `Calendars.Read` - Lire le calendrier de l'utilisateur
   - `offline_access` - Obtenir un refresh token
4. Cliquer **Grant admin consent** (si nécessaire)

### 3. Créer un client secret

1. Aller à **Certificates & secrets**
2. Cliquer **New client secret**
3. Ajouter une description et choisir l'expiration
4. **IMPORTANT**: Copier immédiatement la valeur du secret (ne sera plus visible après)

### 4. Récupérer les credentials

- **Application (client) ID**: visible dans l'overview de l'app
- **Directory (tenant) ID**: visible dans l'overview de l'app
- **Client secret**: copié à l'étape précédente

## Variables d'environnement

Ajouter dans `.env`:

```bash
# Microsoft OAuth Configuration
MICROSOFT_CLIENT_ID=your_application_client_id
MICROSOFT_CLIENT_SECRET=your_client_secret
MICROSOFT_TENANT_ID=common  # ou votre tenant ID spécifique
MICROSOFT_REDIRECT_URI=http://localhost:3000/api/auth/callback/microsoft

# OAuth Encryption Key (générer avec la commande ci-dessous)
OAUTH_ENCRYPTION_KEY=your_fernet_encryption_key
```

### Générer la clé de chiffrement

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Flow d'utilisation

### 1. Connexion utilisateur

```typescript
// Frontend - Demander l'URL d'autorisation
const response = await fetch('/api/v1/integrations/microsoft/auth-url');
const { auth_url, state } = await response.json();

// Sauvegarder le state (vérification CSRF)
sessionStorage.setItem('oauth_state', state);

// Rediriger l'utilisateur
window.location.href = auth_url;
```

### 2. Callback OAuth

```typescript
// Frontend - Après redirection depuis Microsoft
const urlParams = new URLSearchParams(window.location.search);
const code = urlParams.get('code');
const returnedState = urlParams.get('state');

// Vérifier le state (protection CSRF)
const savedState = sessionStorage.getItem('oauth_state');
if (returnedState !== savedState) {
  throw new Error('Invalid OAuth state');
}

// Échanger le code contre des tokens
await fetch('/api/v1/integrations/microsoft/callback', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ code })
});
```

### 3. Synchronisation

```typescript
// Synchroniser les emails Outlook
const emailsResult = await fetch(
  '/api/v1/integrations/microsoft/sync/outlook?max_results=100',
  { method: 'POST' }
);
const { threads_created, messages_created } = await emailsResult.json();

// Synchroniser le calendrier
const calendarResult = await fetch(
  '/api/v1/integrations/microsoft/sync/calendar?max_results=200',
  { method: 'POST' }
);
const { events_created, events_updated } = await calendarResult.json();
```

## Modèles de données

### OAuthToken

```python
{
  "tenant_id": UUID,
  "user_id": UUID,
  "provider": "microsoft",
  "access_token": str,  # chiffré
  "refresh_token": str,  # chiffré
  "token_type": "Bearer",
  "expires_at": datetime,
  "scope": "Mail.Read Calendars.Read offline_access"
}
```

### EmailThread

```python
{
  "tenant_id": UUID,
  "external_id": str,  # conversationId from Graph API
  "provider": "outlook",
  "subject": str,
  "participants": {
    "from": {"email": str, "name": str},
    "to": [{"email": str, "name": str}],
    "cc": [...],
    "bcc": [...]
  },
  "message_count": int,
  "has_attachments": bool,
  "is_important": bool,
  "last_message_at": datetime,
  "synced_at": datetime
}
```

### EmailMessage

```python
{
  "tenant_id": UUID,
  "thread_id": UUID,
  "external_id": str,  # message ID from Graph API
  "provider": "outlook",
  "subject": str,
  "from_address": str,
  "to_addresses": [str],
  "cc_addresses": [str],
  "bcc_addresses": [str],
  "body_text": str,
  "body_html": str,
  "attachments": [{"filename": str, "size": int}],
  "is_read": bool,
  "is_important": bool,
  "received_at": datetime,
  "synced_at": datetime
}
```

### CalendarEvent

```python
{
  "tenant_id": UUID,
  "user_id": UUID,
  "external_id": str,  # event ID from Graph API
  "provider": "outlook",
  "title": str,
  "description": str,
  "start_time": datetime,
  "end_time": datetime,
  "location": str,
  "attendees": [{"email": str, "name": str, "status": str}],
  "is_all_day": bool,
  "metadata": {
    "webLink": str,
    "organizer": {"email": str, "name": str},
    "responseStatus": str,
    "onlineMeetingUrl": str
  },
  "synced_at": datetime
}
```

## Sécurité

### Chiffrement des tokens

- Tous les tokens OAuth sont chiffrés en base de données via Fernet (AES-128)
- La clé de chiffrement doit être conservée en sécurité
- Ne jamais commiter `OAUTH_ENCRYPTION_KEY` dans le code source

### Rafraîchissement automatique

- Les tokens expirés sont automatiquement rafraîchis lors des appels API
- Le service vérifie `expires_at` avant chaque requête Graph API
- Utilise le `refresh_token` pour obtenir un nouveau `access_token`

### Scopes minimum

- `Mail.Read` - Lecture seule des emails (pas d'envoi)
- `Calendars.Read` - Lecture seule du calendrier (pas de modification)
- `offline_access` - Nécessaire pour obtenir un refresh token

## Limitations Microsoft Graph API

- **Rate limits**:
  - 2000 requêtes par seconde par application
  - 10000 requêtes par 10 minutes par utilisateur
- **Pagination**: Utiliser `@odata.nextLink` pour les résultats > 1000
- **Filtres**: Utiliser la syntaxe OData pour les requêtes complexes

## Troubleshooting

### "No Microsoft OAuth token found"

- L'utilisateur n'a pas connecté son compte Microsoft
- Vérifier dans `oauth_tokens` table si un token existe pour cet utilisateur
- Redemander la connexion OAuth

### "Invalid OAUTH_ENCRYPTION_KEY"

- La clé de chiffrement est invalide ou manquante
- Générer une nouvelle clé avec la commande fournie
- **ATTENTION**: Changer la clé rend tous les tokens existants inutilisables

### "Token expired" / 401 Unauthorized

- Le token a expiré et le refresh a échoué
- Possible causes:
  - Refresh token révoqué par l'utilisateur
  - Application Azure AD désactivée
  - Permissions révoquées
- Solution: Redemander la connexion OAuth

### Rate limit dépassé

- Trop de requêtes vers Graph API
- Implémenter un backoff exponentiel
- Utiliser la pagination au lieu de requêtes multiples
- Monitorer les headers `Retry-After`

## Tests

```bash
# Tester le service OAuth
pytest tests/services/test_microsoft_oauth_service.py

# Tester la synchronisation Outlook
pytest tests/services/test_microsoft_outlook_sync_service.py

# Tester la synchronisation Calendar
pytest tests/services/test_microsoft_calendar_service.py

# Tester les endpoints
pytest tests/routers/test_integrations.py::test_microsoft_oauth_flow
```

## Documentation Microsoft

- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/)
- [Mail API](https://learn.microsoft.com/en-us/graph/api/resources/message)
- [Calendar API](https://learn.microsoft.com/en-us/graph/api/resources/event)
- [OAuth 2.0 Flow](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
