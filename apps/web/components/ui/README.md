# LexiBel Premium UI Components

Design system complet avec composants UI premium pour LexiBel, construits avec React, TypeScript et Tailwind CSS.

## Design System

### Colors
- **Primary**: Deep Slate (#0F172A)
- **Accent**: Warm Gold (#D97706)
- **Success**: #059669
- **Warning**: #F59E0B
- **Danger**: #E11D48
- **Neutral**: Shades from 50 to 900

### Typography
- **font-display**: Crimson Pro (titres)
- **font-sans**: Manrope (texte)
- **font-mono**: JetBrains Mono (code)

### Animations
- fadeIn, slideUp, slideDown, slideLeft, slideRight
- scaleIn, shimmer, pulse-subtle

### Shadows
- subtle, sm, md, lg, xl, 2xl

### Border Radius
- sm (8px), md (12px), lg (16px), xl (24px)

## Installation

```typescript
// Import des composants premium
import {
  Button,
  Input,
  Card,
  Badge,
  Modal,
  Tooltip,
  Avatar,
  Tabs,
  Toast,
  Skeleton,
} from '@/components/ui';
```

## Composants Premium

### 1. Button

Bouton avec variants, tailles, loading state et icônes.

```tsx
import { Button } from "@/components/ui";
import { Heart } from "lucide-react";

<Button variant="primary" size="md">Click me</Button>
<Button variant="primary" loading>Loading...</Button>
<Button variant="primary" icon={<Heart className="w-4 h-4" />}>
  With Icon
</Button>
```

**Props**: variant (primary/secondary/ghost/danger), size (sm/md/lg), loading, icon, disabled

### 2. Input

Input avec label, erreurs, et icônes prefix/suffix.

```tsx
import { Input } from "@/components/ui";
import { Search } from "lucide-react";

<Input label="Email" placeholder="Enter your email" type="email" />
<Input label="Search" prefixIcon={<Search className="w-4 h-4" />} placeholder="Search..." />
<Input label="Password" error="Password is required" type="password" />
```

**Props**: label, error, prefixIcon, suffixIcon, + tous les props HTML input

### 3. Card

Card avec header, footer, hover effect et onClick.

```tsx
import { Card } from "@/components/ui";

<Card hover>
  <h3>Card Title</h3>
  <p>Card content</p>
</Card>

<Card header={<h3>Header</h3>} footer={<Button>Action</Button>}>
  Content
</Card>
```

**Props**: children, hover, header, footer, onClick

### 4. Badge

Badge avec variants, tailles, dot indicator et pulse.

```tsx
import { Badge } from "@/components/ui";

<Badge variant="success">Active</Badge>
<Badge variant="danger" dot>Error</Badge>
<Badge variant="accent" dot pulse>Live</Badge>
```

**Props**: variant (default/success/warning/danger/accent/neutral), size (sm/md), dot, pulse

### 5. Modal

Modal avec backdrop blur, animations, keyboard support (ESC).

```tsx
import { Modal } from "@/components/ui";

const [isOpen, setIsOpen] = useState(false);

<Modal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="Modal Title"
  size="md"
  footer={<Button onClick={() => setIsOpen(false)}>Close</Button>}
>
  Modal content
</Modal>
```

**Props**: isOpen, onClose, title, size (sm/md/lg/xl), footer
**Features**: Backdrop blur, ESC key, body scroll lock, animations

### 6. Tooltip

Tooltip avec positionnement et animations.

```tsx
import { Tooltip } from "@/components/ui";

<Tooltip content="Tooltip text" position="top">
  <Button>Hover me</Button>
</Tooltip>
```

**Props**: content, children, position (top/bottom/left/right)

### 7. Avatar

Avatar avec image ou initiales, tailles et status indicator.

```tsx
import { Avatar } from "@/components/ui";

<Avatar src="/avatar.jpg" fallback="JD" size="md" status="online" />
<Avatar fallback="AB" size="lg" status="busy" />
```

**Props**: src, alt, fallback (initiales), size (sm/md/lg/xl), status (online/offline/busy)

### 8. Tabs

Tabs avec icônes, badges et indicator animé.

```tsx
import { Tabs } from "@/components/ui";
import { User, Settings } from "lucide-react";

const tabs = [
  {
    id: "profile",
    label: "Profile",
    icon: <User className="w-4 h-4" />,
    content: <div>Profile content</div>,
  },
  {
    id: "settings",
    label: "Settings",
    icon: <Settings className="w-4 h-4" />,
    badge: 3,
    content: <div>Settings content</div>,
  },
];

<Tabs tabs={tabs} defaultTab="profile" />
```

**Props**: tabs (Tab[]), defaultTab
**Features**: Animated indicator bar, icon + label + badge support

### 9. Toast

Toast notifications avec auto-dismiss et progress bar.

```tsx
import { Toast } from "@/components/ui";

const [show, setShow] = useState(false);

{show && (
  <Toast
    message="Success message"
    type="success"
    duration={5000}
    onClose={() => setShow(false)}
  />
)}
```

**Props**: message, type (success/error/info), duration, onClose
**Features**: Auto-dismiss, progress bar, slideLeft animation

### 10. Skeleton

Skeleton loader avec shimmer effect.

```tsx
import { Skeleton } from "@/components/ui";

<Skeleton variant="text" width="60%" />
<Skeleton variant="circle" width="48px" height="48px" />
<Skeleton variant="rect" width="100%" height="120px" />
```

**Props**: variant (text/circle/rect), width, height
**Features**: Shimmer animation, custom dimensions

---

## Composants Existants

### LoadingSkeleton

Skeleton de chargement animé avec 4 variantes.

```typescript
<LoadingSkeleton variant="card" />    // Grille 3 colonnes
<LoadingSkeleton variant="table" />   // Tableau 5 lignes
```

### ErrorState, EmptyState, StatCard, DataTable

Voir documentation précédente (inchangés)

## Showcase

Pour voir tous les composants en action:

```tsx
import ComponentShowcase from "@/components/ui/ComponentShowcase";

<ComponentShowcase />
```

## TypeScript

Tous les composants exportent leurs interfaces Props:

```typescript
import type {
  ButtonProps,
  InputProps,
  CardProps,
  BadgeProps,
  ModalProps,
  TooltipProps,
  AvatarProps,
  TabsProps,
  Tab,
  ToastProps,
  SkeletonProps,
} from '@/components/ui';
```

## Dépendances

- `lucide-react`: Icônes
- `react`: Hooks (useEffect, useState, useRef)
- Tailwind CSS avec custom config

## Design Principles

1. **Consistency**: Design system cohérent avec Tailwind
2. **Accessibility**: Support clavier, focus states, ARIA
3. **Performance**: Animations optimisées, pas de CSS custom
4. **Flexibility**: Props extensibles, className override
5. **Type Safety**: TypeScript strict avec interfaces exportées
