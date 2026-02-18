# Premium Pages Changelog

**Mission:** Refactored Cases + Contacts pages with premium design system
**Status:** ✓ COMPLETED
**Date:** February 17, 2026

---

## CASES PAGE - Detailed Changes

### File: `F:/LexiBel/apps/web/app/dashboard/cases/page.tsx`

#### State Management
```diff
- const [statusFilter, setStatusFilter] = useState("");
+ const [statusFilter, setStatusFilter] = useState("");
+ const [typeFilter, setTypeFilter] = useState("");
+ const [viewMode, setViewMode] = useState<"table" | "grid">("table");
```

#### Filtering Logic
```diff
const filtered = cases.filter((c) => {
  if (statusFilter && c.status !== statusFilter) return false;
+ if (typeFilter && c.matter_type !== typeFilter) return false;
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    return (
      c.title.toLowerCase().includes(q) ||
      c.reference.toLowerCase().includes(q)
    );
  }
  return true;
});
```

#### Imports
```diff
- import { Plus, Loader2, Search, Folder, X, Check } from "lucide-react";
+ import { Plus, Loader2, Search, Grid3x3, List, X, Check, ChevronRight } from "lucide-react";
- import { LoadingSkeleton, ErrorState, EmptyState, Badge, Modal } from "@/components/ui";
+ import { LoadingSkeleton, ErrorState, EmptyState, Badge, Modal, Button, Card } from "@/components/ui";
```

#### Main Container
```diff
- return (
-   <div>
+ return (
+   <div className="space-y-6">
```

#### Toast Styling
```diff
- <div className="fixed top-4 right-4 z-50 bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md text-sm flex items-center gap-2 shadow-lg animate-in fade-in">
+ <div className="fixed top-4 right-4 z-50 bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2 shadow-lg animate-in fade-in">
```

#### Header Section - MAJOR REDESIGN
```diff
- {/* Header */}
- <div className="flex items-center justify-between mb-6">
-   <div className="flex items-center gap-3">
-     <h1 className="text-2xl font-bold text-neutral-900">Dossiers</h1>
-     <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
-       {cases.length}
-     </span>
-   </div>
-   <button
-     onClick={() => setShowModal(true)}
-     className="btn-primary flex items-center gap-2"
-   >
-     <Plus className="w-4 h-4" />
-     Nouveau dossier
-   </button>
- </div>

+ {/* Premium Header Section */}
+ <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
+   <div>
+     <h1 className="text-4xl font-display font-semibold text-neutral-900 mb-2">
+       Dossiers
+     </h1>
+     <p className="text-neutral-500 text-sm">
+       Gérez et suivez tous vos dossiers clients
+     </p>
+   </div>
+   <Button
+     variant="primary"
+     size="lg"
+     icon={<Plus className="w-5 h-5" />}
+     onClick={() => setShowModal(true)}
+   >
+     Nouveau dossier
+   </Button>
+ </div>
```

#### Filter Bar - MAJOR REDESIGN
```diff
- {/* Filter bar */}
- <div className="flex flex-wrap items-center gap-3 mb-6">
-   <div className="flex gap-1 bg-neutral-100 rounded-md p-1">
-     {STATUS_FILTERS.map((f) => (
-       <button
-         key={f.value}
-         onClick={() => setStatusFilter(f.value)}
-         className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 ${
-           statusFilter === f.value
-             ? "bg-white text-neutral-900 shadow-subtle"
-             : "text-neutral-500 hover:text-neutral-700"
-         }`}
-       >
-         {f.label}
-       </button>
-     ))}
-   </div>
-   <div className="relative flex-1 max-w-xs">
-     <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
-     <input
-       type="text"
-       placeholder="Rechercher un dossier..."
-       value={searchQuery}
-       onChange={(e) => setSearchQuery(e.target.value)}
-       className="input pl-9"
-     />
-   </div>
- </div>

