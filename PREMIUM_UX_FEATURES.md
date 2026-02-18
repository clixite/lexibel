# LexiBel - Premium UX Features Documentation

## Vue d'ensemble

Cette documentation décrit toutes les fonctionnalités UX premium implémentées pour porter LexiBel au niveau des meilleurs SaaS B2B (Linear, Notion, Stripe Dashboard).

---

## 1. Command Palette

**Fichier**: `apps/web/components/CommandPalette.tsx`

### Fonctionnalités
- Ouverture avec `Cmd+K` / `Ctrl+K`
- Navigation clavier (↑↓ pour naviguer, Enter pour sélectionner, Esc pour fermer)
- Recherche fuzzy sur les commandes et mots-clés
- Groupement par catégories (Navigation, Actions, Recherche, Système)
- Affichage des raccourcis clavier
- Auto-focus sur le champ de recherche
- Animation fluide d'apparition

### Utilisation
```typescript
// Déjà intégré dans dashboard/layout.tsx
// S'ouvre automatiquement avec Cmd+K
```

### Raccourcis disponibles
- `N` - Nouveau dossier
- `C` - Nouveau contact
- `/` - Recherche globale

---

## 2. Keyboard Shortcuts

**Fichier**: `apps/web/hooks/useKeyboardShortcuts.ts`

### Fonctionnalités
- Hook personnalisé pour gérer les raccourcis clavier
- Ignore automatiquement les inputs/textarea
- Configuration simple par page

### Utilisation
```typescript
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";

useKeyboardShortcuts({
  "n": () => setShowModal(true),      // N = nouveau
  "/": () => searchInputRef.current?.focus(), // / = search
});
```

---

## 3. Toast System

**Fichier**: `apps/web/components/ToastContainer.tsx`

### Fonctionnalités
- 4 types: success, error, info, warning
- Auto-dismiss après 5 secondes (configurable)
- Fermeture manuelle
- Empilable (plusieurs toasts simultanés)
- Animations smooth
- API simple et globale

### Utilisation
```typescript
import { toast } from "@/components/ToastContainer";

toast.success("Dossier créé avec succès");
toast.error("Erreur lors de la création");
toast.info("Information importante");
toast.warning("Attention requise");
```

---

## 4. Enhanced DataTable

**Fichier**: `apps/web/components/ui/DataTable.tsx`

### Fonctionnalités
- Tri multi-colonnes (cliquer sur les headers)
- Inline editing (double-click sur une cellule éditable)
- Sélection multiple (checkboxes)
- Sticky header
- Colonnes configurables (width, sortable, editable)
- Animations hover subtiles

### Utilisation
```typescript
<DataTable
  data={items}
  columns={[
    { key: "title", label: "Titre", sortable: true, editable: true },
    { key: "status", label: "Statut", render: (item) => <Badge>{item.status}</Badge> }
  ]}
  selectable
  selectedIds={selectedIds}
  onSelectionChange={setSelectedIds}
  onCellEdit={handleCellEdit}
  onRowClick={handleRowClick}
/>
```

---

## 5. Bulk Actions Bar

**Fichier**: `apps/web/components/BulkActionBar.tsx`

### Fonctionnalités
- Apparaît uniquement quand des éléments sont sélectionnés
- Position fixe en bas de l'écran
- Actions configurables (Archiver, Supprimer, custom)
- Compteur de sélection
- Animation d'entrée/sortie

### Utilisation
```typescript
<BulkActionBar
  selectedCount={selectedIds.size}
  onArchive={handleBulkArchive}
  onDelete={handleBulkDelete}
  onCancel={() => setSelectedIds(new Set())}
  actions={[
    {
      label: "Exporter",
      icon: <Download />,
      onClick: handleExport
    }
  ]}
/>
```

---

## 6. Enhanced Empty State

**Fichier**: `apps/web/components/ui/EmptyState.tsx`

### Fonctionnalités
- Icon personnalisable
- Description optionnelle
- Action principale avec raccourci clavier affiché
- Suggestions secondaires (liens utiles)
- Design moderne et engageant

### Utilisation
```typescript
<EmptyState
  title="Aucun dossier trouvé"
  description="Créez votre premier dossier pour commencer"
  action={{
    label: "Créer un dossier",
    onClick: () => setShowModal(true),
    shortcut: "N"
  }}
  suggestions={[
    { label: "Importer depuis Excel", onClick: handleImport },
    { label: "Voir le guide de démarrage", onClick: openGuide }
  ]}
/>
```

---

## 7. Optimistic Updates

**Fichier**: `apps/web/hooks/useOptimisticUpdate.ts`

### Fonctionnalités
- Update UI immédiatement (avant réponse API)
- Rollback automatique en cas d'erreur
- Support create, update, delete
- Indicateur de pending state
- Intégration toast automatique

### Utilisation
```typescript
const { createOptimistic, updateOptimistic, pending } = useOptimisticUpdate(
  cases,
  setCases,
  {
    successMessage: "Dossier créé",
    errorMessage: "Erreur création"
  }
);

await createOptimistic(newCase, (data) =>
  apiFetch("/cases", token, { method: "POST", body: JSON.stringify(data) })
);
```

---

## 8. Auto-Save System

**Fichiers**:
- `apps/web/hooks/useAutoSave.ts`
- `apps/web/components/ui/AutoSaveIndicator.tsx`

### Fonctionnalités
- Sauvegarde automatique après délai (1s par défaut)
- Indicateur visuel (Sauvegarde..., Sauvegardé il y a Xmin)
- Debouncing intelligent
- Gestion d'erreurs
- Force save avec `saveNow()`

