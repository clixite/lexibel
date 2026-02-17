# LexiBel UI Components - Exemples Pratiques

## Exemple 1: Formulaire de Connexion

```tsx
"use client";

import { useState } from "react";
import { Button, Input, Card } from "@/components/ui";
import { Mail, Lock } from "lucide-react";

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({ email: "", password: "" });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    // API call...
    setLoading(false);
  };

  return (
    <Card className="max-w-md mx-auto">
      <h2 className="text-2xl font-display font-bold text-primary-900 mb-6">
        Connexion
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Email"
          type="email"
          placeholder="votre@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          prefixIcon={<Mail className="w-4 h-4" />}
          error={errors.email}
        />
        <Input
          label="Mot de passe"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          prefixIcon={<Lock className="w-4 h-4" />}
          error={errors.password}
        />
        <Button variant="primary" type="submit" loading={loading} className="w-full">
          Se connecter
        </Button>
      </form>
    </Card>
  );
}
```

## Exemple 2: Liste d'Utilisateurs avec Actions

```tsx
"use client";

import { useState } from "react";
import { Card, Avatar, Badge, Button, Tooltip, Toast } from "@/components/ui";
import { Mail, Trash2, Edit } from "lucide-react";

interface User {
  id: string;
  name: string;
  email: string;
  status: "online" | "offline" | "busy";
  role: string;
}

export default function UserList({ users }: { users: User[] }) {
  const [showToast, setShowToast] = useState(false);

  const handleDelete = (userId: string) => {
    // Delete logic...
    setShowToast(true);
  };

  return (
    <div className="space-y-4">
      {users.map((user) => (
        <Card key={user.id} hover className="flex items-center gap-4">
          <Avatar
            fallback={user.name.slice(0, 2).toUpperCase()}
            status={user.status}
            size="lg"
          />
          <div className="flex-1">
            <h3 className="font-semibold text-primary-900">{user.name}</h3>
            <p className="text-sm text-neutral-600">{user.email}</p>
          </div>
          <Badge variant={user.status === "online" ? "success" : "neutral"} dot>
            {user.role}
          </Badge>
          <div className="flex gap-2">
            <Tooltip content="Envoyer un email" position="top">
              <Button variant="ghost" size="sm" icon={<Mail className="w-4 h-4" />} />
            </Tooltip>
            <Tooltip content="Modifier" position="top">
              <Button variant="ghost" size="sm" icon={<Edit className="w-4 h-4" />} />
            </Tooltip>
            <Tooltip content="Supprimer" position="top">
              <Button
                variant="ghost"
                size="sm"
                icon={<Trash2 className="w-4 h-4" />}
                onClick={() => handleDelete(user.id)}
              />
            </Tooltip>
          </div>
        </Card>
      ))}

      {showToast && (
        <Toast
          message="Utilisateur supprimé avec succès"
          type="success"
          onClose={() => setShowToast(false)}
        />
      )}
    </div>
  );
}
```

## Exemple 3: Profil Utilisateur avec Tabs

```tsx
"use client";

import { Tabs, Card, Badge, Avatar, Button } from "@/components/ui";
import { User, Settings, Bell, Shield } from "lucide-react";

export default function UserProfile() {
  const tabs = [
    {
      id: "info",
      label: "Informations",
      icon: <User className="w-4 h-4" />,
      content: (
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <Avatar
              fallback="JD"
              size="xl"
              status="online"
            />
            <div>
              <h3 className="text-xl font-display font-bold">John Doe</h3>
              <p className="text-neutral-600">john.doe@example.com</p>
              <Badge variant="accent" className="mt-2">Administrateur</Badge>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "settings",
      label: "Paramètres",
      icon: <Settings className="w-4 h-4" />,
      content: (
        <div className="space-y-4">
          <h3 className="font-semibold">Préférences</h3>
          <p className="text-neutral-600">Gérez vos paramètres de compte</p>
        </div>
      ),
    },
    {
      id: "notifications",
      label: "Notifications",
      icon: <Bell className="w-4 h-4" />,
      badge: 5,
      content: (
        <div className="space-y-4">
          <h3 className="font-semibold">Notifications récentes</h3>
          <p className="text-neutral-600">5 nouvelles notifications</p>
        </div>
      ),
    },
    {
      id: "security",
      label: "Sécurité",
      icon: <Shield className="w-4 h-4" />,
      content: (
        <div className="space-y-4">
          <h3 className="font-semibold">Sécurité du compte</h3>
          <Button variant="primary">Changer le mot de passe</Button>
        </div>
      ),
    },
  ];

  return (
    <Card>
      <Tabs tabs={tabs} defaultTab="info" />
    </Card>
  );
}
```

## Exemple 4: Modal de Confirmation

