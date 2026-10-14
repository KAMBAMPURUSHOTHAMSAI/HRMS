
import { Construction } from "lucide-react";

export default function ModulePlaceholder({
  title,
  description = "This module's interface will be implemented in the next coding step.",
}) {
  return (
    <section className="module-placeholder">
      <span className="placeholder-icon">
        <Construction size={24} />
      </span>

      <h2>{title}</h2>

      <p>{description}</p>

      <span className="placeholder-label">
        Frontend module in progress
      </span>
    </section>
  );
}
