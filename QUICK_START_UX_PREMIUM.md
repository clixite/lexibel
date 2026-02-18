# Quick Start - Premium UX Features

## Démarrage Rapide (5 minutes)

### Étape 1: Tester les Features Globales

1. **Démarrer l'application**
```bash
cd F:\LexiBel\apps\web
npm run dev
```

2. **Tester la Command Palette**
- Ouvrez http://localhost:3000/dashboard
- Appuyez sur `Cmd+K` (Mac) ou `Ctrl+K` (Windows)
- Tapez "dossiers" et sélectionnez
- ✅ Navigation instantanée

3. **Tester les Toasts**
- Naviguez vers /dashboard/cases
- Cliquez sur "Nouveau dossier"
- Créez un dossier
- ✅ Toast de confirmation apparaît

4. **Tester les Keyboard Shortcuts**
- Sur /dashboard/cases
- Appuyez sur `N` → Modal de création s'ouvre
- Appuyez sur `/` → Focus sur la recherche
- ✅ Navigation au clavier

---

## Intégration dans une Page (10 minutes)

### Exemple: Ajouter Keyboard Shortcuts

```typescript
// Dans votre page
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { useRef } from "react";

export default function MyPage() {
  const searchRef = useRef<HTMLInputElement>(null);

  // Ajoutez les shortcuts
  useKeyboardShortcuts({
    "n": () => setShowModal(true),
    "/": () => searchRef.current?.focus(),
  });

  return (
    <div>
      <input ref={searchRef} placeholder="Rechercher..." />
    </div>
  );
}
```

### Exemple: Ajouter des Toasts

```typescript
// Remplacez vos alertes/notifications
import { toast } from "@/components/ToastContainer";

// Avant
alert("Création réussie");

// Après
toast.success("Dossier créé avec succès");
toast.error("Erreur lors de la création");
toast.info("Information importante");
```

### Exemple: Bulk Actions

```typescript
const [selected, setSelected] = useState<Set<string>>(new Set());

// Dans votre JSX
<BulkActionBar
  selectedCount={selected.size}
  onArchive={async () => {
    await bulkArchive(Array.from(selected));
    toast.success(`${selected.size} dossiers archivés`);
    setSelected(new Set());
  }}
  onDelete={async () => {
    await bulkDelete(Array.from(selected));
    toast.success(`${selected.size} dossiers supprimés`);
    setSelected(new Set());
  }}
  onCancel={() => setSelected(new Set())}
/>
```

---

## Tester la Page Enhanced (2 minutes)

### Option 1: Activer page-enhanced.tsx

```bash
# Renommer les fichiers
cd F:\LexiBel\apps\web\app\dashboard\cases
mv page.tsx page.old.tsx
mv page-enhanced.tsx page.tsx

# Redémarrer
npm run dev
```

### Option 2: Voir l'exemple directement

```bash
# Ouvrir le fichier
code apps/web/app/dashboard/cases/page-enhanced.tsx

# Copier/coller dans votre page
```

### Features à tester:
- ✅ Sélection multiple (checkboxes)
- ✅ Bulk actions (archiver, supprimer)
- ✅ Keyboard shortcuts (N, /)
- ✅ Optimistic create
- ✅ Enhanced empty state
- ✅ Toast notifications

---

## Composants Clés à Essayer

### 1. Command Palette
```typescript
// Déjà intégré dans layout.tsx
// Ouvrir avec Cmd+K
```

### 2. Toast System
```typescript
import { toast } from "@/components/ToastContainer";
toast.success("Action réussie");
```

### 3. DataTable Premium
```typescript
<DataTable
  data={items}
  columns={[
    { key: "title", label: "Titre", sortable: true, editable: true }
  ]}
  selectable
  selectedIds={selectedIds}
  onSelectionChange={setSelectedIds}
/>
```

