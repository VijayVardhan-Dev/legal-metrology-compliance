export default function PageHeader({ eyebrow, title, children }) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
      </div>
      {children && <div className="page-header-actions">{children}</div>}
    </div>
  );
}
