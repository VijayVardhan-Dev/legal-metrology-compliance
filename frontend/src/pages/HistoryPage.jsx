import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { formatPercent, prettify, formatDate, shortId } from '../utils/format';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import EmptyState from '../components/ui/EmptyState';
import ErrorBanner from '../components/ui/ErrorBanner';
import { SkeletonTable } from '../components/ui/Skeleton';

export default function HistoryPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [compliance, setCompliance] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const load = useCallback(
    (params = {}) => {
      setLoading(true);
      const queryParams = {
        page: params.page ?? page,
        page_size: pageSize,
        sort_by: 'created_at',
        sort_order: 'desc',
        ...(search && { search }),
        ...(compliance && { compliance_status: compliance }),
        ...params,
      };
      api.listInspections(queryParams)
        .then(setData)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    },
    [page, search, compliance]
  );

  useEffect(() => {
    load();
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSearch(e) {
    if (e.key === 'Enter' || e.type === 'click') {
      setPage(1);
      load({ page: 1 });
    }
  }

  function handleComplianceFilter(value) {
    setCompliance(value);
    setPage(1);
    load({ page: 1, compliance_status: value });
  }

  return (
    <>
      <ErrorBanner error={error} onDismiss={() => setError('')} />

      <PageHeader eyebrow="INSPECTIONS" title="Inspection history">
        <button className="btn btn-primary" onClick={() => navigate('/inspections/new')}>
          + New inspection
        </button>
      </PageHeader>

      <section className="card">
        <div className="filters-bar">
          <input
            className="form-input"
            placeholder="Search product, report, or ID"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleSearch}
          />
          <select
            className="form-input"
            value={compliance}
            onChange={(e) => handleComplianceFilter(e.target.value)}
            style={{ flex: '0 0 auto', minWidth: 160 }}
          >
            <option value="">All outcomes</option>
            <option value="COMPLIANT">Compliant</option>
            <option value="NON_COMPLIANT">Non-compliant</option>
            <option value="REVIEW_REQUIRED">Review required</option>
          </select>
          <button className="btn" onClick={handleSearch}>
            Search
          </button>
        </div>

        {loading && !data ? (
          <SkeletonTable rows={8} />
        ) : !data?.items?.length ? (
          <EmptyState>No inspections match your filters.</EmptyState>
        ) : (
          <>
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
                    <th>Report</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((x) => (
                    <tr
                      key={x.inspection_id}
                      className="row-clickable"
                      onClick={() => navigate(`/inspections/${x.inspection_id}`)}
                      role="link"
                      tabIndex={0}
                      onKeyDown={(e) =>
                        e.key === 'Enter' && navigate(`/inspections/${x.inspection_id}`)
                      }
                    >
                      <td><span className="cell-primary">{shortId(x.inspection_id)}</span></td>
                      <td>{x.product_name}</td>
                      <td>{prettify(x.category)}</td>
                      <td>{formatDate(x.inspection_date)}</td>
                      <td>
                        {x.overall_compliance_status ? (
                          <StatusBadge status={x.overall_compliance_status} />
                        ) : (
                          <span className="text-tertiary">—</span>
                        )}
                      </td>
                      <td className="confidence">{formatPercent(x.overall_confidence)}</td>
                      <td>
                        {x.report_number ? (
                          <span className="cell-secondary">{x.report_number}</span>
                        ) : (
                          <span className="text-tertiary">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <button
                className="btn btn-sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                ← Previous
              </button>
              <span>
                Page {data.page} of {data.total_pages}
              </span>
              <button
                className="btn btn-sm"
                disabled={page >= data.total_pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </button>
            </div>
          </>
        )}
      </section>
    </>
  );
}