```tsx
"use client";

import { useState } from "react";
import { Modal, Button } from "@/components/ui";
import { AlertCircle } from "lucide-react";

export default function DeleteConfirmation() {
  const [isOpen, setIsOpen] = useState(false);

  const handleDelete = () => {
    // Delete logic...
    setIsOpen(false);
  };

  return (
    <>
      <Button variant="danger" onClick={() => setIsOpen(true)}>
        Supprimer
      </Button>

      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Confirmer la suppression"
        size="sm"
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setIsOpen(false)}>
              Annuler
            </Button>
            <Button variant="danger" onClick={handleDelete}>
              Supprimer
            </Button>
          </div>
        }
      >
        <div className="flex gap-4">
          <AlertCircle className="w-6 h-6 text-danger flex-shrink-0" />
          <div>
            <p className="text-neutral-900 font-medium mb-2">
              Êtes-vous sûr de vouloir supprimer cet élément ?
            </p>
            <p className="text-neutral-600 text-sm">
              Cette action est irréversible. Toutes les données associées
              seront définitivement supprimées.
            </p>
          </div>
        </div>
      </Modal>
    </>
  );
}
```

## Exemple 5: Skeleton Loading State

```tsx
"use client";

import { Card, Skeleton, Avatar, Badge } from "@/components/ui";

export default function LoadingUserCard() {
  const isLoading = true;

  if (isLoading) {
    return (
      <Card>
        <div className="flex items-center gap-4">
          <Skeleton variant="circle" width="48px" height="48px" />
          <div className="flex-1 space-y-2">
            <Skeleton variant="text" width="40%" />
            <Skeleton variant="text" width="60%" />
          </div>
          <Skeleton variant="rect" width="80px" height="24px" />
        </div>
      </Card>
    );
  }

  return (
    <Card className="flex items-center gap-4">
      <Avatar fallback="JD" size="lg" status="online" />
      <div className="flex-1">
        <h3 className="font-semibold">John Doe</h3>
        <p className="text-sm text-neutral-600">john.doe@example.com</p>
      </div>
      <Badge variant="success">Active</Badge>
    </Card>
  );
}
```

## Exemple 6: Toast Notifications System

```tsx
"use client";

import { useState } from "react";
import { Button, Toast } from "@/components/ui";

type ToastType = "success" | "error" | "info";

export default function NotificationSystem() {
  const [toasts, setToasts] = useState<{ id: number; type: ToastType; message: string }[]>([]);
  let nextId = 0;

  const showToast = (type: ToastType, message: string) => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, type, message }]);
  };

  const removeToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <Button
          variant="primary"
          onClick={() => showToast("success", "Opération réussie !")}
        >
          Success
        </Button>
        <Button
          variant="danger"
          onClick={() => showToast("error", "Une erreur est survenue")}
        >
          Error
        </Button>
        <Button
          variant="secondary"
          onClick={() => showToast("info", "Information importante")}
        >
          Info
        </Button>
      </div>

      {toasts.map((toast, index) => (
        <div key={toast.id} style={{ top: `${4 + index * 80}px` }}>
          <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        </div>
      ))}
    </div>
  );
}
```

## Exemple 7: Search avec Filtres

```tsx
"use client";

import { useState } from "react";
import { Input, Badge, Card } from "@/components/ui";
import { Search, Filter } from "lucide-react";

export default function SearchWithFilters() {
  const [search, setSearch] = useState("");
  const [activeFilters, setActiveFilters] = useState<string[]>([]);

  const filters = ["Tous", "Actifs", "Inactifs", "En attente"];

  const toggleFilter = (filter: string) => {
    setActiveFilters((prev) =>
      prev.includes(filter)
        ? prev.filter((f) => f !== filter)
        : [...prev, filter]
    );
  };

  return (
    <Card>
      <Input
        placeholder="Rechercher..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        prefixIcon={<Search className="w-4 h-4" />}
      />

      <div className="flex gap-2 mt-4">
        {filters.map((filter) => (
          <Badge
            key={filter}
            variant={activeFilters.includes(filter) ? "accent" : "neutral"}
            className="cursor-pointer"
            onClick={() => toggleFilter(filter)}
          >
            {filter}
          </Badge>
        ))}
      </div>
    </Card>
  );
}
```

## Patterns Communs

### Pattern 1: Form avec Validation

```tsx
const [errors, setErrors] = useState<Record<string, string>>({});

const validate = () => {
  const newErrors: Record<string, string> = {};
  if (!email) newErrors.email = "Email requis";
  if (!password) newErrors.password = "Mot de passe requis";
  setErrors(newErrors);
  return Object.keys(newErrors).length === 0;
};
```

### Pattern 2: Loading States

```tsx
const [loading, setLoading] = useState(false);

const handleAction = async () => {
  setLoading(true);
  try {
    await api.call();
  } finally {
    setLoading(false);
  }
};
```

### Pattern 3: Confirmation Modal

```tsx
const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

<Modal isOpen={!!confirmDelete} onClose={() => setConfirmDelete(null)}>
  {/* Content */}
</Modal>
```

## Tips et Best Practices

1. **Composition**: Combinez les composants pour créer des interfaces complexes
2. **Feedback**: Utilisez Toast pour les actions asynchrones
3. **Loading**: Montrez toujours un état de chargement avec Skeleton ou Button loading
4. **Validation**: Affichez les erreurs avec Input error prop
5. **Accessibility**: Utilisez Tooltip pour expliquer les actions des boutons
6. **Consistency**: Gardez les variants et sizes cohérents dans toute l'app
