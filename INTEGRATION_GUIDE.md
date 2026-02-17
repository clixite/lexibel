# Integration Guide - Migration & Admin Pages

## Quick Start

The Migration and Admin pages are now fully implemented and ready to use. Follow this guide to integrate them with your backend.

---

## File Locations

```
apps/web/app/dashboard/
├── migration/
│   └── page.tsx                    (392 lines - Migration Wizard)
└── admin/
    ├── page.tsx                    (81 lines - Admin Dashboard)
    ├── IntegrationsManager.tsx      (319 lines - NEW)
    ├── UsersManager.tsx            (Existing)
    ├── TenantsManager.tsx          (Existing)
    ├── SystemHealth.tsx            (Existing)
    └── integrations/
        └── page.tsx                (Existing - no longer used from admin page)
```

---

## Backend Requirements

### 1. Migration Endpoints

#### Create Migration Job
```http
POST /api/v1/migration/jobs
Authorization: Bearer {token}
Content-Type: application/json

{
  "source_system": "veoCRM" | "custom"
}

Response:
{
  "id": "job-uuid",
  "source_system": "veoCRM",
  "status": "created"
}
```

#### Preview Migration Data
```http
POST /api/v1/migration/jobs/{jobId}/preview
Authorization: Bearer {token}
Content-Type: application/json

{
  "data": [
    {
      "column1": "value1",
      "column2": "value2"
    }
  ]
}

Response:
{
  "total_records": 150,
  "duplicates": 5,
  "sample": [...],
  "tables": ["cases", "contacts"]
}
```

#### Execute Migration Import
```http
POST /api/v1/migration/import
Authorization: Bearer {token}
Content-Type: application/json

{
  "job_id": "job-uuid"
}

Response:
{
  "status": "completed" | "failed",
  "imported_records": 145,
  "failed_records": 5,
  "total_records": 150,
  "error_log": [
    {
      "row": 10,
      "message": "Duplicate record found"
    }
  ]
}
```

---

### 2. Admin Endpoints

#### Get Users
```http
GET /api/v1/admin/users
Authorization: Bearer {token}
X-Tenant-ID: {tenantId}

Response:
{
  "users": [
    {
      "id": "user-uuid",
      "email": "avocat@cabinet.be",
      "full_name": "Jean Dupont",
      "role": "junior",
      "is_active": true,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

#### Invite User
```http
POST /api/v1/admin/users/invite
Authorization: Bearer {token}
X-Tenant-ID: {tenantId}
Content-Type: application/json

{
  "email": "avocat@cabinet.be",
  "full_name": "Jean Dupont",
  "role": "junior"
}

Response:
{
  "id": "user-uuid",
  "email": "avocat@cabinet.be",
  "invitation_sent": true
}
```

#### Get Tenants
```http
GET /api/v1/admin/tenants
Authorization: Bearer {token}

