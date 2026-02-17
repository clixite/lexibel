# Quick Reference - Migration & Admin Pages

## File Locations

```
Migration:    apps/web/app/dashboard/migration/page.tsx (392 lines)
Admin:        apps/web/app/dashboard/admin/page.tsx (81 lines)
Integrations: apps/web/app/dashboard/admin/IntegrationsManager.tsx (NEW, 319 lines)
```

---

## URL Routes

```
Migration:     /dashboard/migration
Admin:         /dashboard/admin
Users Tab:     /dashboard/admin (tab 1)
Tenants Tab:   /dashboard/admin (tab 2)
System Tab:    /dashboard/admin (tab 3)
Integrations:  /dashboard/admin (tab 4)
```

---

## Key Components

### Migration Page
- 5-step wizard with progress bar
- Sources: VeoCRM, Custom
- Steps: Source → Upload → Preview → Confirm → Results

### Admin Page
- 4-tab interface
- Super admin role required
- Sub-components: UsersManager, TenantsManager, SystemHealth, IntegrationsManager

### IntegrationsManager
- Provider cards (Google, Microsoft)
- OAuth flow handling
- Integration table display

---

## API Endpoints

### Migration
```
POST /api/v1/migration/jobs                    Create job
POST /api/v1/migration/jobs/{jobId}/preview    Preview data
POST /api/v1/migration/import                  Import data
```

### Admin
```
GET  /api/v1/admin/users                       Get users
POST /api/v1/admin/users/invite                Invite user
GET  /api/v1/admin/tenants                     Get tenants
POST /api/v1/admin/tenants                     Create tenant
GET  /api/v1/admin/health                      System health
```

### Integrations
```
GET    /admin/integrations                            Get all
POST   /admin/integrations/connect/{provider}         Connect
DELETE /admin/integrations/{integrationId}            Disconnect
```

---

## Features Summary

| Feature | Migration | Admin | Integrations |
|---------|-----------|-------|--------------|
| 5-step wizard | ✅ | - | - |
| Progress bar | ✅ | - | - |
| Source selection | ✅ | - | - |
| CSV upload | ✅ | - | - |
| Data preview | ✅ | - | - |
| Import confirmation | ✅ | - | - |
| Results display | ✅ | - | - |
| Role protection | - | ✅ | - |
| 4 tabs | - | ✅ | - |
| User management | - | ✅ | - |
| Tenant management | - | ✅ | - |
| System health | - | ✅ | - |
| OAuth integration | - | - | ✅ |
| Google Workspace | - | - | ✅ |
| Microsoft 365 | - | - | ✅ |

---

## State Management

### Migration
- step (1-5)
- source (string)
- jobId (string)
- csvText (string)
- preview (object)
- result (object)
- loading (boolean)
- importLoading (boolean)
- error (string|null)

### Admin
- activeTab ("users"|"tenants"|"system"|"integrations")
- userRole (from session)

### Integrations
- integrations (array)
- loading (boolean)
- error (string|null)
- connectingProvider (string|null)

---

## Imports Used

```typescript
// React & Next.js
import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

// Icons (lucide-react)
import {
  Shield, Upload, ArrowRight, ArrowLeft,
  Check, Loader2, AlertCircle, Mail, Cloud,
  Building2, Activity, RefreshCw, Plus
} from "lucide-react";

// API
import { apiFetch } from "@/lib/api";

// Components (existing)
import UsersManager from "./UsersManager";
import TenantsManager from "./TenantsManager";
import SystemHealth from "./SystemHealth";
import IntegrationsManager from "./IntegrationsManager";
```

---

## Color Palette (Tailwind)

### Primary Colors
- **accent**: Brand primary color (used for highlights)
- **success**: Green (indicators, success messages)
- **warning**: Yellow (duplicates, warnings)
- **danger**: Red (errors, delete actions)
- **neutral**: Gray (text, backgrounds)

### Usage in CSS
```css
bg-accent        /* Background */
text-accent      /* Text */
border-accent    /* Border */
bg-accent-50     /* Light background */
bg-accent-100    /* Lighter background */
text-accent-700  /* Dark text */

/* Same pattern for success, warning, danger, neutral */
```

---

## Icons Used

| Icon | Usage | Color |
|------|-------|-------|
| Shield | Admin page header | accent |
| Upload | Migration page header | accent |
| ArrowRight | Next button | default |
| ArrowLeft | Previous button | default |
| Check | Success indicator, Completed step | success/white |
| Loader2 | Loading spinner | accent |
| AlertCircle | Error/warning message | danger/warning |
| Mail | Google integration | blue-600 |
| Cloud | Microsoft integration | orange-600 |
| Building2 | Tenants header | accent |
| Activity | System health header | accent |
| RefreshCw | Refresh button | default |
| Plus | Create new button | default |

