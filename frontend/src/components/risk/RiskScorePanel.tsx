import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line } from 'recharts';
import type { RiskScore } from '@/types';
import { RiskLevelBadge } from './RiskLevelBadge';

const CATEGORY_COLORS: Record<string, string> = {
  climate: '#0891b2',
  geopolitical: '#dc2626',
  operational: '#ea580c',
  logistics: '#7c3aed',
  dependency: '#ca8a04',
  financial: '#16a34a',
};

interface Props {
  score: RiskScore;
  history?: Array<{ overall_score: number; calculated_at: string }>;
}

export function RiskScorePanel({ score, history }: Props) {
  const barData = Object.entries(score.category_scores).map(([cat, val]) => ({
    category: cat.charAt(0).toUpperCase() + cat.slice(1),
    score: val,
    color: CATEGORY_COLORS[cat] || '#6b7280',
  }));

  const trendData = history
    ? [...history].reverse().map(h => ({
        date: new Date(h.calculated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
        score: h.overall_score,
      }))
    : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {/* Overall score */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <p className="card__title">Overall Risk Score</p>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--space-3)', marginTop: 'var(--space-2)' }}>
              <span style={{
                fontSize: 56,
                fontWeight: 700,
                letterSpacing: '-0.04em',
                color: scoreColor(score.overall_score),
                lineHeight: 1,
              }}>
                {Math.round(score.overall_score)}
              </span>
              <span style={{ fontSize: 'var(--text-lg)', color: 'var(--color-text-muted)' }}>/100</span>
              <RiskLevelBadge level={score.risk_level} large />
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p className="text-muted">Calculated</p>
            <p className="text-sm" style={{ fontWeight: 500 }}>{new Date(score.calculated_at).toLocaleString()}</p>
            <p className="text-muted" style={{ marginTop: 4 }}>Engine v{score.scoring_version}</p>
          </div>
        </div>

        <div className="risk-score-bar" style={{ marginTop: 'var(--space-4)', height: 10 }}>
          <div
            className={`risk-score-bar__fill risk-score-bar__fill--${score.risk_level}`}
            style={{ width: `${score.overall_score}%` }}
          />
        </div>
      </div>

      {trendData.length > 1 && (
        <div className="card">
          <p className="card__title" style={{ marginBottom: 'var(--space-3)' }}>Score Trend</p>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={trendData} margin={{ top: 4, right: 12, bottom: 4, left: -20 }}>
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => [Math.round(v), 'Score']} />
              <Line type="monotone" dataKey="score" stroke="var(--color-accent)" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid-2">
        {/* Category breakdown */}
        <div className="card">
          <p className="card__title" style={{ marginBottom: 'var(--space-4)' }}>Category Breakdown</p>
          <div className="score-breakdown">
            {Object.entries(score.category_scores).map(([cat, val]) => (
              <div key={cat} className="score-item">
                <span className="score-item__label">{cat}</span>
                <div className="risk-score-bar" style={{ flex: 1 }}>
                  <div
                    className="risk-score-bar__fill"
                    style={{ width: `${val}%`, background: CATEGORY_COLORS[cat] }}
                  />
                </div>
                <span className="score-item__value">{Math.round(val)}</span>
              </div>
            ))}
          </div>

          <ResponsiveContainer width="100%" height={160} style={{ marginTop: 'var(--space-4)' }}>
            <BarChart data={barData} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
              <XAxis dataKey="category" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => [Math.round(v), 'Score']} />
              <Bar dataKey="score" radius={[3, 3, 0, 0]}>
                {barData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Weights */}
        <div className="card">
          <p className="card__title" style={{ marginBottom: 'var(--space-4)' }}>Score Weights</p>
          <div className="score-breakdown">
            {Object.entries(score.weights).map(([cat, weight]) => (
              <div key={cat} className="score-item">
                <span className="score-item__label">{cat}</span>
                <div className="risk-score-bar" style={{ flex: 1 }}>
                  <div
                    className="risk-score-bar__fill"
                    style={{ width: `${(weight as number) * 100}%`, background: CATEGORY_COLORS[cat] }}
                  />
                </div>
                <span className="score-item__value">{Math.round((weight as number) * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Contributing factors */}
      <div className="card">
        <p className="card__title" style={{ marginBottom: 'var(--space-4)' }}>Contributing Factors</p>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-3)' }}>
          All factors derived from real data sources. No black-box scoring.
        </p>
        {score.contributing_factors.length === 0 ? (
          <p className="text-muted">No significant risk factors detected</p>
        ) : (
          <div className="table-container" style={{ border: 'none' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Factor</th>
                  <th>Category</th>
                  <th>Impact</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {score.contributing_factors.map((f, i) => (
                  <tr key={i}>
                    <td>
                      <p style={{ fontWeight: 500 }}>{f.description}</p>
                      {f.evidence && <p className="text-muted">{f.evidence}</p>}
                    </td>
                    <td>
                      <span style={{
                        display: 'inline-block', padding: '2px 8px', borderRadius: 100,
                        background: CATEGORY_COLORS[f.category] + '18',
                        color: CATEGORY_COLORS[f.category],
                        fontSize: 'var(--text-xs)', fontWeight: 600,
                        textTransform: 'capitalize',
                      }}>
                        {f.category}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600, color: f.score_contribution > 20 ? 'var(--color-risk-high)' : 'var(--color-text-primary)' }}>
                        +{Math.round(f.score_contribution)}
                      </span>
                    </td>
                    <td><span className="font-mono text-sm text-muted">{f.source}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-3)' }}>
          Data sources: {score.data_sources.join(', ')}
        </p>
      </div>
    </div>
  );
}

function scoreColor(score: number) {
  if (score >= 75) return 'var(--color-risk-critical)';
  if (score >= 50) return 'var(--color-risk-high)';
  if (score >= 25) return 'var(--color-risk-medium)';
  return 'var(--color-risk-low)';
}
