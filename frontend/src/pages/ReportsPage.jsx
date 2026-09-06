import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { prettify, formatDate } from '../utils/format';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import EmptyState from '../components/ui/EmptyState';
import ErrorBanner from '../components/ui/ErrorBanner';
import { SkeletonTable } from '../components/ui/Skeleton';

export default function ReportsPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.listInspections({ page: 1, page_size: 100, sort_by: 'created_at', sort_order: 'desc' })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const reportsOnly = (data?.items || []).filter((x) => x.report_number);

  return (
    <>
      <ErrorBanner error={error} onDismiss={() => setError('')} />

      <PageHeader eyebrow="DOCUMENTS" title="Reports" />

      <section className="card">
        {loading ? (
          <SkeletonTable rows={6} />
        ) : !reportsOnly.length ? (
          <EmptyState>No reports have been generated.</EmptyState>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Report number</th>
                  <th>Product</th>
                  <th>Outcome</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reportsOnly.map((x) => (
                  <tr key={x.inspection_id}>
                    <td>
                      <span className="cell-primary">{x.report_number}</span>
                    </td>
                    <td>
                      <button
                        className="btn-link"
                        onClick={() => navigate(`/inspections/${x.inspection_id}`)}
                      >
                        {x.product_name}
                      </button>
                    </td>
                    <td>
                      {x.overall_compliance_status && (
                        <StatusBadge status={x.overall_compliance_status} />
                      )}
                    </td>
                    <td>{formatDate(x.inspection_date)}</td>
                    <td>
                      <a
                        className="btn-link"
                        href={api.reportDownloadUrl(x.inspection_id)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Download PDF
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
