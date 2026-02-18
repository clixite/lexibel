# LexiBel - Quick Start Guide

Guide rapide pour démarrer avec la nouvelle UX/UI premium.

---

## Installation & Setup

### Première fois

```bash
# Clone le repository
git clone https://github.com/clixite/lexibel.git
cd lexibel

# Installe les dépendances
npm install

# Configure l'environnement
cp .env.example .env.local
# Éditer .env.local avec vos credentials

# Lance le dev server
cd apps/web
npm run dev
```

### Après pull de la refonte

```bash
# Pull les derniers changements
git pull origin main

# Reinstalle si package.json a changé
npm install

# Rebuild
cd apps/web
npx next build

# Lance dev
npm run dev
```

---

## Commandes Utiles

### Development

```bash
# Dev server (port 3000)
npm run dev

# Dev avec turbopack (plus rapide)
npm run dev -- --turbo

# Build production
npm run build

# Start production server
npm run start

# Lint
npm run lint

# Type check
npm run type-check
```

### Testing

```bash
# Unit tests (à configurer)
npm run test

# E2E tests (à configurer)
npm run test:e2e

# Watch mode
npm run test:watch
```

### Code Quality

```bash
# Format avec Prettier
npm run format

# Check formatting
npm run format:check

# Lint + fix
npm run lint:fix

# Type check strict
npx tsc --noEmit
```

---

## Structure du Projet

```
lexibel/
├── apps/
│   └── web/                    # Next.js app
│       ├── app/
│       │   ├── dashboard/      # 16 pages refaites
│       │   ├── globals.css     # Design system
│       │   └── layout.tsx
│       ├── components/
│       │   ├── ui/             # 17 composants premium
│       │   ├── Sidebar.tsx     # Navigation
│       │   └── TopBar.tsx      # Header
│       └── tailwind.config.ts  # Config Tailwind
├── packages/
│   └── db/                     # Database models
└── infra/
    └── qdrant/                 # Vector DB
```

---

## Utilisation des Composants UI

### Import

```typescript
// Import individuel
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

// Import depuis barrel
import { Button, Card, Badge } from '@/components/ui'
```

### Exemples Rapides

#### Button

```tsx
<Button variant="primary" loading={isLoading}>
  Créer un dossier
</Button>
```

#### Card

```tsx
<Card
  header={
    <div className="flex justify-between">
      <h3>Titre</h3>
      <Badge>Nouveau</Badge>
    </div>
  }
>
  Contenu de la carte
</Card>
```

#### Input

```tsx
<Input
  label="Email"
  type="email"
  error={errors.email}
  prefix={<Mail className="w-4 h-4" />}
/>
```

#### Modal

```tsx
const [isOpen, setIsOpen] = useState(false)

<Modal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="Confirmation"
>
  Êtes-vous sûr ?
</Modal>
```

### Documentation Complète

Voir `apps/web/components/ui/EXAMPLES.md` pour tous les exemples.

---

## Design System

### Couleurs

```tsx
// Primary (Deep Slate)
className="bg-slate-900 text-white"

// Accent (Warm Gold)
className="bg-gold-600 text-white"

// Semantic
className="bg-green-500"  // Success
className="bg-red-500"    // Error
className="bg-yellow-500" // Warning
className="bg-blue-500"   // Info
```

### Typography

```tsx
// Display (Crimson Pro)
className="font-serif text-4xl font-semibold"

// Body (Manrope)
className="font-sans text-base"

// Sizes
text-xs, text-sm, text-base, text-lg, text-xl,
text-2xl, text-3xl, text-4xl, text-5xl
```

### Spacing

```tsx
// Padding/Margin: 0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32
p-4, px-6, py-8, m-2, mx-auto, my-4

// Gap (flex/grid)
gap-2, gap-4, gap-6, gap-8
```

### Shadows

```tsx
shadow-sm      // Subtle
shadow-md      // Medium
shadow-lg      // Large
shadow-xl      // Extra large
shadow-premium // Premium (custom)
```

### Animations

```tsx
// Classes utilitaires
animate-fadeIn
animate-slideUp
animate-scaleIn
animate-shimmer
animate-pulse-subtle

// Transitions
transition-all duration-150 ease-out
transition-colors duration-200
```

---

## Routing

### Pages Dashboard

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard` | Home | Vue d'ensemble + stats |
| `/dashboard/cases` | Dossiers | Gestion des dossiers |
| `/dashboard/contacts` | Contacts | Annuaire clients |
| `/dashboard/billing` | Facturation | Factures + temps |
| `/dashboard/inbox` | Inbox | Messages AI |
| `/dashboard/emails` | Emails | Messagerie |
| `/dashboard/calendar` | Calendrier | Agenda |
| `/dashboard/calls` | Appels | Historique |
| `/dashboard/search` | Recherche | Recherche globale |
| `/dashboard/ai` | AI Hub | Outils AI |
| `/dashboard/legal` | Legal RAG | Recherche juridique |
| `/dashboard/graph` | Graph | Visualisation |
| `/dashboard/ai/transcription` | Transcription | Audio → Text |
| `/dashboard/migration` | Migration | Import données |
| `/dashboard/admin` | Admin | Configuration |

### Routes Dynamiques

```typescript
// Dossier individuel
/dashboard/cases/[id]