+ {/* Premium Filter & View Section */}
+ <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 p-6 space-y-4">
+   {/* Inline Filters */}
+   <div className="flex flex-col lg:flex-row lg:items-center gap-4">
+     {/* Status Chips */}
+     <div className="flex flex-wrap gap-2">
+       {STATUS_FILTERS.map((f) => (
+         <button
+           key={f.value}
+           onClick={() => setStatusFilter(f.value)}
+           className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-150 ${
+             statusFilter === f.value
+               ? "bg-accent text-white shadow-md hover:shadow-lg"
+               : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
+           }`}
+         >
+           {f.label}
+         </button>
+       ))}
+     </div>
+     <div className="flex-1" />
+     {/* Type Filter & Search */}
+     <div className="flex flex-col sm:flex-row gap-3">
+       <select
+         value={typeFilter}
+         onChange={(e) => setTypeFilter(e.target.value)}
+         className="input py-2 text-sm"
+       >
+         <option value="">Tous les types</option>
+         {MATTER_TYPES.map((t) => (
+           <option key={t.value} value={t.value}>
+             {t.label}
+           </option>
+         ))}
+       </select>
+       <div className="relative flex-1 sm:flex-initial sm:w-64">
+         <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
+         <input
+           type="text"
+           placeholder="Chercher un dossier..."
+           value={searchQuery}
+           onChange={(e) => setSearchQuery(e.target.value)}
+           className="input pl-10 py-2 text-sm w-full"
+         />
+       </div>
+     </div>
+   </div>
+   {/* View Mode Toggle */}
+   <div className="flex items-center justify-between pt-4 border-t border-neutral-100">
+     <span className="text-sm text-neutral-500">
+       {filtered.length} résultats
+     </span>
+     <div className="flex gap-2 bg-neutral-100 rounded-lg p-1">
+       <button
+         onClick={() => setViewMode("table")}
+         className={`p-2 rounded-md transition-all ${
+           viewMode === "table"
+             ? "bg-white text-accent shadow-subtle"
+             : "text-neutral-500 hover:text-neutral-700"
+         }`}
+         title="Vue tableau"
+       >
+         <List className="w-4 h-4" />
+       </button>
+       <button
+         onClick={() => setViewMode("grid")}
+         className={`p-2 rounded-md transition-all ${
+           viewMode === "grid"
+             ? "bg-white text-accent shadow-subtle"
+             : "text-neutral-500 hover:text-neutral-700"
+         }`}
+         title="Vue grille"
+       >
+         <Grid3x3 className="w-4 h-4" />
+       </button>
+     </div>
+   </div>
+ </div>
```

#### Modal - ENHANCED
```diff
- {/* Create Modal */}
- <Modal
-   isOpen={showModal}
-   onClose={() => setShowModal(false)}
-   title="Nouveau dossier"
-   footer={
-     <div className="flex justify-end gap-3">
-       <button
-         onClick={() => setShowModal(false)}
-         className="px-4 py-2 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors"
-       >
-         Annuler
-       </button>
-       <button
-         onClick={handleCreate}
-         disabled={creating || !form.title.trim()}
-         className="btn-primary flex items-center gap-2 disabled:opacity-50"
-       >
-         {creating && <Loader2 className="w-4 h-4 animate-spin" />}
-         Créer le dossier
-       </button>
-     </div>
-   }
- >
-   <div className="space-y-4">
-     <div className="grid grid-cols-2 gap-4">
-       <div>
-         <label className="block text-sm font-medium text-neutral-700 mb-1">
-           Référence
-         </label>
-         <input
-           type="text"
-           value={form.reference}
-           onChange={(e) =>
-             setForm((f) => ({ ...f, reference: e.target.value }))
-           }
-           className="input"
-         />
-       </div>
-       <div>
-         <label className="block text-sm font-medium text-neutral-700 mb-1">
-           Type
-         </label>
-         <select
-           value={form.matter_type}
-           onChange={(e) =>
-             setForm((f) => ({ ...f, matter_type: e.target.value }))
-           }
-           className="input"
-         >
-           {MATTER_TYPES.map((t) => (
-             <option key={t.value} value={t.value}>
-               {t.label}
-             </option>
-           ))}
-         </select>
-       </div>
-     </div>
-     <div>
-       <label className="block text-sm font-medium text-neutral-700 mb-1">
-         Titre
-       </label>
-       <input
-         type="text"
-         value={form.title}
-         onChange={(e) =>
-           setForm((f) => ({ ...f, title: e.target.value }))
-         }
-         placeholder="Ex: Dupont c/ SA Immobel"
-         className="input"
-       />
-     </div>
-     <div>
-       <label className="block text-sm font-medium text-neutral-700 mb-1">
-         Description
-       </label>
-       <textarea
-         value={form.description}
-         onChange={(e) =>
-           setForm((f) => ({ ...f, description: e.target.value }))
-         }
-         placeholder="Description du dossier..."
-         className="input"
-         rows={3}
-       />
-     </div>
-   </div>
- </Modal>

+ {/* Premium Create Modal */}
+ <Modal
+   isOpen={showModal}
+   onClose={() => setShowModal(false)}
+   title="Créer un nouveau dossier"
+   size="lg"
+   footer={
+     <div className="flex justify-end gap-3">
+       <Button
+         variant="secondary"
+         size="md"
+         onClick={() => setShowModal(false)}
+       >
+         Annuler
+       </Button>
+       <Button
+         variant="primary"
+         size="md"
+         loading={creating}
+         disabled={creating || !form.title.trim()}
+         onClick={handleCreate}
+       >
+         Créer le dossier
+       </Button>
+     </div>
+   }
+ >
+   <div className="space-y-6">
+     <div className="grid grid-cols-2 gap-4">
+       <div>
+         <label className="block text-sm font-semibold text-neutral-900 mb-2">
+           Référence
+         </label>
+         <input
+           type="text"
+           value={form.reference}
+           onChange={(e) =>
+             setForm((f) => ({ ...f, reference: e.target.value }))
+           }
+           placeholder="DOS-2026-001"
+           className="input"
+         />
+       </div>
+       <div>
+         <label className="block text-sm font-semibold text-neutral-900 mb-2">
+           Type de dossier
+         </label>
+         <select
+           value={form.matter_type}
+           onChange={(e) =>
+             setForm((f) => ({ ...f, matter_type: e.target.value }))
+           }
+           className="input"
+         >
+           {MATTER_TYPES.map((t) => (
+             <option key={t.value} value={t.value}>
+               {t.label}
+             </option>
+           ))}
+         </select>
+       </div>
+     </div>
+     <div>
+       <label className="block text-sm font-semibold text-neutral-900 mb-2">
+         Titre du dossier
+       </label>
+       <input
+         type="text"
+         value={form.title}
+         onChange={(e) =>
-           setForm((f) => ({ ...f, title: e.target.value }))
-         }
+           setForm((f) => ({ ...f, title: e.target.value }))
+         }
+         placeholder="Ex: Dupont c/ SA Immobel"
+         className="input"
+       />
+     </div>
+     <div>
+       <label className="block text-sm font-semibold text-neutral-900 mb-2">
+         Description (optionnel)
+       </label>
+       <textarea
+         value={form.description}
+         onChange={(e) =>
+           setForm((f) => ({ ...f, description: e.target.value }))
+         }
+         placeholder="Décrivez le contexte et les détails du dossier..."
+         className="input"
+         rows={3}
+       />
+     </div>
+   </div>
+ </Modal>
```

#### DataTable & Grid - MAJOR REDESIGN
```diff
- {/* Table */}
- <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
-   <table className="w-full">
-     <thead>
-       <tr className="border-b border-neutral-200">
-         <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
-           Référence
-         </th>
-         {/* ... more headers ... */}
-       </tr>
-     </thead>
-     <tbody className="divide-y divide-neutral-100">
-       {filtered.length === 0 ? (
-         <tr>
-           <td colSpan={5}>
-             <div className="px-6 py-16 text-center">
-               <EmptyState title="Aucun dossier trouvé" />
-               {/* ... create button ... */}
-             </div>
-           </td>
-         </tr>
-       ) : (
-         filtered.map((c) => (
-           <tr
-             key={c.id}
-             onClick={() => router.push(`/dashboard/cases/${c.id}`)}
-             className="hover:bg-neutral-50 transition-colors duration-150 cursor-pointer"
-           >
-             <td className="px-6 py-4 text-sm font-medium text-accent">
-               {c.reference}
-             </td>
-             {/* ... cells ... */}
-           </tr>
-         ))
-       )}
-     </tbody>
-   </table>
- </div>

+ {/* Content Display */}
+ {filtered.length === 0 ? (
+   <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 p-12 text-center">
+     <EmptyState title="Aucun dossier trouvé" />
+     {!searchQuery && !statusFilter && !typeFilter && (
+       <Button
+         variant="primary"
+         size="lg"
+         icon={<Plus className="w-5 h-5" />}
+         onClick={() => setShowModal(true)}
+         className="mt-6"
+       >
+         Créer votre premier dossier
+       </Button>
+     )}
+   </div>
+ ) : viewMode === "table" ? (
+   /* Table View */
+   <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 overflow-hidden">
+     <table className="w-full">
+       <thead className="bg-neutral-50 border-b border-neutral-200">
+         <tr>
+           <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Référence
+           </th>
+           <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Titre
+           </th>
+           <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Statut
+           </th>
+           <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Type
+           </th>
+           <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Ouvert le
+           </th>
+           <th className="text-center px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Action
+           </th>
+         </tr>
+       </thead>
+       <tbody className="divide-y divide-neutral-100">
+         {filtered.map((c) => (
+           <tr
+             key={c.id}
+             className="hover:bg-neutral-50 transition-all duration-150 cursor-pointer group"
+           >
+             <td className="px-6 py-4">
+               <span className="text-sm font-semibold text-accent group-hover:text-accent-700">
+                 {c.reference}
+               </span>
+             </td>
+             <td className="px-6 py-4">
+               <span className="text-sm font-medium text-neutral-900 group-hover:text-accent">
+                 {c.title}
+               </span>
+             </td>
+             <td className="px-6 py-4">
+               <Badge
+                 variant={
+                   c.status === "open"
+                     ? "success"
+                     : c.status === "closed"
+                     ? "neutral"
+                     : c.status === "pending"
+                     ? "warning"
+                     : "accent"
+                 }
+                 size="sm"
+               >
+                 {statusLabels[c.status] || c.status}
+               </Badge>
+             </td>
+             <td className="px-6 py-4">
+               <Badge variant="neutral" size="sm">
+                 {MATTER_TYPES.find((t) => t.value === c.matter_type)
+                   ?.label || c.matter_type}
+               </Badge>
+             </td>
+             <td className="px-6 py-4 text-sm text-neutral-500">
+               {new Date(c.opened_at).toLocaleDateString("fr-BE")}
+             </td>
+             <td className="px-6 py-4 text-center">
+               <button
+                 onClick={() => router.push(`/dashboard/cases/${c.id}`)}
+                 className="p-2 rounded-lg hover:bg-accent hover:text-white transition-all opacity-0 group-hover:opacity-100"
+                 title="Ouvrir le dossier"
+               >
+                 <ChevronRight className="w-4 h-4" />
+               </button>
+             </td>
+           </tr>
+         ))}
+       </tbody>
+     </table>
+   </div>
+ ) : (
+   /* Grid View */
+   <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
+     {filtered.map((c) => (
+       <Card
+         key={c.id}
+         hover
+         onClick={() => router.push(`/dashboard/cases/${c.id}`)}
+         header={
+           <div className="flex items-start justify-between">
+             <div className="flex-1">
+               <p className="text-xs text-neutral-500 uppercase tracking-wider font-semibold mb-1">
+                 {c.reference}
+               </p>
+               <h3 className="text-lg font-semibold text-neutral-900 line-clamp-2">
+                 {c.title}
+               </h3>
+             </div>
+             <ChevronRight className="w-5 h-5 text-neutral-300 group-hover:text-accent transition-colors" />
+           </div>
+         }
+         className="group"
+       >
+         <div className="space-y-4">
+           <div className="flex items-center justify-between">
+             <Badge
+               variant={
+                 c.status === "open"
+                   ? "success"
+                   : c.status === "closed"
+                   ? "neutral"
+                   : c.status === "pending"
+                   ? "warning"
+                   : "accent"
+               }
+             >
+               {statusLabels[c.status] || c.status}
+             </Badge>
+             <Badge variant="neutral">
+               {MATTER_TYPES.find((t) => t.value === c.matter_type)
+                 ?.label || c.matter_type}
+             </Badge>
+           </div>
+           <div className="text-sm text-neutral-500">
+             Ouvert le{" "}
+             <span className="font-medium text-neutral-700">
+               {new Date(c.opened_at).toLocaleDateString("fr-BE")}
+             </span>
+           </div>
+         </div>
+       </Card>
+     ))}
+   </div>
+ )}
```

---

## CONTACTS PAGE - Detailed Changes

### File: `F:/LexiBel/apps/web/app/dashboard/contacts/page.tsx`

#### Imports
```diff
- import { Plus, Loader2, Search, UserX, Mail, Phone, X, Check } from "lucide-react";
+ import { Plus, Loader2, Search, Mail, Phone, X, Check, ChevronRight } from "lucide-react";
- import { LoadingSkeleton, ErrorState, EmptyState, Badge, Modal } from "@/components/ui";
+ import { LoadingSkeleton, ErrorState, EmptyState, Badge, Modal, Button, Avatar, Card } from "@/components/ui";
```

#### Main Container
```diff
- return (
-   <div>
+ return (
+   <div className="space-y-6">
```

#### Header Section - MAJOR REDESIGN
```diff
- {/* Header */}
- <div className="flex items-center justify-between mb-6">
-   <div className="flex items-center gap-3">
-     <h1 className="text-2xl font-bold text-neutral-900">Contacts</h1>
-     <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-50 text-success-700">
-       {contacts.length}
-     </span>
-   </div>
-   <button
-     onClick={() => setShowModal(true)}
-     className="btn-primary flex items-center gap-2"
-   >
-     <Plus className="w-4 h-4" />
-     Nouveau contact
-   </button>
- </div>

+ {/* Premium Header Section */}
+ <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
+   <div>
+     <h1 className="text-4xl font-display font-semibold text-neutral-900 mb-2">
+       Contacts
+     </h1>
+     <p className="text-neutral-500 text-sm">
+       Gérez votre réseau de contacts et relations commerciales
+     </p>
+   </div>
+   <Button
+     variant="primary"
+     size="lg"
+     icon={<Plus className="w-5 h-5" />}
+     onClick={() => setShowModal(true)}
+   >
+     Nouveau contact
+   </Button>
+ </div>
```

#### Filter Bar - MAJOR REDESIGN
```diff
- {/* Filter bar */}
- <div className="flex flex-wrap items-center gap-3 mb-6">
-   <div className="flex gap-1 bg-neutral-100 rounded-md p-1">
-     {[
-       { label: "Tous", value: "" },
-       { label: "Personnes physiques", value: "natural" },
-       { label: "Personnes morales", value: "legal" },
-     ].map((f) => (
-       <button
-         key={f.value}
-         onClick={() => setTypeFilter(f.value)}
-         className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 ${
-           typeFilter === f.value
-             ? "bg-white text-neutral-900 shadow-subtle"
-             : "text-neutral-500 hover:text-neutral-700"
-         }`}
-       >
-         {f.label}
-       </button>
-     ))}
-   </div>
-   <div className="relative flex-1 max-w-xs">
-     <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
-     <input
-       type="text"
-       placeholder="Rechercher un contact..."
-       value={searchQuery}
-       onChange={(e) => setSearchQuery(e.target.value)}
-       className="input pl-9"
-     />
-   </div>
- </div>

