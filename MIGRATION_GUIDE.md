# Guide de Migration - Premium UX Features

## Étape 1: Activer la nouvelle Sidebar (Optionnel)

Si vous souhaitez activer la sidebar avec sous-navigation:

### Dans `apps/web/app/dashboard/layout.tsx`

```typescript
// Remplacer
import Sidebar from "@/components/Sidebar";

// Par
import Sidebar from "@/components/SidebarEnhanced";
```

---

## Étape 2: Utiliser la page Cases améliorée

### Option A: Remplacer complètement

```bash
# Renommer l'ancienne page
mv apps/web/app/dashboard/cases/page.tsx apps/web/app/dashboard/cases/page.old.tsx

# Renommer la nouvelle page
mv apps/web/app/dashboard/cases/page-enhanced.tsx apps/web/app/dashboard/cases/page.tsx
```

### Option B: Intégration progressive

Copiez les fonctionnalités de `page-enhanced.tsx` dans votre page actuelle:

1. **Ajoutez les imports**:
```typescript
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { toast } from "@/components/ToastContainer";
import BulkActionBar from "@/components/BulkActionBar";
```

2. **Ajoutez le state pour la sélection**:
```typescript
const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
```

3. **Ajoutez les keyboard shortcuts**:
```typescript
const searchInputRef = useRef<HTMLInputElement>(null);

useKeyboardShortcuts({
  n: () => setShowModal(true),
  "/": () => searchInputRef.current?.focus(),
});
```

4. **Remplacez les toast inline par le système global**:
```typescript
// Avant
setSuccess("Dossier créé avec succès");

// Après
toast.success("Dossier créé avec succès");
```

5. **Ajoutez le BulkActionBar**:
```typescript
<BulkActionBar
  selectedCount={selectedIds.size}
  onArchive={handleBulkArchive}
  onDelete={handleBulkDelete}
  onCancel={() => setSelectedIds(new Set())}
/>
```

6. **Ajoutez les checkboxes dans le tableau**:
```typescript
<th className="px-4 py-4 w-12">
  <input
    type="checkbox"
    checked={filtered.length > 0 && selectedIds.size === filtered.length}
    onChange={handleSelectAll}
    className="rounded border-neutral-300 text-primary focus:ring-primary"
  />
</th>
```

---

## Étape 3: Améliorer l'EmptyState

### Avant
```typescript
<EmptyState title="Aucun dossier trouvé" />
```

### Après
```typescript
<EmptyState
  title="Aucun dossier trouvé"
  description="Créez votre premier dossier pour commencer"
  action={{
    label: "Créer votre premier dossier",
    onClick: () => setShowModal(true),
    shortcut: "N",
  }}
  suggestions={[
    {
      label: "Réinitialiser tous les filtres",
      onClick: () => {
        setSearchQuery("");
        setStatusFilter("");
        setTypeFilter("");
      },
    },
  ]}
/>
```

---

## Étape 4: Implémenter Auto-Save (pour les formulaires d'édition)

### Dans une page d'édition de dossier

```typescript
import { useAutoSave } from "@/hooks/useAutoSave";
import AutoSaveIndicator from "@/components/ui/AutoSaveIndicator";

// Dans le composant
const [formData, setFormData] = useState(initialData);

const { status, lastSaved } = useAutoSave({
  data: formData,
  onSave: async (data) => {
    await apiFetch(`/cases/${id}`, token, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },
  delay: 1000,
});

// Dans le render
<div className="flex items-center justify-between">
  <h1>Éditer le dossier</h1>
  <AutoSaveIndicator status={status} lastSaved={lastSaved} />
</div>
```

---

## Étape 5: Utiliser le DataTable amélioré

### Avant
```typescript
<DataTable
  data={items}
  columns={columns}
  onRowClick={handleClick}
/>
```

### Après
```typescript
<DataTable
  data={items}
  columns={[
    { key: "title", label: "Titre", sortable: true, editable: true },
    { key: "status", label: "Statut", sortable: true },
  ]}
  selectable
  selectedIds={selectedIds}
  onSelectionChange={setSelectedIds}
  onCellEdit={async (item, key, value) => {
    await apiFetch(`/items/${item.id}`, token, {
      method: "PATCH",
      body: JSON.stringify({ [key]: value }),
    });
    toast.success("Modifié avec succès");
  }}
  onRowClick={handleClick}
/>
```

---

## Étape 6: Ajouter un Breadcrumb

### Dans une page de détail

```typescript
import Breadcrumb from "@/components/ui/Breadcrumb";

<Breadcrumb
  items={[
    { label: "Dashboard", href: "/dashboard", icon: <Home className="w-4 h-4" /> },
    { label: "Dossiers", href: "/dashboard/cases" },
    { label: caseData.reference },
  ]}
  actions={
    <>
      <Button variant="secondary" onClick={handleArchive}>
        Archiver
      </Button>
      <Button variant="primary" onClick={handleEdit}>
        Modifier
      </Button>
    </>
  }
/>
```

