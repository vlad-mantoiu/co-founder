# Deferred Items - Phase 08-06

## Build Error - Next.js 15 Async Params

**Issue:** Build fails due to Next.js 15 breaking change in `app/(dashboard)/company/[projectId]/page.tsx`

**Error:**
```
Type 'CompanyDashboardPageProps' does not satisfy the constraint 'PageProps'.
  Types of property 'params' are incompatible.
    Type '{ projectId: string; }' is missing the following properties from type 'Promise<any>': then, catch, finally, [Symbol.toStringTag]
```

**Root Cause:** Next.js 15 changed `params` to be async (returns Promise). This file needs to be updated to:
```typescript
interface CompanyDashboardPageProps {
  params: Promise<{ projectId: string; }>;
}

export default async function CompanyDashboardPage({ params }: CompanyDashboardPageProps) {
  const { projectId } = await params;
  // ... rest of component
}
```

**Scope:** Pre-existing issue in unrelated file. Not caused by Phase 08-06 changes.

**Action:** Deferred for future fix. Does not block Phase 08 functionality.
