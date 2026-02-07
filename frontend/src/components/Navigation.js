import React from 'react';
import { Link, useLocation } from 'react-router-dom';

function Navigation() {
  const location = useLocation();

  return (
    <nav className="nav-bar">
      <Link to="/" className={location.pathname === '/' ? 'active' : ''}>
        Timeline
      </Link>
      <Link to="/map" className={location.pathname === '/map' ? 'active' : ''}>
        Map
      </Link>
      <Link to="/albums" className={location.pathname === '/albums' ? 'active' : ''}>
        Albums
      </Link>
    </nav>
  );
}

export default Navigation;