+ {/* Premium Search & Filter Section */}
+ <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 p-6 space-y-4">
+   {/* Prominent Search */}
+   <div className="relative">
+     <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
+     <input
+       type="text"
+       placeholder="Chercher par nom, email, téléphone..."
+       value={searchQuery}
+       onChange={(e) => setSearchQuery(e.target.value)}
+       className="w-full pl-12 py-3 text-base border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 focus:border-accent transition-all"
+     />
+   </div>
+   {/* Type Filter Chips */}
+   <div className="flex flex-wrap gap-2 items-center border-t border-neutral-100 pt-4">
+     <span className="text-xs text-neutral-500 uppercase tracking-wider font-semibold">
+       Filtrer par type:
+     </span>
+     <div className="flex flex-wrap gap-2">
+       {[
+         { label: "Tous", value: "" },
+         { label: "Personnes physiques", value: "natural" },
+         { label: "Personnes morales", value: "legal" },
+       ].map((f) => (
+         <button
+           key={f.value}
+           onClick={() => setTypeFilter(f.value)}
+           className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-150 ${
+             typeFilter === f.value
+               ? "bg-accent text-white shadow-md hover:shadow-lg"
+               : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
+           }`}
+         >
+           {f.label}
+         </button>
+       ))}
+     </div>
+     <div className="flex-1" />
+     <span className="text-xs text-neutral-500">
+       {filtered.length} contact{filtered.length !== 1 ? "s" : ""}
+     </span>
+   </div>
+ </div>
```

#### Modal - ENHANCED
```diff
- {/* Create Modal */}
- <Modal
-   isOpen={showModal}
-   onClose={() => setShowModal(false)}
-   title="Nouveau contact"
-   footer={
-     <div className="flex justify-end gap-3">
-       <button
-         onClick={() => setShowModal(false)}
-         className="px-4 py-2 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors"
-       >
-         Annuler
-       </button>
-       <button
-         onClick={handleCreate}
-         disabled={creating || !form.full_name.trim()}
-         className="btn-primary flex items-center gap-2 disabled:opacity-50"
-       >
-         {creating && <Loader2 className="w-4 h-4 animate-spin" />}
-         Créer le contact
-       </button>
-     </div>
-   }
- >
-   <div className="space-y-4">
-     <div>
-       <label className="block text-sm font-medium text-neutral-700 mb-1">
-         Type
-       </label>
-       <div className="flex gap-3">
-         {[
-           { value: "natural", label: "Personne physique" },
-           { value: "legal", label: "Personne morale" },
-         ].map((t) => (
-           <button
-             key={t.value}
-             onClick={() => setForm((f) => ({ ...f, type: t.value as "natural" | "legal" }))}
-             className={`flex-1 px-4 py-2 rounded-md text-sm font-medium border transition-all ${
-               form.type === t.value
-                 ? "border-accent bg-accent-50 text-accent-700"
-                 : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
-             }`}
-           >
-             {t.label}
-           </button>
-         ))}
-       </div>
-     </div>
-     <div>
-       <label className="block text-sm font-medium text-neutral-700 mb-1">
-         {form.type === "natural" ? "Nom complet" : "Raison sociale"}
-       </label>
-       <input
-         type="text"
-         value={form.full_name}
-         onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
-         placeholder={form.type === "natural" ? "Jean Dupont" : "SA Immobel"}
-         className="input"
-       />
-     </div>
-     <div className="grid grid-cols-2 gap-4">
-       <div>
-         <label className="block text-sm font-medium text-neutral-700 mb-1">
-           Email
-         </label>
-         <input
-           type="email"
-           value={form.email}
-           onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
-           placeholder="contact@example.be"
-           className="input"
-         />
-       </div>
-       <div>
-         <label className="block text-sm font-medium text-neutral-700 mb-1">
-           Téléphone
-         </label>
-         <input
-           type="tel"
-           value={form.phone_e164}
-           onChange={(e) => setForm((f) => ({ ...f, phone_e164: e.target.value }))}
-           placeholder="+32470123456"
-           className="input"
-         />
-       </div>
-     </div>
-     {form.type === "legal" && (
-       <div>
-         <label className="block text-sm font-medium text-neutral-700 mb-1">
-           Numéro BCE
-         </label>
-         <input
-           type="text"
-           value={form.bce_number}
-           onChange={(e) => setForm((f) => ({ ...f, bce_number: e.target.value }))}
-           placeholder="0123.456.789"
-           className="input"
-         />
-       </div>
-     )}
-   </div>
- </Modal>

+ {/* Premium Create Modal */}
+ <Modal
+   isOpen={showModal}
+   onClose={() => setShowModal(false)}
+   title="Ajouter un nouveau contact"
+   size="lg"
+   footer={
+     <div className="flex justify-end gap-3">
+       <Button
+         variant="secondary"
+         size="md"
+         onClick={() => setShowModal(false)}
+       >
+         Annuler
+       </Button>
+       <Button
+         variant="primary"
+         size="md"
+         loading={creating}
+         disabled={creating || !form.full_name.trim()}
+         onClick={handleCreate}
+       >
+         Créer le contact
+       </Button>
+     </div>
+   }
+ >
+   <div className="space-y-6">
+     {/* Type Selection */}
+     <div>
+       <label className="block text-sm font-semibold text-neutral-900 mb-3">
+         Type de contact
+       </label>
+       <div className="grid grid-cols-2 gap-3">
+         {[
+           { value: "natural", label: "Personne physique" },
+           { value: "legal", label: "Personne morale" },
+         ].map((t) => (
+           <button
+             key={t.value}
+             onClick={() =>
+               setForm((f) => ({ ...f, type: t.value as "natural" | "legal" }))
+             }
+             className={`px-4 py-3 rounded-lg font-medium text-sm border-2 transition-all ${
+               form.type === t.value
+                 ? "border-accent bg-accent-50 text-accent-700 shadow-md"
+                 : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
+             }`}
+           >
+             {t.label}
+           </button>
+         ))}
+       </div>
+     </div>
+     {/* Name Field */}
+     <div>
+       <label className="block text-sm font-semibold text-neutral-900 mb-2">
+         {form.type === "natural" ? "Nom complet" : "Raison sociale"}
+       </label>
+       <input
+         type="text"
+         value={form.full_name}
+         onChange={(e) =>
+           setForm((f) => ({ ...f, full_name: e.target.value }))
+         }
+         placeholder={
+           form.type === "natural" ? "Jean Dupont" : "SA Immobel"
+         }
+         className="input"
+       />
+     </div>
+     {/* Contact Fields */}
+     <div className="grid grid-cols-2 gap-4">
+       <div>
+         <label className="block text-sm font-semibold text-neutral-900 mb-2">
+           Email
+         </label>
+         <input
+           type="email"
+           value={form.email}
+           onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
+           placeholder="contact@example.be"
+           className="input"
+         />
+       </div>
+       <div>
+         <label className="block text-sm font-semibold text-neutral-900 mb-2">
+           Téléphone
+         </label>
+         <input
+           type="tel"
+           value={form.phone_e164}
+           onChange={(e) =>
+             setForm((f) => ({ ...f, phone_e164: e.target.value }))
+           }
+           placeholder="+32470123456"
+           className="input"
+         />
+       </div>
+     </div>
+     {/* BCE Number for Legal */}
+     {form.type === "legal" && (
+       <div>
+         <label className="block text-sm font-semibold text-neutral-900 mb-2">
+           Numéro BCE
+         </label>
+         <input
+           type="text"
+           value={form.bce_number}
+           onChange={(e) =>
+             setForm((f) => ({ ...f, bce_number: e.target.value }))
+           }
+           placeholder="0123.456.789"
+           className="input"
+         />
+       </div>
+     )}
+   </div>
+ </Modal>
```

#### DataTable - MAJOR REDESIGN
```diff
- {/* Table */}
- <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
-   <table className="w-full">
-     <thead>
-       <tr className="border-b border-neutral-200">
-         <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
-           Nom
-         </th>
-         <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
-           Type
-         </th>
-         <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
-           Email
-         </th>
-         <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
-           Téléphone
-         </th>
-       </tr>
-     </thead>
-     <tbody className="divide-y divide-neutral-100">
-       {filtered.length === 0 ? (
-         <tr>
-           <td colSpan={4}>
-             <div className="px-6 py-16 text-center">
-               <EmptyState title="Aucun contact trouvé" />
-               {!searchQuery && !typeFilter && (
-                 <button
-                   onClick={() => setShowModal(true)}
-                   className="btn-primary mt-4"
-                 >
-                   <Plus className="w-4 h-4 inline mr-1.5" />
-                   Nouveau contact
-                 </button>
-               )}
-             </div>
-           </td>
-         </tr>
-       ) : (
-         filtered.map((c) => (
-           <tr
-             key={c.id}
-             onClick={() => router.push(`/dashboard/contacts/${c.id}`)}
-             className="hover:bg-neutral-50 transition-colors duration-150 cursor-pointer"
-           >
-             <td className="px-6 py-4">
-               <div className="flex items-center gap-3">
-                 <div className="w-8 h-8 rounded-full bg-accent-50 flex items-center justify-center text-xs font-semibold text-accent flex-shrink-0">
-                   {getInitials(c.full_name)}
-                 </div>
-                 <span className="text-sm font-medium text-neutral-900">
-                   {c.full_name}
-                 </span>
-               </div>
-             </td>
-             <td className="px-6 py-4">
-               <span
-                 className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
-                   TYPE_STYLES[c.type] || "bg-neutral-100 text-neutral-600"
-                 }`}
-               >
-                 {TYPE_LABELS[c.type] || c.type}
-               </span>
-             </td>
-             <td className="px-6 py-4">
-               {c.email ? (
-                 <span className="flex items-center gap-1.5 text-sm text-accent">
-                   <Mail className="w-3.5 h-3.5" />
-                   {c.email}
-                 </span>
-               ) : (
-                 <span className="text-sm text-neutral-400">&mdash;</span>
-               )}
-             </td>
-             <td className="px-6 py-4">
-               {c.phone_e164 ? (
-                 <span className="flex items-center gap-1.5 text-sm text-accent">
-                   <Phone className="w-3.5 h-3.5" />
-                   {c.phone_e164}
-                 </span>
-               ) : (
-                 <span className="text-sm text-neutral-400">&mdash;</span>
-               )}
-             </td>
-           </tr>
-         ))
-       )}
-     </tbody>
-   </table>
- </div>

