import { money, label, type Value } from "./api";

export function RecordView({ value }: Readonly<{ value: Value }>) {
  if (value === null) return <span>None</span>;
  if (Array.isArray(value))
    return (
      <ul>
        {value.map((item, i) => (
          <li key={i}>
            <RecordView value={item} />
          </li>
        ))}
      </ul>
    );
  if (typeof value === "object")
    return (
      <dl>
        {Object.entries(value).map(([key, item]) => (
          <div key={key}>
            <dt>{label(key)}</dt>
            <dd>
              <RecordView
                value={
                  typeof item === "number" &&
                  (key.includes("amount") ||
                    key.includes("cost") ||
                    key.endsWith("max") ||
                    key.includes("limit") ||
                    key === "deductible")
                    ? money(item)
                    : item
                }
              />
            </dd>
          </div>
        ))}
      </dl>
    );
  return <span>{String(value)}</span>;
}
