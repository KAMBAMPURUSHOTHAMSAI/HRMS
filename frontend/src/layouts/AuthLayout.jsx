export default function AuthLayout({ children }) {
  return (
    <main className="auth-page">
      <section className="auth-intro">
        <div className="auth-intro-inner">
          <span className="brand-mark brand-mark-large">H</span>

          <p className="auth-kicker">PEOPLE · OPERATIONS · GROWTH</p>

          <h1>Manage your people with clarity.</h1>

          <p className="auth-description">
            One workspace for employee information, attendance,
            leave requests and payroll.
          </p>
        </div>

        <p className="auth-copyright">
          Human Resource Management System
        </p>
      </section>

      <section className="auth-form-area">
        {children}
      </section>
    </main>
  );
}