### 4. Empty State
```typescript
<EmptyState
  title="Aucun résultat"
  description="Essayez une autre recherche"
  action={{
    label: "Créer un dossier",
    onClick: () => setShowModal(true),
    shortcut: "N"
  }}
  suggestions={[
    { label: "Réinitialiser filtres", onClick: reset }
  ]}
/>
```

### 5. Auto-Save
```typescript
const { status, lastSaved } = useAutoSave({
  data: formData,
  onSave: async (data) => {
    await api.save(data);
  }
});

// Dans le JSX
<AutoSaveIndicator status={status} lastSaved={lastSaved} />
```

---

## Raccourcis Clavier Disponibles

### Globaux (dans tout le dashboard)
- `Cmd+K` / `Ctrl+K` → Command Palette
- `Cmd+/` / `Ctrl+/` → Global Search
- `Esc` → Fermer modals/palettes

### Page Cases
- `N` → Nouveau dossier
- `/` → Focus recherche

### DataTable
- Double-click → Éditer cellule
- `Enter` → Sauvegarder
- `Esc` → Annuler

---

## Checklist de Test

### Navigation
- [ ] Command Palette s'ouvre avec Cmd+K
- [ ] Recherche filtre les commandes
- [ ] Navigation clavier fonctionne (↑↓)
- [ ] Sélection redirige correctement

### Feedback
- [ ] Toasts s'affichent correctement
- [ ] Auto-dismiss après 5 secondes
- [ ] Fermeture manuelle fonctionne
- [ ] Plusieurs toasts empilables

### Interactions
- [ ] Keyboard shortcuts fonctionnent
- [ ] Pas de conflit avec inputs
- [ ] Focus recherche avec /
- [ ] Modal s'ouvre avec N

### Bulk Actions
- [ ] Checkboxes sélectionnent
- [ ] BulkActionBar apparaît
- [ ] Actions bulk fonctionnent
- [ ] Annulation fonctionne

### DataTable
- [ ] Tri par colonne fonctionne
- [ ] Double-click pour éditer
- [ ] Enter sauvegarde, Esc annule
- [ ] Sélection multiple fonctionne

---

## Dépannage

### Command Palette ne s'ouvre pas
- Vérifier que `CommandPalette` est dans `layout.tsx`
- Vérifier que vous êtes sur une page `/dashboard/*`
- Essayer de rafraîchir la page

### Toasts ne s'affichent pas
- Vérifier que `ToastContainer` est dans `layout.tsx`
- Vérifier l'import: `import { toast } from "@/components/ToastContainer"`
- Vérifier la console pour les erreurs

### Keyboard shortcuts ne fonctionnent pas
- Vérifier que vous n'êtes pas dans un input/textarea
- Vérifier que le hook est appelé: `useKeyboardShortcuts({...})`
- Vérifier que la page est montée (pas en loading)

### Build errors
- Vérifier que tous les imports sont corrects
- Vérifier les types TypeScript
- Essayer: `npm run build` pour voir les erreurs détaillées

---

## Prochaines Étapes

### Court Terme
1. Tester toutes les features sur /dashboard/cases
2. Migrer /dashboard/contacts avec les mêmes patterns
3. Ajouter auto-save aux formulaires d'édition

### Moyen Terme
4. Ajouter Context Menu sur les listes
5. Implémenter Drag & Drop
6. Ajouter Undo/Redo

### Long Terme
7. Column resizing dans DataTable
8. Virtual scrolling pour grandes listes
9. Saved views (filtres sauvegardés)

---

## Documentation Complète

- **PREMIUM_UX_FEATURES.md** - Documentation détaillée de chaque feature
- **MIGRATION_GUIDE.md** - Guide de migration complet
- **UX_PREMIUM_SUMMARY.md** - Résumé exécutif

---

## Support

Questions? Consultez:
1. Les exemples dans `page-enhanced.tsx`
2. La documentation complète
3. Les composants source dans `apps/web/components/`

---

**Temps Total**: ~15 minutes pour tout tester
**Difficulté**: ⭐⭐ Facile
**Impact UX**: ⭐⭐⭐⭐⭐ Majeur
