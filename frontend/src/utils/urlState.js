export function readEnumParam(searchParams, key, allowedValues, defaultValue) {
  const raw = String(searchParams.get(key) || '').trim().toLowerCase();
  return allowedValues.includes(raw) ? raw : defaultValue;
}

export function readNumberEnumParam(searchParams, key, allowedValues, defaultValue) {
  const raw = Number(searchParams.get(key));
  return allowedValues.includes(raw) ? raw : defaultValue;
}

export function readBooleanFlagParam(searchParams, key, trueValue = '1') {
  return searchParams.get(key) === trueValue;
}

export function readCsvEnumSetParam(searchParams, key, allowedValues) {
  const raw = String(searchParams.get(key) || '');
  return Array.from(
    new Set(
      raw
        .split(',')
        .map((v) => v.trim().toLowerCase())
        .filter(Boolean)
        .filter((v) => allowedValues.includes(v))
    )
  );
}

export function withParam(searchParams, key, value, options = {}) {
  const { defaultValue } = options;
  const next = new URLSearchParams(searchParams.toString());

  if (
    value === undefined ||
    value === null ||
    value === '' ||
    (defaultValue !== undefined && value === defaultValue)
  ) {
    next.delete(key);
  } else {
    next.set(key, String(value));
  }

  return next;
}

export function withBooleanFlagParam(searchParams, key, enabled, trueValue = '1') {
  const next = new URLSearchParams(searchParams.toString());
  if (enabled) next.set(key, trueValue);
  else next.delete(key);
  return next;
}

export function withCsvEnumSetParam(searchParams, key, values) {
  const next = new URLSearchParams(searchParams.toString());
  if (!values?.length) {
    next.delete(key);
  } else {
    next.set(key, values.join(','));
  }
  return next;
}

export function normalizeEnumParam(searchParams, key, allowedValues, defaultValue) {
  const current = searchParams.get(key);
  if (current === null) return null;

  const normalized = readEnumParam(searchParams, key, allowedValues, defaultValue);
  const next = withParam(searchParams, key, normalized, { defaultValue });
  return next.toString() === searchParams.toString() ? null : next;
}

export function normalizeNumberEnumParam(searchParams, key, allowedValues, defaultValue) {
  const current = searchParams.get(key);
  if (current === null) return null;

  const normalized = readNumberEnumParam(searchParams, key, allowedValues, defaultValue);
  const next = withParam(searchParams, key, normalized, { defaultValue });
  return next.toString() === searchParams.toString() ? null : next;
}

export function normalizeBooleanFlagParam(searchParams, key, trueValue = '1') {
  const current = searchParams.get(key);
  if (current === null) return null;
  if (current === trueValue || current === '0') return null;

  const next = new URLSearchParams(searchParams.toString());
  next.delete(key);
  return next;
}

export function normalizeCsvEnumSetParam(searchParams, key, allowedValues) {
  const current = searchParams.get(key);
  if (current === null) return null;

  const normalized = readCsvEnumSetParam(searchParams, key, allowedValues);
  const next = withCsvEnumSetParam(searchParams, key, normalized);
  return next.toString() === searchParams.toString() ? null : next;
}
