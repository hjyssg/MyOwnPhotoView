import React from 'react';
import { Link, useLocation } from 'react-router-dom';

function Navigation() {
  const location = useLocation();
  const isSettings = location.pathname === '/settings' || location.pathname === '/scan';

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
      <Link to="/busy-days" className={location.pathname === '/busy-days' ? 'active' : ''}>
        Busy Days
      </Link>
      <Link to="/settings" className={isSettings ? 'active' : ''}>
        Settings
      </Link>
    </nav>
  );
}

export default Navigation;
