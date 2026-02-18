# Migration & Admin Pages - Code Patterns & Best Practices

## Overview

This document provides reusable code patterns and best practices used in the Migration Wizard and Admin Pages implementation.

---

## Pattern 1: Step-Based Wizard

### Structure

```tsx
type Step = 1 | 2 | 3 | 4 | 5;

const STEP_LABELS = ["Source", "Upload", "Preview", "Confirmation", "Résultats"];
const STEP_ICONS = [Upload, FileUp, Eye, CheckCircle2, Check];

export default function WizardPage() {
  const [step, setStep] = useState<Step>(1);
  const progressPercent = (step / 5) * 100;

  return (
    <div>
      {/* Progress Bar */}
      <ProgressBar percent={progressPercent} step={step} />

      {/* Step Indicators */}
      <StepIndicators currentStep={step} />

      {/* Conditional Content */}
      {step === 1 && <StepOne onNext={() => setStep(2)} />}
      {step === 2 && <StepTwo onNext={() => setStep(3)} />}
      {step === 3 && <StepThree onNext={() => setStep(4)} />}
      {step === 4 && <StepFour onNext={() => setStep(5)} />}
      {step === 5 && <StepFive onRestart={() => setStep(1)} />}
    </div>
  );
}
```

### Progress Bar Component

```tsx
// Reusable Progress Bar
function ProgressBar({ percent, step, total = 5 }: { percent: number; step: number; total?: number }) {
  return (
    <div className="bg-white rounded-lg shadow-subtle p-4 mb-8">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-neutral-900">Progression</span>
        <span className="text-sm font-bold text-accent">{Math.round(percent)}%</span>
      </div>
      <div className="h-2.5 bg-neutral-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-accent to-accent-600 transition-all duration-300 shadow-md"
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="mt-2 text-xs text-neutral-500">
        Étape {step} sur {total}
      </div>
    </div>
  );
}
```

### Step Indicators Component

