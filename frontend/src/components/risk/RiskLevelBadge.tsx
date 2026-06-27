import type { RiskLevel } from '@/types';

interface Props {
  level: RiskLevel | string;
  large?: boolean;
}

const LABELS: Record<string, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

export function RiskLevelBadge({ level, large }: Props) {
  return (
    <span
      className={`badge badge--${level}`}
      style={large ? { fontSize: 'var(--text-sm)', padding: '4px 12px' } : undefined}
    >
      {LABELS[level] ?? level}
    </span>
  );
}