---

## Étape 7: Ajouter un Context Menu

### Pour les actions rapides sur un élément

```typescript
import ContextMenu from "@/components/ui/ContextMenu";

<ContextMenu
  items={[
    { label: "Ouvrir", icon: <Eye />, onClick: () => router.push(`/cases/${id}`) },
    { label: "Dupliquer", icon: <Copy />, onClick: handleDuplicate },
    { separator: true },
    { label: "Archiver", icon: <Archive />, onClick: handleArchive },
    { label: "Supprimer", icon: <Trash />, onClick: handleDelete, variant: "danger" },
  ]}
>
  <div className="case-card">
    {/* Votre contenu */}
  </div>
</ContextMenu>
```

---

## Étape 8: Optimistic Updates

### Avant
```typescript
const handleCreate = async () => {
  try {
    const result = await apiFetch("/cases", token, { method: "POST", body });
    setCases([...cases, result]);
    toast.success("Créé");
  } catch (err) {
    toast.error("Erreur");
  }
};
```

### Après
```typescript
import { useOptimisticUpdate } from "@/hooks/useOptimisticUpdate";

const { createOptimistic } = useOptimisticUpdate(cases, setCases, {
  successMessage: "Dossier créé",
  errorMessage: "Erreur création",
});

const handleCreate = async () => {
  await createOptimistic(newCaseData, (data) =>
    apiFetch("/cases", token, { method: "POST", body: JSON.stringify(data) })
  );
};
```

---

## Étape 9: Debounced Search

### Avant
```typescript
const [searchQuery, setSearchQuery] = useState("");

// Recherche à chaque frappe
useEffect(() => {
  searchAPI(searchQuery);
}, [searchQuery]);
```

### Après
```typescript
import { useDebounce } from "@/hooks/useDebounce";

const [searchQuery, setSearchQuery] = useState("");
const debouncedSearch = useDebounce(searchQuery, 500);

useEffect(() => {
  if (debouncedSearch) {
    searchAPI(debouncedSearch);
  }
}, [debouncedSearch]);
```

---

## Checklist de Migration

### Pages à migrer

- [ ] `/dashboard/cases` - Liste des dossiers
- [ ] `/dashboard/cases/[id]` - Détail d'un dossier
- [ ] `/dashboard/contacts` - Liste des contacts
- [ ] `/dashboard/contacts/[id]` - Détail d'un contact
- [ ] `/dashboard/timeline` - Timeline
- [ ] `/dashboard/calendar` - Calendrier
- [ ] `/dashboard/billing` - Facturation

### Composants à remplacer

- [ ] Toasts inline → `toast.success()`, `toast.error()`
- [ ] Empty states basiques → `EmptyState` avec suggestions
- [ ] DataTable basique → DataTable avec sort/edit/select
- [ ] Pas de keyboard shortcuts → `useKeyboardShortcuts`
- [ ] Pas d'optimistic updates → `useOptimisticUpdate`
- [ ] Search non-debouncé → `useDebounce`

---

## Tests après Migration

### 1. Command Palette
- [ ] `Cmd+K` / `Ctrl+K` ouvre la palette
- [ ] Navigation clavier fonctionne
- [ ] Recherche filtre les commandes
- [ ] Sélection redirige correctement

### 2. Toasts
- [ ] Success toast s'affiche
- [ ] Error toast s'affiche
- [ ] Auto-dismiss après 5s
- [ ] Fermeture manuelle fonctionne

### 3. Keyboard Shortcuts
- [ ] `N` ouvre modal de création
- [ ] `/` focus le champ de recherche
- [ ] Pas de conflits avec inputs

### 4. Bulk Actions
- [ ] Sélection multiple fonctionne
- [ ] BulkActionBar apparaît
- [ ] Actions bulk fonctionnent
- [ ] Annulation fonctionne

### 5. DataTable
- [ ] Tri sur colonnes fonctionne
- [ ] Double-click pour éditer
- [ ] Enter pour sauvegarder
- [ ] Escape pour annuler

### 6. Optimistic Updates
- [ ] UI update immédiat
- [ ] Rollback en cas d'erreur
- [ ] Toast de confirmation

### 7. Auto-Save
- [ ] Indicateur visible
- [ ] Sauvegarde après 1s
- [ ] "Sauvegardé il y a Xmin" correct

---

## Support

En cas de problème:
1. Vérifier la console pour les erreurs
2. Consulter `PREMIUM_UX_FEATURES.md`
3. Vérifier les exemples dans `page-enhanced.tsx`

---

## Prochaines étapes recommandées

1. Migrer toutes les pages liste (cases, contacts)
2. Ajouter auto-save aux formulaires d'édition
3. Ajouter context menus partout
4. Optimiser toutes les mutations avec optimistic updates
5. Ajouter des breadcrumbs aux pages de détail