---

## Loading States

### All Pages
- Show `Loader2` spinner while fetching
- Disable buttons during operations
- Display "Loading..." text
- Maintain previous data visibility

### Tables
- Show spinner in center
- Display "Aucun utilisateur" when empty
- Show full table with hover effects when loaded

### Forms
- Show spinner in button
- Button text: "Loading...", "Connexion...", "Inviter"
- Disable input fields
- Disable submit button

---

## Error Handling

### All Pages
```
Try-Catch Pattern:
1. API call throws error
2. Extract err.message
3. setError(err.message)
4. Display error alert
5. Allow retry
```

### Alert UI
```html
<div class="bg-danger-50 border border-danger-200
            text-danger-700 px-4 py-3 rounded-md text-sm
            flex items-center gap-2">
  <AlertCircle class="w-4 h-4" />
  {error message}
</div>
```

---

## Authentication

### Session Access
```typescript
const { data: session } = useSession();
const token = (session?.user as any)?.accessToken;
const tenantId = (session?.user as any)?.tenantId;
const role = (session?.user as any)?.role;
```

### Header Injection
```typescript
// apiFetch automatically adds:
// Authorization: Bearer {token}
// X-Tenant-ID: {tenantId}
```

### Admin Protection
```typescript
if (session && role !== "super_admin") {
  return <ErrorState message="Accès refusé" />
}
```

---

## Common Patterns

### Async Function with Loading
```typescript
const handleAction = async () => {
  setLoading(true);
  setError(null);
  try {
    const result = await apiFetch(endpoint, token, {...});
    // Handle success
  } catch (err: any) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
};
```

### Conditional Rendering
```typescript
{loading ? (
  <Loader2 className="animate-spin" />
) : items.length === 0 ? (
  <p>No items</p>
) : (
  <Table />
)}
```

### Tab Navigation
```typescript
<button
  onClick={() => setActiveTab(tab.id)}
  className={`border-b-2 ${
    activeTab === tab.id
      ? "border-accent text-accent"
      : "border-transparent text-neutral-500"
  }`}
>
  {tab.label}
</button>
```

---

## TypeScript Types

### Common
```typescript
type Step = 1 | 2 | 3 | 4 | 5;
type TabId = "users" | "tenants" | "system" | "integrations";
type Status = "active" | "expired" | "error";
type Provider = "google" | "microsoft";
```

### Data
```typescript
interface OAuthIntegration {
  id: string;
  provider: "google" | "microsoft";
  email: string;
  status: "active" | "expired" | "error";
  connected_at: string;
}

interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
}

interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan: string;
}
```

---

## Testing Checklist

### Migration
- [ ] Can select source
- [ ] Can upload CSV
- [ ] Can preview data
- [ ] Can confirm import
- [ ] Can see results
- [ ] Progress bar works
- [ ] Error handling works
- [ ] Can start new migration

### Admin
- [ ] Non-admin sees error
- [ ] Super-admin can access
- [ ] Can switch tabs
- [ ] Users tab loads data
- [ ] Tenants tab loads data
- [ ] System tab loads health
- [ ] Integrations tab loads

### Integrations
- [ ] Google card visible
- [ ] Microsoft card visible
- [ ] Can click connect
- [ ] Can disconnect
- [ ] Status shows correctly
- [ ] Table displays

---

## Build & Deploy

### Build Command
```bash
cd apps/web
npm run build
```

### Environment
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1
```

### Verification
```bash
# Check for errors
npm run build 2>&1

# Should complete successfully
# Watch for TypeScript errors
```

---

## Git Info

**Commit:** `bb0b931`
**Files:** 3 modified/created
**Lines:** +499, -73
**Size:** ~30 KB total

---

## Documentation Files

1. **MIGRATION_ADMIN_IMPLEMENTATION.md** - Detailed specs
2. **VERIFICATION_CHECKLIST.md** - 100+ checkpoints
3. **INTEGRATION_GUIDE.md** - Backend & setup
4. **IMPLEMENTATION_SUMMARY.md** - Project overview
5. **QUICK_REFERENCE.md** - This file

---

## Last Updated

**Date:** February 17, 2026
**Version:** 1.0
**Status:** ✅ Complete & Ready for Integration
