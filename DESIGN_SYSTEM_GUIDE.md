# LexiBel Design System - Guide d'Utilisation

## Vue d'ensemble

Ce guide décrit comment utiliser les 5 composants principaux du design system LexiBel pour créer des pages cohérentes et maintenables.

### Composants disponibles
- **Card**: Conteneur principal
- **Badge**: Indicateur/tag
- **Button**: Action
- **Tabs**: Filtrage/navigation
- **DataTable**: Listes de données

---

## 1. Card Component

### Import
```tsx
import { Card } from "@/components/ui";
```

### Usage Basique
```tsx
<Card>
  <div>Contenu simple</div>
</Card>
```

### Props
```tsx
interface CardProps {
  children: ReactNode;
  hover?: boolean;        // Ajoute hover effect (lift + shadow)
  className?: string;     // Classes Tailwind additionnelles
  header?: ReactNode;     // Contenu header avec border-bottom
  footer?: ReactNode;     // Contenu footer avec border-top
  onClick?: () => void;   // Callback au clic
}
```

### Exemples

#### Stats Card
```tsx
<Card className="hover:shadow-lg transition-shadow">
  <StatCard
    title="Total Conversations"
    value={42}
    icon={<Mail className="w-5 h-5" />}
    color="accent"
  />
</Card>
```

#### Item Card avec Hover
```tsx
<Card hover onClick={() => navigate()}>
  <div className="flex items-start gap-4">
    <div className="w-10 h-10 bg-accent-50 rounded-lg" />
    <div className="flex-1">
      <h3 className="font-medium">Titre</h3>
      <p className="text-sm text-neutral-600">Description</p>
    </div>
  </div>
</Card>
```

#### Card avec Header/Footer
```tsx
<Card
  header={<h3 className="font-semibold">Titre Section</h3>}
  footer={<Button onClick={handleSave}>Enregistrer</Button>}
>
  {/* Contenu */}
</Card>
```

### Classes Tailwind
```css
/* Base */
bg-white rounded-lg shadow-md transition-all duration-normal

/* Hover (si hover={true}) */
hover:-translate-y-1 hover:shadow-xl

/* Custom */
p-6                    /* Padding interne */
border border-neutral-100
```

---

## 2. Badge Component

### Import
```tsx
import { Badge } from "@/components/ui";
```

### Props
```tsx
interface BadgeProps {
  children: ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "accent" | "neutral";
  size?: "sm" | "md";
  dot?: boolean;           // Ajoute dot indicator avant le texte
  pulse?: boolean;         // Animation pulse
  className?: string;      // Tailwind classes additionnelles
}
```

### Variants Colors

| Variant | Background | Text | Use Case |
|---------|------------|------|----------|
| default | bg-neutral-100 | text-neutral-700 | Défaut, neutre |
| success | bg-success-100 | text-success-700 | Validé, réussi |
| warning | bg-warning-100 | text-warning-700 | Attention, en attente |
| danger | bg-danger-100 | text-danger-700 | Erreur, refusé |
| accent | bg-accent-100 | text-accent-700 | Important, focus |
| neutral | bg-neutral-200 | text-neutral-800 | Secondaire |

### Exemples

#### Status Badge
```tsx
<Badge
  variant={status === "DRAFT" ? "warning" : "success"}
  size="sm"
>
  {statusLabel}
</Badge>
```

#### Badge avec Dot Indicator
```tsx
<Badge variant="success" dot>
  Entrant
</Badge>
```

#### Count Badge
```tsx
<Badge variant="accent" size="sm">
  42
</Badge>
```

#### Badge avec Custom Margin
```tsx
<Badge variant="accent" size="sm" className="ml-2">
  Dossier suggéré
</Badge>
```

### Sizing
- **sm**: `px-2 py-0.5 text-xs` (compact)
- **md**: `px-2.5 py-1 text-sm` (par défaut, normal)

---

## 3. Button Component

### Import
```tsx
import { Button } from "@/components/ui";
```

### Props
```tsx
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;       // Montre spinner au lieu d'icon
  icon?: ReactNode;        // Icône avant le texte
  children?: ReactNode;    // Texte du bouton (optionnel)
  className?: string;      // Tailwind classes additionnelles
  disabled?: boolean;
  onClick?: () => void;
}
```

### Variants

| Variant | Style | Use Case |
|---------|-------|----------|
| primary | bg-accent + hover scale | Actions principales |
| secondary | border + white bg | Actions alternatives |
| ghost | transparent | Actions secondaires |
| danger | bg-danger + hover scale | Actions destructives |

### Sizes

| Size | Padding | Font | Use Case |
|------|---------|------|----------|
| sm | px-3 py-1.5 | text-sm | Boutons compacts, inline |
| md | px-4 py-2 | text-base | Boutons standards |
| lg | px-6 py-3 | text-lg | CTAs principales |

