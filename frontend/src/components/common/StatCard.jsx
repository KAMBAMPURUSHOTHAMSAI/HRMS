export default function StatCard({
  label,
  value,
  description,
  icon: Icon,
}) {
  return (
    <article className="stat-card">
      <div className="stat-card-top">
        <span>{label}</span>

        {Icon && (
          <span className="stat-icon">
            <Icon size={20} />
          </span>
        )}
      </div>

      <div className="stat-value">{value}</div>

      {description && (
        <p className="stat-description">{description}</p>
      )}
    </article>
  );
}