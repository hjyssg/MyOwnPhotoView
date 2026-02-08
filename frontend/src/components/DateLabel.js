import React from 'react';

function getDateHref(value, groupBy = 'day') {
  if (!value) return null;
  if (groupBy === 'month') return `/date/month/${value}`;
  if (groupBy === 'year') return `/date/year/${value}`;
  return `/date/day/${value}`;
}

function DateLabel({ value, groupBy = 'day', clickable = false, className = 'group-title-link' }) {
  if (!clickable) return value;

  const href = getDateHref(value, groupBy);
  if (!href) return value;

  return (
    <a href={href} target="_blank" rel="noreferrer" className={className}>
      {value}
    </a>
  );
}

export default DateLabel;
