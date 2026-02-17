export default function SkeletonTable() {
  return (
    <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
      <table className="w-full">
        {/* Header */}
        <thead>
          <tr className="border-b border-neutral-200">
            <th className="text-left px-6 py-3">
              <div className="h-3 bg-neutral-100 rounded w-20 animate-pulse" />
            </th>
            <th className="text-left px-6 py-3">
              <div className="h-3 bg-neutral-100 rounded w-24 animate-pulse" />
            </th>
            <th className="text-left px-6 py-3">
              <div className="h-3 bg-neutral-100 rounded w-16 animate-pulse" />
            </th>
            <th className="text-left px-6 py-3">
              <div className="h-3 bg-neutral-100 rounded w-20 animate-pulse" />
            </th>
            <th className="text-left px-6 py-3">
              <div className="h-3 bg-neutral-100 rounded w-24 animate-pulse" />
            </th>
          </tr>
        </thead>

        {/* Body - 5 rows */}
        <tbody className="divide-y divide-neutral-100">
          {[...Array(5)].map((_, i) => (
            <tr key={i} className="animate-pulse">
              <td className="px-6 py-4">
                <div className="h-4 bg-neutral-100 rounded w-24" />
              </td>
              <td className="px-6 py-4">
                <div className="h-4 bg-neutral-100 rounded w-40" />
              </td>
              <td className="px-6 py-4">
                <div className="h-5 bg-neutral-100 rounded-full w-16" />
              </td>
              <td className="px-6 py-4">
                <div className="h-4 bg-neutral-100 rounded w-20" />
              </td>
              <td className="px-6 py-4">
                <div className="h-4 bg-neutral-100 rounded w-28" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
