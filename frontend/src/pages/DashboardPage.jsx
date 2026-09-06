import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { formatPercent, prettify, formatDate, shortId } from '../utils/format';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import EmptyState from '../components/ui/EmptyState';
import ErrorBanner from '../components/ui/ErrorBanner';
import { SkeletonCard, SkeletonTable } from '../components/ui/Skeleton';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.dashboard()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <>
        <PageHeader eyebrow="OVERVIEW" title="Dashboard" />
        <div className="stats-grid">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="stat-card"><SkeletonCard /></div>
          ))}
        </div>
        <div className="grid-2">
          <SkeletonCard /><SkeletonCard />
        </div>
        <SkeletonTable rows={5} />
      </>
    );
  }

  const s = data?.summary || {};

  return (
    <>
      <ErrorBanner error={error} onDismiss={() => setError('')} />

      <PageHeader eyebrow="OVERVIEW" title="Dashboard">
        <button className="btn btn-primary" onClick={() => navigate('/inspections/new')}>
          + New inspection
        </button>
      </PageHeader>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-card-label">Total inspections</span>
          <span className="stat-card-value">{s.total_inspections ?? '—'}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Compliant</span>
          <span className="stat-card-value tone-compliant">{s.compliant_inspections ?? '—'}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Non-compliant</span>
          <span className="stat-card-value tone-non-compliant">{s.non_compliant_inspections ?? '—'}</span>
        </div>
        <div className="stat-card">
          <span className="stat-card-label">Review required</span>
          <span className="stat-card-value tone-review">{s.review_required_inspections ?? '—'}</span>
        </div>
      </div>

      {/* Distribution charts */}
      <div className="grid-2">
        {/* Compliance distribution */}
        <section className="card">
          <div className="card-header">
            <div className="card-header-text">
              <p className="eyebrow">DISTRIBUTION</p>
              <h2>Compliance outcomes</h2>
            </div>
            {s.average_compliance_confidence != null && (
              <span className="text-tertiary">
                {formatPercent(s.average_compliance_confidence)} avg confidence
              </span>
            )}
          </div>
          <div className="bar-chart">
            {(data?.compliance?.items || []).map((item) => (
              <div className="bar-row" key={item.status}>
                <span>{prettify(item.status)}</span>
                <div className="bar-track">
                  <div
                    className={`bar-fill bar-fill-${item.status.toLowerCase()}`}
                    style={{
                      width: `${s.total_inspections ? (item.count / s.total_inspections) * 100 : 0}%`,
                    }}
                  />
                </div>
                <span className="bar-count">{item.count}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Category distribution */}
        <section className="card">
          <div className="card-header">
            <div className="card-header-text">
              <p className="eyebrow">CATEGORIES</p>
              <h2>Product mix</h2>
            </div>
          </div>
          {data?.categories?.items?.length ? (
            <div className="category-list">
              {data.categories.items.slice(0, 8).map((x) => (
                <div className="category-item" key={`${x.category}-${x.subcategory}`}>
                  <span>
                    <span className="category-name">{prettify(x.category)}</span>
                    {x.subcategory && <span className="category-sub">{prettify(x.subcategory)}</span>}
                  </span>
                  <span className="category-count">{x.inspection_count}</span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState>No category data yet.</EmptyState>
          )}
        </section>
      </div>

      {/* Recent inspections */}
      <section className="card">
        <div className="card-header">
          <div className="card-header-text">
            <p className="eyebrow">RECENT ACTIVITY</p>
            <h2>Recent inspections</h2>
          </div>
          <button className="btn-link" onClick={() => navigate('/inspections')}>
            View all →
          </button>
        </div>
        <InspectionTable items={data?.recent || []} />
      </section>
    </>
  );
}

function InspectionTable({ items }) {
  const navigate = useNavigate();

  if (!items.length) {
    return <EmptyState>No inspections have been created.</EmptyState>;
  }

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Inspection</th>
            <th>Product</th>
            <th>Category</th>
            <th>Date</th>
            <th>Compliance</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {items.map((x) => (
            <tr
              key={x.inspection_id}
              className="row-clickable"
              onClick={() => navigate(`/inspections/${x.inspection_id}`)}
              role="link"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && navigate(`/inspections/${x.inspection_id}`)}
            >
              <td><span className="cell-primary">{shortId(x.inspection_id)}</span></td>
              <td>{x.product_name}</td>
              <td>{prettify(x.category)}</td>
              <td>{formatDate(x.inspection_date)}</td>
              <td>
                {x.overall_compliance_status && (
                  <StatusBadge status={x.overall_compliance_status} />
                )}
              </td>
              <td className="confidence">{formatPercent(x.overall_confidence)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