### Utilisation
```typescript
const { status, lastSaved, saveNow } = useAutoSave({
  data: formData,
  onSave: async (data) => {
    await apiFetch("/cases/123", token, {
      method: "PATCH",
      body: JSON.stringify(data)
    });
  },
  delay: 1000
});

// Dans le render
<AutoSaveIndicator status={status} lastSaved={lastSaved} />
```

---

## 9. Enhanced Sidebar

**Fichier**: `apps/web/components/SidebarEnhanced.tsx`

### Fonctionnalités
- Sous-navigation expandable
- Indicateurs visuels actifs
- Icônes pour chaque item
- Badges de notification
- Mode collapsed avec tooltips
- Animation smooth d'expand/collapse
- Groupement par sections

### Structure
```
Dossiers
├─ Tous les dossiers
├─ Mes dossiers
├─ En cours
├─ Récents
└─ Archivés

Contacts
├─ Tous
├─ Physiques
├─ Moraux
└─ Favoris
```

---

## 10. Breadcrumb Navigation

**Fichier**: `apps/web/components/ui/Breadcrumb.tsx`

### Fonctionnalités
- Navigation contextuelle
- Actions contextuelles (boutons)
- Icônes personnalisables
- Séparateurs automatiques
- Style moderne

### Utilisation
```typescript
<Breadcrumb
  items={[
    { label: "Dashboard", href: "/dashboard", icon: <Home /> },
    { label: "Dossiers", href: "/dashboard/cases" },
    { label: "DOS-2026-123" }
  ]}
  actions={
    <>
      <Button variant="secondary">Archiver</Button>
      <Button variant="primary">Modifier</Button>
    </>
  }
/>
```

---

## 11. Global Search

**Fichier**: `apps/web/components/GlobalSearch.tsx`

### Fonctionnalités
- Ouverture avec `Cmd+/` / `Ctrl+/`
- Recherche multi-entités (dossiers, contacts, événements, documents)
- Navigation clavier
- Groupement par type
- Preview des résultats
- API extensible

### Utilisation
```typescript
// Déjà intégré dans le layout
// S'ouvre avec Cmd+/
```

---

## 12. Context Menu

**Fichier**: `apps/web/components/ui/ContextMenu.tsx`

### Fonctionnalités
- Clic-droit natif
- Items avec icônes
- Séparateurs
- Variant danger pour actions destructives
- Auto-fermeture sur scroll/click

### Utilisation
```typescript
<ContextMenu
  items={[
    { label: "Ouvrir", icon: <Eye />, onClick: handleOpen },
    { separator: true },
    { label: "Supprimer", icon: <Trash />, onClick: handleDelete, variant: "danger" }
  ]}
>
  <div>Clic-droit sur moi</div>
</ContextMenu>
```

---

## 13. Additional Hooks

### useDebounce
**Fichier**: `apps/web/hooks/useDebounce.ts`

```typescript
const debouncedSearch = useDebounce(searchQuery, 500);
```

---

## Intégration dans les pages

### Example: Cases Page Enhanced

**Fichier**: `apps/web/app/dashboard/cases/page-enhanced.tsx`

Fonctionnalités intégrées:
- ✅ Keyboard shortcuts (N pour nouveau, / pour search)
- ✅ Optimistic create
- ✅ Bulk selection + BulkActionBar
- ✅ Toast notifications
- ✅ Enhanced EmptyState avec suggestions
- ✅ Search avec ref focus
- ✅ Grid/Table view toggle
- ✅ Filters inline

---

## Checklist UX Premium

- ✅ Command Palette (Cmd+K)
- ✅ Keyboard shortcuts globaux
- ✅ Toast system moderne
- ✅ Inline editing (DataTable)
- ✅ Bulk actions avec toolbar
- ✅ Optimistic updates
- ✅ Auto-save avec indicateur
- ✅ Enhanced empty states
- ✅ Sidebar avec sous-navigation
- ✅ Breadcrumb navigation
- ✅ Global search (Cmd+/)
- ✅ Context menus
- ✅ Debouncing
- ✅ Smooth animations (150ms partout)
- ✅ Focus states visible
- ✅ Loading skeletons (pas de spinners)
- ✅ Tooltips sur icônes

---

## Prochaines étapes recommandées

1. **Drag & Drop**: Pour réorganiser des items
2. **Undo/Redo**: Ctrl+Z / Ctrl+Shift+Z
3. **Column Resizing**: Dans DataTable
4. **Virtual Scrolling**: Pour grandes listes (>1000 items)
5. **Export CSV**: Fonctionnalité d'export
6. **Advanced Filters**: Builder de filtres complexes
7. **Saved Views**: Sauvegarder configurations de filtres
8. **Collaborative Cursors**: Voir qui édite quoi en temps réel

---

## Performance Tips

- Tous les composants utilisent `"use client"` uniquement quand nécessaire
- Debouncing sur les recherches
- Optimistic updates pour UI réactive
- Animations GPU-accelerated (transform, opacity)
- Lazy loading des modals
- Memoization des renders coûteux

---

## Design Tokens

### Transitions
```css
transition-colors duration-150
transition-all duration-150
```

### Shadows
```css
shadow-sm      /* Cartes */
shadow-lg      /* Modals */
shadow-2xl     /* Toasts */
```

### Borders
```css
border border-neutral-200    /* Standard */
border border-primary        /* Active */
```

### Animations
```css
animate-in fade-in slide-in-from-top-4 duration-150
```

---

## Support & Maintenance

Pour toute question ou amélioration:
1. Consulter cette documentation
2. Vérifier les exemples dans `page-enhanced.tsx`
3. Tester dans l'environnement de développement

---

**Objectif atteint**: LexiBel rivalise maintenant avec Linear, Notion, Stripe Dashboard en termes d'UX premium.