### Exemples

#### Button Principal
```tsx
<Button
  variant="primary"
  size="md"
  onClick={handleSubmit}
>
  Enregistrer
</Button>
```

#### Button avec Icon
```tsx
<Button
  variant="primary"
  icon={<CheckCircle2 className="w-4 h-4" />}
>
  Valider
</Button>
```

#### Button Loading
```tsx
<Button
  variant="primary"
  loading={isLoading}
  onClick={handleAsync}
>
  Synchroniser...
</Button>
```

#### Icon-only Button
```tsx
<Button
  variant="ghost"
  icon={<ChevronDown className="w-4 h-4" />}
/>
```

#### Button Danger
```tsx
<Button
  variant="danger"
  size="sm"
  icon={<XCircle className="w-3.5 h-3.5" />}
>
  Refuser
</Button>
```

### Focus State
```css
focus:outline-none
focus:ring-2
focus:ring-accent-300
focus:ring-offset-2
```

---

## 4. Tabs Component

### Import
```tsx
import { Tabs } from "@/components/ui";
```

### Props
```tsx
interface Tab {
  id: string;
  label: string;
  content: ReactNode;
  icon?: ReactNode;
  badge?: number;
}

interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
  onTabChange?: (tabId: string) => void;
}
```

### Exemples

#### Simple Tabs
```tsx
<Tabs
  tabs={[
    { id: "all", label: "Tous", content: <AllContent /> },
    { id: "draft", label: "Brouillon", content: <DraftContent /> },
    { id: "published", label: "Publié", content: <PublishedContent /> },
  ]}
  defaultTab="all"
/>
```

#### Tabs avec Badges et Callback
```tsx
<Tabs
  tabs={STATUS_FILTERS.map((filter) => ({
    id: filter.value,
    label: filter.label,
    content: null,  // Afficher le contenu en dehors de Tabs
    badge: counts[filter.value],  // Affiche le count du filtre
  }))}
  defaultTab={selectedFilter}
  onTabChange={setSelectedFilter}
/>
```

#### Tabs avec Icons
```tsx
<Tabs
  tabs={[
    {
      id: "messages",
      label: "Messages",
      icon: <Mail className="w-4 h-4" />,
      content: <MessagesContent />,
      badge: unreadCount
    },
    {
      id: "calls",
      label: "Appels",
      icon: <Phone className="w-4 h-4" />,
      content: <CallsContent />,
      badge: missedCalls
    },
  ]}
/>
```

### Display Details

#### Badge Display
- Affiche si `badge !== undefined && badge > 0`
- Style: `bg-accent-100 text-accent-700 rounded-full`
- Position: à droite du label

#### Animated Indicator
- Underline bar rouge d'accent
- Transition smooth vers l'onglet actif
- Position: `bottom-0 h-0.5`

---

## 5. DataTable Component

### Import
```tsx
import { DataTable } from "@/components/ui";
```

### Props
```tsx
interface Column<T> {
  key: string;
  label: string;
  render?: (item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (item: T) => void;
  pagination?: {
    page: number;
    perPage: number;
    total: number;
    onPageChange: (page: number) => void;
  };
}
```

### Exemples

#### Simple Table
```tsx
<DataTable
  data={items}
  columns={[
    { key: "name", label: "Nom" },
    { key: "email", label: "Email" },
    { key: "status", label: "Statut" },
  ]}
/>
```

#### Table avec Custom Renders
```tsx
<DataTable
  data={calls}
  columns={[
    {
      key: "date",
      label: "Date",
      render: (call) => new Date(call.date).toLocaleDateString("fr-FR")
    },
    {
      key: "direction",
      label: "Direction",
      render: (call) => (
        <Badge
          variant={call.direction === "INBOUND" ? "success" : "accent"}
          dot
          size="sm"
        >
          {call.direction === "INBOUND" ? "Entrant" : "Sortant"}
        </Badge>
      )
    },
  ]}
  onRowClick={(call) => navigate(`/calls/${call.id}`)}
/>
```

#### Table avec Pagination
```tsx
<DataTable
  data={filteredItems}
  columns={tableColumns}
  pagination={{
    page: currentPage,
    perPage: 20,
    total: totalCount,
    onPageChange: setCurrentPage,
  }}
  onRowClick={(item) => navigate(`/items/${item.id}`)}
/>
```

### Row Styling
```css
/* Header */
bg-neutral-50 border-b border-neutral-200
text-xs font-medium text-neutral-700 uppercase

/* Rows */
divide-y divide-neutral-200
hover:bg-neutral-50 cursor-pointer (if clickable)

/* Pagination */
border-t border-neutral-200
flex justify-between items-center
```