```tsx
// Reusable Step Indicators
interface StepIndicatorsProps {
  steps: Array<{ label: string; icon?: React.ComponentType<{ className?: string }> }>;
  currentStep: number;
}

function StepIndicators({ steps, currentStep }: StepIndicatorsProps) {
  return (
    <div className="mb-8 overflow-x-auto">
      <div className="flex items-center gap-3 min-w-full pb-2">
        {steps.map((step, i) => {
          const IconComponent = step.icon;
          const isCompleted = i + 1 < currentStep;
          const isActive = i + 1 === currentStep;

          return (
            <div key={step.label} className="flex items-center gap-3 flex-shrink-0">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center font-medium transition-all duration-200 shadow-sm ${
                  isActive
                    ? "bg-accent text-white shadow-md"
                    : isCompleted
                      ? "bg-success text-white"
                      : "bg-neutral-100 text-neutral-400"
                }`}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5" />
                ) : IconComponent ? (
                  <IconComponent className="w-5 h-5" />
                ) : (
                  i + 1
                )}
              </div>
              <span className={`text-sm whitespace-nowrap font-medium ${
                isActive ? "text-neutral-900" : isCompleted ? "text-success" : "text-neutral-500"
              }`}>
                {step.label}
              </span>
              {i < steps.length - 1 && (
                <div className={`w-8 h-0.5 transition-colors flex-shrink-0 ${
                  isCompleted ? "bg-success" : "bg-neutral-200"
                }`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

---

## Pattern 2: Tab Navigation Grid

### Structure

```tsx
interface TabItem {
  id: string;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  description?: string;
}

interface TabNavigationProps {
  tabs: TabItem[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  colsDesktop?: string; // e.g., "md:grid-cols-4"
  colsMobile?: string;  // e.g., "grid-cols-2"
}

export function TabNavigation({
  tabs,
  activeTab,
  onTabChange,
  colsDesktop = "md:grid-cols-4",
  colsMobile = "grid-cols-2",
}: TabNavigationProps) {
  return (
    <div className={`grid ${colsMobile} ${colsDesktop} gap-3 mb-8`}>
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`p-4 rounded-lg border-2 transition-all duration-200 text-left group ${
              isActive
                ? "border-accent bg-accent-50 shadow-md"
                : "border-neutral-200 bg-white hover:border-accent hover:shadow-subtle"
            }`}
          >
            <div className="flex items-start gap-3">
              {Icon && (
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors ${
                  isActive
                    ? "bg-accent text-white"
                    : "bg-neutral-100 text-neutral-600 group-hover:bg-accent group-hover:text-white"
                }`}>
                  <Icon className="w-5 h-5" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className={`font-semibold transition-colors ${
                  isActive ? "text-neutral-900" : "text-neutral-700 group-hover:text-neutral-900"
                }`}>
                  {tab.label}
                </p>
                {tab.description && (
                  <p className="text-xs text-neutral-500 mt-0.5 line-clamp-1">
                    {tab.description}
                  </p>
                )}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
```

---

## Pattern 3: Statistics Cards Grid

### Design Variations

#### 3-Column Statistics (Preview/Upload Step)

```tsx
function StatisticsGrid3() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* Card 1: Blue Gradient */}
      <div className="card bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200">
        <p className="text-sm text-blue-700 font-medium">Enregistrements</p>
        <p className="text-3xl font-bold text-blue-900 mt-2">{totalRecords}</p>
      </div>

      {/* Card 2: Dynamic Color (Warning/Success) */}
      <div className={`card bg-gradient-to-br ${
        duplicates > 0
          ? "from-warning-50 to-warning-100 border-warning-200"
          : "from-success-50 to-success-100 border-success-200"
      }`}>
        <p className={`text-sm font-medium ${
          duplicates > 0 ? "text-warning-700" : "text-success-700"
        }`}>
          Doublons
        </p>
        <p className={`text-3xl font-bold mt-2 ${
          duplicates > 0 ? "text-warning-900" : "text-success-900"
        }`}>
          {duplicates || 0}
        </p>
      </div>

      {/* Card 3: Status with Pulse Dot */}
      <div className="card bg-gradient-to-br from-success-50 to-success-100 border border-success-200">
        <p className="text-sm text-success-700 font-medium">Statut</p>
        <div className="flex items-center gap-2 mt-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
          <p className="text-sm font-semibold text-success-900">Prêt à importer</p>
        </div>
      </div>
    </div>
  );
}
```

#### 4-Column Statistics (Results Step)

```tsx
function StatisticsGrid4() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {/* Status Card */}
      <div className={`card ${
        status === "completed"
          ? "bg-gradient-to-br from-success-50 to-success-100 border-success-200"
          : "bg-gradient-to-br from-danger-50 to-danger-100 border-danger-200"
      }`}>
        <p className="text-xs text-neutral-600 font-semibold uppercase tracking-wider">Statut</p>
        <p className={`text-2xl font-bold mt-2 ${
          status === "completed" ? "text-success-900" : "text-danger-900"
        }`}>
          {status === "completed" ? "Réussi" : "Erreur"}
        </p>
      </div>

      {/* Imported Count */}
      <div className="card bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
        <p className="text-xs text-neutral-600 font-semibold uppercase tracking-wider">Importés</p>
        <p className="text-2xl font-bold mt-2 text-blue-900">{importedRecords || 0}</p>
      </div>

      {/* Failed Count */}
      <div className="card bg-gradient-to-br from-warning-50 to-warning-100 border-warning-200">
        <p className="text-xs text-neutral-600 font-semibold uppercase tracking-wider">Échoués</p>
        <p className="text-2xl font-bold mt-2 text-warning-900">{failedRecords || 0}</p>
      </div>

      {/* Total Count */}
      <div className="card bg-gradient-to-br from-neutral-100 to-neutral-200 border-neutral-300">
        <p className="text-xs text-neutral-600 font-semibold uppercase tracking-wider">Total</p>
        <p className="text-2xl font-bold mt-2 text-neutral-900">{totalRecords}</p>
      </div>
    </div>
  );
}
```

---

## Pattern 4: Alert/Banner Components

### Success Alert with Icon

```tsx
function SuccessAlert({ title, message }: { title: string; message: string }) {
  return (
    <div className="bg-gradient-to-r from-success-50 to-success-100 border border-success-300 rounded-lg p-5 mb-6">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-full bg-success text-white flex items-center justify-center flex-shrink-0">
          <Check className="w-6 h-6" />
        </div>
        <div className="flex-1">
          <h3 className="font-bold text-success-900 text-lg">{title}</h3>
          <p className="text-success-800 text-sm mt-1">{message}</p>
        </div>
      </div>
    </div>
  );
}
```

### Warning Alert

```tsx
function WarningAlert({ title, message }: { title: string; message: string }) {
  return (
    <div className="bg-warning-50 border border-warning-200 rounded-lg p-4 mb-6 flex gap-3">
      <AlertCircle className="w-5 h-5 text-warning-600 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-semibold text-warning-900">{title}</p>
        <p className="text-sm text-warning-800 mt-1">{message}</p>
      </div>
    </div>
  );
}
```

### Error Alert

```tsx
function ErrorAlert({ title, message }: { title: string; message: string }) {
  return (
    <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm flex items-center gap-2">
      <AlertCircle className="w-4 h-4" />
      <div>
        <p className="font-semibold">{title}</p>
        <p className="text-sm">{message}</p>
      </div>
    </div>
  );
}
```

---

## Pattern 5: Data Preview Table

### Generic Table Component

```tsx
interface TableColumn {
  key: string;
  header: string;
  render?: (value: any, row: any) => React.ReactNode;
}