// Détection conflits
/dashboard/cases/[id]/conflicts

// Contact individuel
/dashboard/contacts/[id]

// Email thread
/dashboard/emails/[id]

// Détails appel
/dashboard/calls/[id]
```

---

## Développement

### Créer un Nouveau Composant

```bash
# 1. Créer le fichier
touch apps/web/components/ui/MyComponent.tsx

# 2. Template de base
```

```tsx
'use client'

import { cn } from '@/lib/utils'

interface MyComponentProps {
  children: React.ReactNode
  className?: string
}

export function MyComponent({ children, className }: MyComponentProps) {
  return (
    <div className={cn('base-styles', className)}>
      {children}
    </div>
  )
}
```

```bash
# 3. Export dans index.ts
echo "export { MyComponent } from './MyComponent'" >> apps/web/components/ui/index.ts
```

### Créer une Nouvelle Page

```bash
# 1. Créer le dossier
mkdir -p apps/web/app/dashboard/my-page

# 2. Créer page.tsx
touch apps/web/app/dashboard/my-page/page.tsx
```

```tsx
export default function MyPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-serif font-semibold mb-6">
        Ma Page
      </h1>
      {/* Contenu */}
    </div>
  )
}
```

### Ajouter une Route au Sidebar

```tsx
// Dans components/Sidebar.tsx

const navigation = [
  // ...
  {
    name: 'Ma Page',
    href: '/dashboard/my-page',
    icon: MyIcon,
    badge: '3', // optionnel
  },
]
```

---

## Debugging

### Build Errors

```bash
# Voir les erreurs TypeScript
npx tsc --noEmit

# Build verbose
npx next build --debug

# Analyser le bundle
npm install -g @next/bundle-analyzer
ANALYZE=true npm run build
```

### Dev Server Issues

```bash
# Clean .next cache
rm -rf apps/web/.next

# Clean node_modules
rm -rf node_modules apps/web/node_modules
npm install

# Kill port 3000
lsof -ti:3000 | xargs kill -9  # Mac/Linux
netstat -ano | findstr :3000   # Windows
```

### Type Errors

```bash
# Regenerer types Prisma
npx prisma generate

# Check TypeScript version
npx tsc --version

# Update @types
npm update @types/react @types/node
```

---

## Git Workflow

### Branches

```bash
# Créer feature branch
git checkout -b feature/my-feature

# Commit
git add .
git commit -m "feat: add my feature"

# Push
git push -u origin feature/my-feature

# Merge to main
git checkout main
git merge feature/my-feature
git push
```

### Conventions de Commit

```
feat: nouvelle fonctionnalité
fix: correction de bug
refactor: refactoring sans changement fonctionnel
style: changements de style (formatting, etc.)
docs: documentation
test: ajout/modification de tests
chore: maintenance (deps, config, etc.)
```

---

## Déploiement

### Vercel (Recommandé)

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy preview
vercel

# Deploy production
vercel --prod
```

### Docker

```bash
# Build image
docker build -t lexibel-web .

# Run container
docker run -p 3000:3000 lexibel-web
```

### Variables d'Environnement

```bash
# .env.local (development)
DATABASE_URL="postgresql://..."
NEXTAUTH_SECRET="..."
NEXTAUTH_URL="http://localhost:3000"

# .env.production (production)
DATABASE_URL="postgresql://..."
NEXTAUTH_SECRET="..."
NEXTAUTH_URL="https://lexibel.com"
```

---

## Troubleshooting

### "Cannot find module '@/components/ui'"

```bash
# Vérifier tsconfig.json
"paths": {
  "@/*": ["./*"]
}
```

### "Hydration mismatch"

```tsx
// Ajouter suppressHydrationWarning
<html suppressHydrationWarning>

// Ou wrapper en client component
'use client'
```

### "Module not found: Can't resolve 'X'"

```bash
# Installer la dépendance
npm install X

# Ou mettre à jour
npm update
```

### Animations ne fonctionnent pas

```js
// Vérifier tailwind.config.ts
theme: {
  extend: {
    keyframes: { /* ... */ },
    animation: { /* ... */ }
  }
}
```

---

## Resources

### Documentation
- Next.js: https://nextjs.org/docs
- Tailwind CSS: https://tailwindcss.com/docs
- TypeScript: https://www.typescriptlang.org/docs
- React: https://react.dev

### Design System
- `apps/web/components/ui/README.md` - Component docs
- `apps/web/components/ui/EXAMPLES.md` - Code examples
- `apps/web/app/globals.css` - CSS variables

### Project Docs
- `REFONTE_UX_UI_COMPLETE.md` - Full refonte report
- `MISSION_QA_FINAL_SUCCESS.md` - QA summary
- `COMPONENT_MIGRATION_GUIDE.md` - Migration guide

---

## Support

### Issues
- GitHub: https://github.com/clixite/lexibel/issues
- Email: support@lexibel.com

### Team
- Product: [Product Owner]
- Design: [Lead Designer]
- Dev: [Lead Developer]
- QA: [QA Engineer]

---

**Last Updated**: 2026-02-17
**Version**: 1.0.0
**Status**: Production Ready
