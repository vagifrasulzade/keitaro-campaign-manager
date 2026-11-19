import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { api, errorText } from "../api/client";
import type { Offer } from "../api/types";
import { useToast } from "./Toast";
import { INPUT_CLASS, Tag } from "./ui";

const DEBOUNCE_MS = 250;

interface Props {
  onSelect: (offer: Offer) => void;
  id?: string;
  placeholder?: string;
  autoFocus?: boolean;
}

export function OfferAutocomplete({ onSelect, id, placeholder = "Search by name or ID…", autoFocus = false }: Props) {
  const toast = useToast();
  const listId = useId();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Offer[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const lastRequest = useRef(0);
  const timer = useRef<number | undefined>(undefined);
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  useEffect(() => {
    listRef.current?.children[highlighted]?.scrollIntoView({ block: "nearest" });
  }, [highlighted]);

  const search = useCallback(
    (q: string, delay: number) => {
      window.clearTimeout(timer.current);
      // every new search invalidates the ones still in flight, so an older response
      // (e.g. the empty query sent on focus) never overwrites newer results
      const requestId = ++lastRequest.current;
      setLoading(true);
      timer.current = window.setTimeout(async () => {
        try {
          const offers = await api.searchOffers(q.trim());
          if (requestId !== lastRequest.current) return;
          setResults(offers);
          setHighlighted(0);
        } catch (err) {
          if (requestId === lastRequest.current) toast(errorText(err), "error");
        } finally {
          if (requestId === lastRequest.current) setLoading(false);
        }
      }, delay);
    },
    [toast],
  );

  function pick(offer: Offer) {
    window.clearTimeout(timer.current);
    lastRequest.current++;
    setLoading(false);
    setQuery("");
    setResults([]);
    setOpen(false);
    onSelect(offer);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        if (!open) {
          setOpen(true);
          search(query, 0);
        } else {
          setHighlighted((i) => Math.min(i + 1, Math.max(results.length - 1, 0)));
        }
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlighted((i) => Math.max(i - 1, 0));
        break;
      case "Enter":
        if (!open) return;
        e.preventDefault(); // never submit the surrounding form while the list is open
        // results may still belong to the previous query
        if (!loading && results[highlighted]) pick(results[highlighted]);
        break;
      case "Escape":
        if (open) {
          e.preventDefault();
          setOpen(false);
        }
        break;
    }
  }

  const activeOption = open && results[highlighted] ? `${listId}-${highlighted}` : undefined;

  return (
    <div className="relative">
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={activeOption}
        autoComplete="off"
        autoFocus={autoFocus}
        placeholder={placeholder}
        className={INPUT_CLASS}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          search(e.target.value, DEBOUNCE_MS);
        }}
        onFocus={() => {
          setOpen(true);
          search(query, 0);
        }}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
      />
      {open && (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded border border-gray-200 bg-white py-1 text-sm shadow-lg"
        >
          {results.length === 0 ? (
            <li className="px-3 py-2 text-gray-500">{loading ? "Searching…" : "No offers found"}</li>
          ) : (
            results.map((offer, i) => (
              <li
                key={offer.id}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === highlighted}
                className={`flex cursor-pointer items-center gap-2 px-3 py-1.5 ${i === highlighted ? "bg-green-50" : ""}`}
                onMouseEnter={() => setHighlighted(i)}
                // mousedown + preventDefault: pick before the input's blur closes the list
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(offer);
                }}
              >
                <span className="shrink-0 text-gray-500">[{offer.id}]</span>
                <span className="min-w-0 flex-1 truncate" title={offer.name}>
                  {offer.name}
                </span>
                {offer.country.length > 0 && <Tag>{offer.country.join(", ")}</Tag>}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