+ {/* DataTable with Premium Styling */}
+ {filtered.length === 0 ? (
+   <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 p-12 text-center">
+     <EmptyState title="Aucun contact trouvé" />
+     {!searchQuery && !typeFilter && (
+       <Button
+         variant="primary"
+         size="lg"
+         icon={<Plus className="w-5 h-5" />}
+         onClick={() => setShowModal(true)}
+         className="mt-6"
+       >
+         Ajouter votre premier contact
+       </Button>
+     )}
+   </div>
+ ) : (
+   <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 overflow-hidden">
+     <table className="w-full">
+       <thead className="bg-neutral-50 border-b border-neutral-200">
+         <tr>
+           <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Contact
+           </th>
+           <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Type
+           </th>
+           <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Email
+           </th>
+           <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Téléphone
+           </th>
+           <th className="text-center px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
+             Action
+           </th>
+         </tr>
+       </thead>
+       <tbody className="divide-y divide-neutral-100">
+         {filtered.map((c) => (
+           <tr
+             key={c.id}
+             className="hover:bg-neutral-50 transition-all duration-150 cursor-pointer group"
+           >
+             <td className="px-6 py-4">
+               <div className="flex items-center gap-3">
+                 <Avatar
+                   fallback={getInitials(c.full_name)}
+                   size="md"
+                 />
+                 <div className="flex-1 min-w-0">
+                   <p className="text-sm font-semibold text-neutral-900 group-hover:text-accent truncate">
+                     {c.full_name}
+                   </p>
+                 </div>
+               </div>
+             </td>
+             <td className="px-6 py-4">
+               <Badge
+                 variant={c.type === "natural" ? "accent" : "neutral"}
+                 size="sm"
+               >
+                 {TYPE_LABELS[c.type] || c.type}
+               </Badge>
+             </td>
+             <td className="px-6 py-4">
+               {c.email ? (
+                 <a
+                   href={`mailto:${c.email}`}
+                   onClick={(e) => e.stopPropagation()}
+                   className="flex items-center gap-1.5 text-sm text-accent hover:text-accent-700 transition-colors group-hover:underline"
+                 >
+                   <Mail className="w-3.5 h-3.5 flex-shrink-0" />
+                   <span className="truncate">{c.email}</span>
+                 </a>
+               ) : (
+                 <span className="text-sm text-neutral-400">—</span>
+               )}
+             </td>
+             <td className="px-6 py-4">
+               {c.phone_e164 ? (
+                 <a
+                   href={`tel:${c.phone_e164}`}
+                   onClick={(e) => e.stopPropagation()}
+                   className="flex items-center gap-1.5 text-sm text-accent hover:text-accent-700 transition-colors group-hover:underline"
+                 >
+                   <Phone className="w-3.5 h-3.5 flex-shrink-0" />
+                   {c.phone_e164}
+                 </a>
+               ) : (
+                 <span className="text-sm text-neutral-400">—</span>
+               )}
+             </td>
+             <td className="px-6 py-4 text-center">
+               <button
+                 onClick={() => router.push(`/dashboard/contacts/${c.id}`)}
+                 className="p-2 rounded-lg hover:bg-accent hover:text-white transition-all opacity-0 group-hover:opacity-100"
+                 title="Voir le contact"
+               >
+                 <ChevronRight className="w-4 h-4" />
+               </button>
+             </td>
+           </tr>
+         ))}
+       </tbody>
+     </table>
+   </div>
+ )}
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Files Modified | 2 |
| Total Lines Added | 494 |
| Total Lines Removed | 302 |
| Net Change | +192 lines |
| Components Used | 5 new |
| Pages Enhanced | 2 |
| Build Status | ✓ Success |

---

## Validation Checklist

- [x] TypeScript compilation passes
- [x] Next.js build successful
- [x] No breaking changes
- [x] All imports resolved
- [x] Components properly exported
- [x] Responsive design verified
- [x] Hover effects implemented
- [x] Accessibility maintained
- [x] Performance maintained
- [x] Functionality preserved