---

## Patterns Communs

### Pattern 1: Listes d'éléments

```tsx
<div className="space-y-3">
  {items.map((item) => (
    <Card key={item.id} hover onClick={() => navigate(item.id)}>
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-lg bg-accent-50" />
        <div className="flex-1">
          <h3 className="font-medium">{item.title}</h3>
          <p className="text-sm text-neutral-600">{item.description}</p>
        </div>
      </div>
    </Card>
  ))}
</div>
```

### Pattern 2: Stats Grid

```tsx
<div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
  {stats.map((stat) => (
    <Card key={stat.id} className="hover:shadow-lg transition-shadow">
      <StatCard
        title={stat.title}
        value={stat.value}
        icon={stat.icon}
        color={stat.color}
      />
    </Card>
  ))}
</div>
```

### Pattern 3: Filtrage avec Tabs

```tsx
const [filter, setFilter] = useState("all");

<Tabs
  tabs={filters.map((f) => ({
    id: f.id,
    label: f.label,
    content: null,
    badge: counts[f.id],
  }))}
  defaultTab="all"
  onTabChange={setFilter}
/>

{/* Afficher le contenu filtré en dehors des Tabs */}
<div className="space-y-3 mt-6">
  {filteredItems.map((item) => (
    <ItemCard key={item.id} item={item} />
  ))}
</div>
```

### Pattern 4: Header avec Buttons

```tsx
<div className="flex items-center justify-between mb-6">
  <div>
    <h1 className="text-2xl font-bold">Titre</h1>
    <p className="text-neutral-500 text-sm mt-1">Description</p>
  </div>
  <div className="flex gap-2">
    <Button variant="secondary">Annuler</Button>
    <Button variant="primary" onClick={handleAction}>
      Action
    </Button>
  </div>
</div>
```

### Pattern 5: Dropdown avec Chevron

```tsx
<div className="relative inline-block">
  <select
    value={selected}
    onChange={handleChange}
    className="appearance-none px-4 py-2 border border-neutral-200 rounded-lg pr-8"
  >
    <option>Option 1</option>
    <option>Option 2</option>
  </select>
  <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none" />
</div>
```

---

## Colors Reference

### Base Colors
```
accent: #7C3AED (Violet)
success: #10B981 (Vert)
warning: #F59E0B (Orange)
danger: #EF4444 (Rouge)
neutral-50 à 900: Gris
```

### Variants
- `{color}-50`: Très clair (backgrounds)
- `{color}-100`: Clair (badges, hovers)
- `{color}-600`: Standard (text, icons)
- `{color}-700`: Foncé (text hover)

---

## Tailwind Classes Essentiels

### Spacing
```css
gap-2, gap-4, gap-6          /* Gaps */
p-2, p-4, p-6                /* Padding */
mt-1, mt-2, mb-3 mb-6        /* Margins */
```

### Typography
```css
text-xs, text-sm, text-base, text-lg
font-medium, font-semibold, font-bold
truncate, line-clamp-2
```

### Effects
```css
shadow-subtle, shadow-md, shadow-lg
rounded-lg, rounded-full
border, border-2
hover:shadow-lg, hover:bg-neutral-50
transition-all, transition-shadow duration-normal
```

### States
```css
disabled:opacity-50, disabled:cursor-not-allowed
hover:scale-[1.02], active:scale-[0.98]
animate-spin, animate-pulse, animate-fadeIn
focus:outline-none, focus:ring-2, focus:ring-offset-2
```

---

## Best Practices

1. **Cards**: Toujours wrapper les contenus dans Cards pour cohérence
2. **Badges**: Utiliser pour les statuts, counts, tags
3. **Buttons**: Primary pour actions principales, secondary pour alternatives
4. **Tabs**: Avec badges pour montrer counts/importances
5. **Tables**: Avec row click pour navigation
6. **Spacing**: Utiliser gap-3 pour listes, gap-4 pour grids
7. **Colors**: Maintenir cohérence (success=valid, warning=pending, danger=error)
8. **Icons**: De lucide-react, classe w-4 h-4 ou w-5 h-5 pour cohérence

---

## Checklist de Cohérence

- [ ] Toutes les sections sont en Cards
- [ ] Stats cards sont wrappés dans Cards avec hover
- [ ] Les badges utilisent les variantes correctes
- [ ] Les boutons utilisent les bons variants
- [ ] Les listes ont space-y-3 entre items
- [ ] Les icônes sont de lucide-react
- [ ] Le responsive grid est utilisé pour les grids
- [ ] Les colors correspondent aux variants définis
- [ ] Focus states sont visibles
- [ ] Loading states utilisent le prop `loading` de Button

