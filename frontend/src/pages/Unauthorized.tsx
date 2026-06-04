import { Link } from 'react-router-dom';

function Unauthorized() {
  return (
    <div className="page-shell">
      <section className="glass-panel notfound-panel">
        <h2>Unauthorized</h2>
        <p>You need to sign in to access this resource.</p>
        <Link to="/login" className="primary-button">
          Sign in
        </Link>
      </section>
    </div>
  );
}
export default Unauthorized;