Response:
{
  "tenants": [
    {
      "id": "tenant-uuid",
      "name": "Cabinet Dupont",
      "slug": "cabinet-dupont",
      "plan": "team",
      "status": "active",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

#### Create Tenant
```http
POST /api/v1/admin/tenants
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Cabinet Dupont",
  "slug": "cabinet-dupont",
  "plan": "team"
}

Response:
{
  "id": "tenant-uuid",
  "name": "Cabinet Dupont",
  "slug": "cabinet-dupont",
  "plan": "team",
  "status": "active"
}
```

#### Get System Health
```http
GET /api/v1/admin/health
Authorization: Bearer {token}

Response:
{
  "status": "healthy",
  "services": {
    "api": {
      "status": "healthy",
      "version": "1.0.0"
    },
    "database": {
      "status": "healthy"
    },
    "redis": {
      "status": "healthy"
    },
    "celery": {
      "status": "healthy"
    },
    "storage": {
      "status": "healthy"
    },
    "email": {
      "status": "degraded"
    }
  },
  "checked_at": "2024-02-17T14:30:00Z"
}
```

---

### 3. Integration Endpoints

#### Get Integrations
```http
GET /admin/integrations
Authorization: Bearer {token}
X-Tenant-ID: {tenantId}

Response:
{
  "items": [
    {
      "id": "integration-uuid",
      "provider": "google",
      "email": "user@gmail.com",
      "scopes": ["mail", "calendar"],
      "status": "active",
      "connected_at": "2024-02-15T10:00:00Z",
      "last_sync_at": "2024-02-17T14:00:00Z"
    }
  ]
}
```

#### Initiate OAuth Connection
```http
POST /admin/integrations/connect/{provider}
Authorization: Bearer {token}
X-Tenant-ID: {tenantId}

{provider} = "google" | "microsoft"

Response:
{
  "oauth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

#### Disconnect Integration
```http
DELETE /admin/integrations/{integrationId}
Authorization: Bearer {token}
X-Tenant-ID: {tenantId}

Response:
{
  "success": true
}
```

---

## Frontend Setup

### 1. Environment Configuration

Ensure `NEXT_PUBLIC_API_URL` is set in your `.env.local`:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 2. NextAuth Setup

The pages use `next-auth/react` for session management. Ensure your NextAuth configuration includes:

```typescript
// pages/api/auth/[...nextauth].ts
export const authOptions = {
  // ... your config
  callbacks: {
    async jwt({ token, user, account }) {
      // Include accessToken and tenantId in token
      if (account) {
        token.accessToken = account.access_token;
      }
      return token;
    },
    async session({ session, token }) {
      // Pass accessToken and tenantId to session
      session.user.accessToken = token.accessToken;
      session.user.tenantId = token.tenantId;
      session.user.role = token.role; // Include role for admin protection
      return session;
    },
  },
};
```

### 3. Import Paths

Both pages use the `@` alias for imports:

```typescript
import { apiFetch } from "@/lib/api";     // API helper
import { Shield } from "lucide-react";    // Icons
```

Ensure your `tsconfig.json` includes:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

---

## Component Structure

### Migration Page Structure

```
MigrationPage
├── Progress Bar
├── Step Indicator
├── Step 1: Source Selection
│   ├── Source Cards
│   └── Next Button
├── Step 2: CSV Upload
│   ├── Textarea
│   ├── Previous Button
│   └── Next Button
├── Step 3: Preview
│   ├── Stat Cards
│   ├── Sample Data
│   ├── Previous Button
│   └── Next Button
├── Step 4: Confirmation
│   ├── Summary Card
│   ├── Previous Button
│   └── Import Button
└── Step 5: Results
    ├── Success/Error Alert
    ├── Result Cards
    ├── Error Log (if any)
    └── New Migration Button
```

### Admin Page Structure

```
AdminPage
├── Role Protection Check
├── Page Header
├── Tab Navigation
└── Active Tab Content
    ├── Users Tab
    │   ├── Invite Form
    │   └── Users Table
    ├── Tenants Tab
    │   ├── Create Form
    │   └── Tenants Table
    ├── System Tab
    │   ├── Health Cards
    │   └── Stats Grid
    └── Integrations Tab
        └── IntegrationsManager
            ├── Provider Cards
            ├── Connect/Disconnect
            └── Integrations Table
```

---

## State Management

### Migration Page State
```typescript
const [step, setStep] = useState<Step>(1);
const [source, setSource] = useState<string>("");
const [jobId, setJobId] = useState<string>("");
const [csvText, setCsvText] = useState<string>("");
const [preview, setPreview] = useState<any>(null);
const [result, setResult] = useState<any>(null);
const [loading, setLoading] = useState(false);
const [importLoading, setImportLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
```

### Admin Page State
```typescript
const [activeTab, setActiveTab] = useState<TabId>("users");
const userRole = (session?.user as any)?.role;
```

### IntegrationsManager State
```typescript
const [integrations, setIntegrations] = useState<OAuthIntegration[]>([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
```

---

## Error Handling

The frontend includes comprehensive error handling:

```typescript
try {
  const data = await apiFetch<T>(endpoint, token, {
    method: "POST",
    body: JSON.stringify(payload),
    tenantId
  });
  // Success
} catch (err: any) {
  // err.message contains user-friendly error
  setError(err.message);
}
```

Common error codes from backend should return messages like:
- "API 401: Session expirée"
- "API 400: Données invalides"
- "API 500: Erreur serveur"

---

## Testing

### Manual Testing Checklist

**Migration Page:**
1. Navigate to `/dashboard/migration`
2. Select a source (VeoCRM or Custom)
3. Paste CSV data in Step 2
4. Review preview in Step 3
5. Confirm import in Step 4
6. Check results in Step 5
7. Start new migration

**Admin Page:**
1. Navigate to `/dashboard/admin`
2. Non-admin users should see "Accès refusé"
3. Super admin users see all tabs
4. Click through each tab to verify content
5. Test actions: Invite, Create, Refresh, Connect

**Integrations:**
1. Click "Connecter Google" in Integrations tab
2. Verify OAuth window opens
3. Check integrations list updates
4. Test disconnect functionality

---

## Performance Considerations

1. **Data Loading**
   - Use loading states for all async operations
   - Show spinners during API calls
   - Display skeletons while fetching user lists

2. **Memory Usage**
   - Large CSV data stays as string in textarea
   - Preview data limited by backend
   - Integration list is paginated

3. **Optimization**
   - Memoize provider cards to prevent re-renders
   - Use conditional rendering for tabs
   - Clean up event listeners on unmount

---

## Troubleshooting

### OAuth Window Not Opening
- Check browser popup blocker settings
- Verify `window.open()` is called synchronously
- Ensure OAuth URL is valid from backend

### API 401 Unauthorized
- Verify token is included in session
- Check token expiration
- Clear cookies and re-authenticate

### Data Not Loading
- Check network tab for API calls
- Verify backend endpoint is implemented
- Check X-Tenant-ID header is sent

### Styling Issues
- Ensure Tailwind CSS is installed
- Verify color utility classes are available
- Check dark mode configuration

---

## Future Enhancements

Potential improvements for future iterations:

1. **Migration Page:**
   - Add CSV file upload instead of paste
   - Add data validation/transformation preview
   - Batch import status tracking
   - Import schedule feature

2. **Admin Page:**
   - User edit/delete actions
   - Tenant configuration panel
   - Role-based feature flags
   - Audit logging view

3. **Integrations:**
   - Sync status indicator
   - Sync history/logs
   - Revoke permissions
   - Data sync settings

4. **General:**
   - Dark mode support
   - Pagination for large tables
   - Export admin reports
   - Webhook management

---

## Support

For issues or questions:
1. Check `/MIGRATION_ADMIN_IMPLEMENTATION.md` for detailed documentation
2. Review `/VERIFICATION_CHECKLIST.md` for implementation status
3. Check browser console for error messages
4. Verify backend endpoints are responding correctly

---

## Version History

- **v1.0** (2026-02-17): Initial implementation
  - 5-step migration wizard
  - 4-tab admin dashboard
  - OAuth integration management
  - Full TypeScript support
  - Role-based access control
