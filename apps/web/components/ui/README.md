# Composants UI LexiBel

Bibliothèque de composants UI réutilisables pour le projet LexiBel, construits avec React, TypeScript et Tailwind CSS.

## Installation

```typescript
// Import depuis le fichier index
import { Badge, Modal, DataTable, StatCard } from '@/components/ui';

// Ou import direct
import Badge from '@/components/ui/Badge';
```

## Composants

### 1. LoadingSkeleton

Skeleton de chargement animé avec 4 variantes.

```typescript
import { LoadingSkeleton } from '@/components/ui';

<LoadingSkeleton variant="card" />    // Grille 3 colonnes
<LoadingSkeleton variant="table" />   // Tableau 5 lignes
<LoadingSkeleton variant="list" />    // Liste verticale
<LoadingSkeleton variant="stats" />   // 4 cards statistiques
```

### 2. ErrorState

Affichage d'erreur avec option de réessayer.

```typescript
import { ErrorState } from '@/components/ui';

<ErrorState
  message="Impossible de charger les données"
  onRetry={() => refetch()}
/>
```

### 3. EmptyState

État vide personnalisable avec icône et action.

```typescript
import { EmptyState } from '@/components/ui';
import { Users } from 'lucide-react';

<EmptyState
  title="Aucun utilisateur"
  description="Commencez par créer votre premier utilisateur"
  icon={<Users className="h-12 w-12 text-neutral-400" />}
  action={{
    label: "Créer un utilisateur",
    onClick: () => router.push('/users/new')
  }}
/>
```

### 4. StatCard

Card de statistiques avec icône et tendance.

```typescript
import { StatCard } from '@/components/ui';
import { Users } from 'lucide-react';

<StatCard
  title="Total Utilisateurs"
  value={1234}
  icon={<Users className="h-6 w-6" />}
  color="accent"
  trend={{ value: 12.5, label: "vs mois dernier" }}
/>
```

**Couleurs disponibles**: `accent`, `success`, `warning`, `error`

### 5. DataTable

Tableau de données paginé et réutilisable.

```typescript
import { DataTable, Column } from '@/components/ui';

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
}

const columns: Column<User>[] = [
  { key: 'name', label: 'Nom' },
  { key: 'email', label: 'Email' },
  {
    key: 'role',
    label: 'Rôle',
    render: (user) => <Badge variant="accent">{user.role}</Badge>
  },
];

<DataTable
  data={users}
  columns={columns}
  onRowClick={(user) => router.push(`/users/${user.id}`)}
  pagination={{
    page: 1,
    perPage: 10,
    total: 100,
    onPageChange: (page) => setPage(page)
  }}
/>
```

### 6. Badge

Badge coloré en 2 tailles et 5 variantes.

```typescript
import { Badge } from '@/components/ui';

<Badge variant="success" size="md">Actif</Badge>
<Badge variant="error" size="sm">Erreur</Badge>
<Badge variant="warning">En attente</Badge>
```

**Variantes**: `default`, `success`, `warning`, `error`, `accent`
**Tailles**: `sm`, `md`

### 7. Modal

Modal responsive avec header, body et footer optionnel.

```typescript
import { Modal } from '@/components/ui';

const [isOpen, setIsOpen] = useState(false);

<Modal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="Créer un utilisateur"
  size="lg"
  footer={
    <div className="flex justify-end space-x-3">
      <button onClick={() => setIsOpen(false)}>Annuler</button>
      <button onClick={handleSubmit}>Créer</button>
    </div>
  }
>
  <form>
    {/* Contenu du formulaire */}
  </form>
</Modal>
```

**Tailles**: `sm` (max-w-md), `md` (max-w-lg), `lg` (max-w-2xl), `xl` (max-w-4xl)

**Fonctionnalités**:
- Fermeture avec Escape
- Fermeture au clic sur overlay
- Scroll verrouillé quand ouvert
- Animation d'entrée

## Design System

### Couleurs

Les composants utilisent les classes Tailwind suivantes:

- **accent**: Bleu (actions primaires)
- **success**: Vert (succès, validation)
- **warning**: Jaune (avertissements)
- **error**: Rouge (erreurs)
- **neutral**: Gris (texte, bordures)

### Typographie

- `font-medium`: Titres et labels
- `text-sm`: Texte secondaire (12-14px)
- `text-base`: Texte normal (16px)
- `text-lg`: Titres de sections

### Ombres et bordures

- `shadow-subtle`: Ombres légères pour cards
- `rounded-lg`: Bordures arrondies (8px)
- `border-neutral-200`: Bordures grises claires

## TypeScript

Tous les composants exportent leurs interfaces Props:

```typescript
import type { ModalProps, DataTableProps, Column } from '@/components/ui';
```

## Dépendances

- `lucide-react`: Icônes (AlertCircle, Inbox, X, ChevronLeft, ChevronRight, TrendingUp, TrendingDown)
- `react`: Hooks (useEffect, useState)
- Tailwind CSS configuré dans le projet
