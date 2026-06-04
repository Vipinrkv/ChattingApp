import { Link } from 'react-router-dom';

function NotFound() {
  return (
    <div className="page-shell">
      <section className="glass-panel notfound-panel">
        <h2>404 — Page not found</h2>
        <p>The page you were looking for does not exist.</p>
        <Link to="/" className="primary-button">
          Back to dashboard
        </Link>
      </section>
    </div>
  );
}

export default NotFound;
