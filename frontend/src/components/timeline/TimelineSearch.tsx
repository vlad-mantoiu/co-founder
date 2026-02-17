"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Search } from "lucide-react";

export interface SearchParams {
  query: string;
  typeFilter: string | null;
  dateFrom: string | null;
  dateTo: string | null;
}

interface TimelineSearchProps {
  onSearch: (params: SearchParams) => void;
}

const TYPE_OPTIONS = [
  { value: "", label: "All Types" },
  { value: "decision", label: "Decisions" },
  { value: "milestone", label: "Milestones" },
  { value: "artifact", label: "Artifacts" },
];

export function TimelineSearch({ onSearch }: TimelineSearchProps) {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const notifySearch = useCallback(
    (q: string, tf: string, df: string, dt: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onSearch({
          query: q,
          typeFilter: tf || null,
          dateFrom: df || null,
          dateTo: dt || null,
        });
      }, 300);
    },
    [onSearch],
  );

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const handleQueryChange = (value: string) => {
    setQuery(value);
    notifySearch(value, typeFilter, dateFrom, dateTo);
  };

  const handleTypeChange = (value: string) => {
    setTypeFilter(value);
    notifySearch(query, value, dateFrom, dateTo);
  };

  const handleDateFromChange = (value: string) => {
    setDateFrom(value);
    notifySearch(query, typeFilter, value, dateTo);
  };

  const handleDateToChange = (value: string) => {
    setDateTo(value);
    notifySearch(query, typeFilter, dateFrom, value);
  };

  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 p-3 rounded-xl border border-white/5 bg-white/[0.02]">
      {/* Text search */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
        <input
          type="text"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          placeholder="Search timeline..."
          className="w-full pl-9 pr-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-brand/40 focus:bg-white/[0.07] transition-colors"
        />
      </div>

      {/* Type filter */}
      <select
        value={typeFilter}
        onChange={(e) => handleTypeChange(e.target.value)}
        className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:outline-none focus:border-brand/40 transition-colors appearance-none cursor-pointer min-w-[140px]"
      >
        {TYPE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-zinc-900 text-white">
            {opt.label}
          </option>
        ))}
      </select>

      {/* Date range */}
      <div className="flex items-center gap-2">
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => handleDateFromChange(e.target.value)}
          className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:outline-none focus:border-brand/40 transition-colors cursor-pointer"
          title="From date"
        />
        <span className="text-white/30 text-xs">to</span>
        <input
          type="date"
          value={dateTo}
          onChange={(e) => handleDateToChange(e.target.value)}
          className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:outline-none focus:border-brand/40 transition-colors cursor-pointer"
          title="To date"
        />
      </div>
    </div>
  );
}