interface DataTableProps {
  columns: TableColumn[];
  data: any[];
  maxRows?: number;
  className?: string;
}

export function DataTable({ columns, data, maxRows = 5, className = "" }: DataTableProps) {
  const displayData = data.slice(0, maxRows);
  const hasMore = data.length > maxRows;

  return (
    <div className={`card bg-neutral-50 border border-neutral-200 ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-neutral-200">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="text-left py-2 px-3 text-neutral-600 font-semibold"
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayData.map((row, idx) => (
              <tr
                key={idx}
                className="border-b border-neutral-100 hover:bg-neutral-100 transition-colors"
              >
                {columns.map((col) => (
                  <td key={col.key} className="py-2 px-3 text-neutral-700">
                    {col.render ? col.render(row[col.key], row) : String(row[col.key]).substring(0, 30)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {hasMore && (
        <p className="text-xs text-neutral-500 py-2 px-3 bg-neutral-100">
          ...et {data.length - maxRows} ligne(s) supplémentaire(s)
        </p>
      )}
    </div>
  );
}

// Usage
<DataTable
  columns={[
    { key: "reference", header: "Référence" },
    { key: "title", header: "Titre" },
    {
      key: "status",
      header: "Statut",
      render: (value) => (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
          {value}
        </span>
      ),
    },
  ]}
  data={previewData}
  maxRows={5}
/>
```

---

## Pattern 6: Form Input Groups

### Textarea with Counter

```tsx
function TextareaWithCounter({
  value,
  onChange,
  placeholder,
  label,
}: {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  placeholder: string;
  label: string;
}) {
  const lineCount = value.split('\n').length - 1;

  return (
    <div className="mb-6">
      <label className="block text-sm font-semibold text-neutral-900 mb-3">
        {label}
      </label>
      <textarea
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="input h-64 font-mono text-xs resize-none"
      />
      <p className="text-xs text-neutral-500 mt-2">
        {lineCount} ligne(s) de données
      </p>
    </div>
  );
}
```

### Input with Hint Box

```tsx
function InputWithHint({
  hint,
  children,
}: {
  hint: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <>
      <div className="bg-accent-50 border border-accent-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-accent-800">{hint}</p>
      </div>
      {children}
    </>
  );
}
```

---

## Pattern 7: Loading and Error States

### Loading Spinner Overlay

```tsx
function LoadingOverlay({ isLoading, children }: { isLoading: boolean; children: React.ReactNode }) {
  return (
    <div className="relative">
      {isLoading && (
        <div className="absolute inset-0 bg-white/50 rounded-lg flex items-center justify-center z-50 backdrop-blur-sm">
          <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
        </div>
      )}
      <div className={isLoading ? "opacity-50 pointer-events-none" : ""}>
        {children}
      </div>
    </div>
  );
}
```

### Button with Loading State

```tsx
function LoadingButton({
  onClick,
  disabled,
  loading,
  children,
  className = "btn-primary",
}: {
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`flex items-center gap-2 ${className} disabled:opacity-50`}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
      {children}
    </button>
  );
}
```

---

## Pattern 8: Responsive Grid Layouts

### 2-4 Column Grid

```tsx
// Automatic responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {items.map((item) => (
    <div key={item.id} className="card">{item.name}</div>
  ))}
</div>

// Custom breakpoints
<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
  {/* content */}
</div>
```

### Dynamic Column Count

```tsx
function ResponsiveGrid({
  items,
  cols = { mobile: 1, tablet: 2, desktop: 4 },
  gap = 4,
}: {
  items: React.ReactNode[];
  cols?: { mobile: number; tablet: number; desktop: number };
  gap?: number;
}) {
  const colClass = `grid-cols-${cols.mobile} sm:grid-cols-${cols.tablet} lg:grid-cols-${cols.desktop}`;

  return (
    <div className={`grid ${colClass} gap-${gap}`}>
      {items.map((item, i) => (
        <div key={i}>{item}</div>
      ))}
    </div>
  );
}
```

---

## Pattern 9: Conditional Styling

### Active/Inactive States

```tsx
// Pattern 1: Ternary in className
className={activeTab === tab.id ? "border-accent" : "border-neutral-200"}

// Pattern 2: Object mapping
const stateClasses: Record<string, string> = {
  active: "bg-accent text-white",
  inactive: "bg-neutral-100 text-neutral-600",
  disabled: "opacity-50 cursor-not-allowed",
};

className={stateClasses[state]}

// Pattern 3: Helper function
function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    success: "bg-success-50 text-success-700",
    warning: "bg-warning-50 text-warning-700",
    danger: "bg-danger-50 text-danger-700",
  };
  return colors[status] || "bg-neutral-50 text-neutral-700";
}

className={getStatusColor(status)}
```

---

## Pattern 10: Animation Transitions

### Fade In Animation

```tsx
// Tab content fade in
<div className="animate-in fade-in duration-200">
  {activeTab === "users" && <UsersManager />}
</div>
```

### Gradient Animation

```tsx
// Progress bar gradient
className="h-full bg-gradient-to-r from-accent to-accent-600 transition-all duration-300"

// Card gradient
className="bg-gradient-to-br from-success-50 to-success-100"
```

### Pulse Animation

```tsx
// Status indicator
<div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>

// Loading spinner
<Loader2 className="w-4 h-4 animate-spin" />
```

### Hover Transitions

```tsx
className="transition-all duration-200 hover:border-accent hover:shadow-md"
className="transition-colors duration-200 group-hover:bg-accent"
```

---

## Best Practices Summary

### Do's
- ✓ Use semantic HTML (button, table, form)
- ✓ Implement proper loading states
- ✓ Show clear error messages
- ✓ Use gradients for visual interest
- ✓ Keep animations under 200ms
- ✓ Test responsive on mobile/tablet/desktop
- ✓ Use consistent spacing (Tailwind scale)
- ✓ Color-code status (green=success, orange=warning, red=danger)

### Don'ts
- ✗ Don't use opacity for disabled states (use color changes)
- ✗ Don't animate more than 2-3 properties at once
- ✗ Don't mix multiple icon sizes in same component
- ✗ Don't use shadows on every element
- ✗ Don't forget accessibility (color contrast, keyboard nav)
- ✗ Don't hardcode colors (use CSS variables)
- ✗ Don't create custom animations if Tailwind has it

---

## Migration to Other Pages

To apply these patterns to other pages:

1. **Wizards**: Use Pattern 1 (Step-Based Wizard)
2. **Dashboards**: Use Pattern 2 (Tab Navigation Grid)
3. **Statistics**: Use Pattern 3 (Statistics Cards)
4. **Forms**: Use Pattern 6 (Form Input Groups)
5. **Data Display**: Use Pattern 5 (Data Tables)
6. **Loading**: Use Pattern 7 (Loading States)
7. **Responsive**: Use Pattern 8 (Grid Layouts)

---

## File References

- Patterns Used In: `apps/web/app/dashboard/migration/page.tsx`
- Patterns Used In: `apps/web/app/dashboard/admin/page.tsx`
- Related Components: `apps/web/components/ui/`
- Tailwind Config: `apps/web/tailwind.config.ts`

