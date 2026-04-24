export function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-gray-200 dark:border-white/10 pt-8 first:border-t-0 first:pt-0">
      <div className="mb-5">
        <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">
          {title}
        </h3>
        {description ? (
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {description}
          </p>
        ) : null}
      </div>
      <div className="space-y-5">{children}</div>
    </section>
  );
}

export function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1.5">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:border-gray-400 dark:focus:border-white/30 transition-colors"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  );
}

export function TextField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1.5">
        {label}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:border-gray-400 dark:focus:border-white/30 transition-colors"
      />
    </div>
  );
}

export function NumberField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
}) {
  const id = `field-${label.toLowerCase().replace(/\s+/g, '-')}`;
  return (
    <div>
      <label htmlFor={id} className="block text-sm text-gray-700 dark:text-gray-300 mb-1.5">
        {label}
      </label>
      <input
        id={id}
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full rounded-lg border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 text-gray-900 dark:text-gray-100 px-3 py-2 text-sm focus:outline-none focus:border-gray-400 dark:focus:border-white/30 transition-colors"
      />
    </div>
  );
}

export function KeyStatus({ label, present }: { label: string; present: boolean }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
      <span
        className={`inline-block h-1.5 w-1.5 rounded-full ${
          present
            ? 'bg-gray-900 dark:bg-gray-100'
            : 'bg-gray-300 dark:bg-white/25'
        }`}
        aria-hidden="true"
      />
      <span>
        {label ? `${label} ` : ''}{present ? 'Set' : 'Not set'}
      </span>
    </div>
  );
}
