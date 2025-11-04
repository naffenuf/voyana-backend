interface StatusBadgeProps {
  status: string;
  size?: 'small' | 'medium';
}

export default function StatusBadge({ status, size = 'small' }: StatusBadgeProps) {
  const statusConfig: Record<
    string,
    { label: string; classes: string }
  > = {
    pending: {
      label: 'Pending',
      classes: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    },
    reviewed: {
      label: 'Reviewed',
      classes: 'bg-blue-100 text-blue-800 border-blue-200',
    },
    resolved: {
      label: 'Resolved',
      classes: 'bg-green-100 text-green-800 border-green-200',
    },
    dismissed: {
      label: 'Dismissed',
      classes: 'bg-gray-100 text-gray-800 border-gray-200',
    },
  };

  const config = statusConfig[status] || {
    label: status,
    classes: 'bg-gray-100 text-gray-800 border-gray-200',
  };

  const sizeClasses = size === 'small' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1';

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium border ${config.classes} ${sizeClasses}`}
    >
      {config.label}
    </span>
  );
}
