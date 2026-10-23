import {
  Children,
  isValidElement,
  type KeyboardEvent,
  type ReactElement,
  type ReactNode,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";

type OptionProps = { value?: string; children?: ReactNode; disabled?: boolean };
type Choice = { value: string; label: string; disabled: boolean };

// Lists longer than this get a search box (countries, subdivisions).
const SEARCH_FROM = 12;

function text(node: ReactNode): string {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(text).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return text(node.props.children);
  return "";
}

function choices(children: ReactNode): Choice[] {
  return Children.toArray(children)
    .filter((child): child is ReactElement<OptionProps> => isValidElement(child))
    .map((child) => ({
      value: String(child.props.value ?? ""),
      label: text(child.props.children),
      disabled: Boolean(child.props.disabled),
    }));
}

function fold(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase();
}

/** A themed stand-in for a native <select>: same props (`value`, `onChange(e)` with
 * `e.target.value`, <option> children), but the open list is drawn in the page's colours instead
 * of the operating system's, in light and dark and in RTL. */
export function Select({
  value,
  onChange,
  children,
  id,
  className = "",
  disabled = false,
  "aria-label": ariaLabel,
}: {
  value: string;
  onChange: (event: { target: { value: string } }) => void;
  children: ReactNode;
  id?: string;
  className?: string;
  disabled?: boolean;
  "aria-label"?: string;
}) {
  const { t } = useTranslation();
  const listId = useId();
  const options = useMemo(() => choices(children), [children]);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [upward, setUpward] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const searchable = options.length > SEARCH_FROM;

  const shown = useMemo(() => {
    const needle = fold(query.trim());
    if (!needle) return options;
    return options.filter((o) => fold(o.label).includes(needle) || fold(o.value) === needle);
  }, [options, query]);

  const selected = options.find((o) => o.value === value);

  function show() {
    if (disabled) return;
    const box = trigger.current?.getBoundingClientRect();
    if (box) setUpward(window.innerHeight - box.bottom < 300 && box.top > window.innerHeight / 2);
    setQuery("");
    setActive(
      Math.max(
        0,
        options.findIndex((o) => o.value === value),
      ),
    );
    setOpen(true);
  }

  function close(refocus = true) {
    setOpen(false);
    if (refocus) trigger.current?.focus();
  }

  function pick(choice: Choice | undefined) {
    if (!choice || choice.disabled) return;
    if (choice.value !== value) onChange({ target: { value: choice.value } });
    close();
  }

  useEffect(() => {
    if (!open) return;
    (searchable ? panel.current?.querySelector("input") : list.current)?.focus();
    function outside(event: PointerEvent) {
      if (!root.current?.contains(event.target as Node)) close(false);
    }
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open, searchable]);

  useEffect(() => {
    if (open)
      list.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [open, active]);

  function move(step: number) {
    if (!shown.length) return;
    let next = active;
    for (let i = 0; i < shown.length; i++) {
      next = (next + step + shown.length) % shown.length;
      if (!shown[next]?.disabled) break;
    }
    setActive(next);
  }

  function onListKey(event: KeyboardEvent) {
    const keys: Record<string, () => void> = {
      ArrowDown: () => move(1),
      ArrowUp: () => move(-1),
      Home: () => setActive(0),
      End: () => setActive(shown.length - 1),
      Enter: () => pick(shown[active]),
      Escape: () => close(),
      Tab: () => close(false),
    };
    const action = keys[event.key];
    if (action) {
      if (event.key !== "Tab") event.preventDefault();
      action();
      return;
    }
    // Without a search box, typing jumps to the first option that starts with the letter.
    if (!searchable && event.key.length === 1) {
      const start = fold(event.key);
      const index = shown.findIndex((o) => fold(o.label).startsWith(start));
      if (index >= 0) setActive(index);
    }
  }

  function onTriggerKey(event: KeyboardEvent) {
    if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
      event.preventDefault();
      show();
    }
  }

  const activeId = shown[active] ? `${listId}-${active}` : undefined;

  return (
    <div ref={root} className={`relative ${className}`}>
      <button
        ref={trigger}
        id={id}
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-label={ariaLabel}
        onClick={() => (open ? close() : show())}
        onKeyDown={onTriggerKey}
        className="dropdown-trigger flex w-full min-w-0 items-center justify-between gap-2 rounded-lg border border-line bg-surface px-3 py-2 text-start text-ink transition-colors hover:border-accent focus:border-accent focus:ring-2 focus:ring-accent/20 focus:outline-none disabled:opacity-60 aria-expanded:border-accent"
      >
        <span className="truncate">{selected?.label ?? ""}</span>
        <svg
          viewBox="0 0 20 20"
          aria-hidden="true"
          className={`size-4 shrink-0 fill-none stroke-muted stroke-2 transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M5 8l5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        // Field wraps controls in a <label>: without this, a click in the list would also
        // "click" the trigger through the label and reopen it.
        <div
          ref={panel}
          onClick={(event) => event.preventDefault()}
          className={`dropdown-panel absolute inset-x-0 z-40 min-w-[12rem] overflow-hidden rounded-xl border border-line bg-surface shadow-[0_18px_40px_-18px] shadow-night/50 ${upward ? "bottom-full mb-1.5" : "top-full mt-1.5"}`}
        >
          {searchable && (
            <div className="border-b border-line p-2">
              <input
                type="search"
                role="combobox"
                aria-expanded="true"
                aria-controls={listId}
                aria-activedescendant={activeId}
                aria-autocomplete="list"
                aria-label={t("dropdown.search")}
                placeholder={t("dropdown.search")}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setActive(0);
                }}
                onKeyDown={onListKey}
                className="w-full rounded-lg border border-line bg-paper px-3 py-1.5 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none"
              />
            </div>
          )}
          <ul
            ref={list}
            id={listId}
            role="listbox"
            tabIndex={searchable ? -1 : 0}
            aria-label={ariaLabel}
            aria-activedescendant={searchable ? undefined : activeId}
            onKeyDown={searchable ? undefined : onListKey}
            className="max-h-72 overflow-y-auto overscroll-contain p-1 focus:outline-none"
          >
            {shown.map((option, index) => (
              <li
                key={option.value}
                id={`${listId}-${index}`}
                data-index={index}
                role="option"
                aria-selected={option.value === value}
                aria-disabled={option.disabled || undefined}
                onPointerMove={() => setActive(index)}
                onClick={() => pick(option)}
                className={`flex cursor-pointer items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm ${index === active ? "bg-accent-soft text-ink" : "text-ink"} ${option.value === value ? "font-semibold" : ""} aria-disabled:cursor-not-allowed aria-disabled:opacity-50`}
              >
                <span className="min-w-0 break-words">{option.label}</span>
                {option.value === value && (
                  <svg
                    viewBox="0 0 20 20"
                    aria-hidden="true"
                    className="size-4 shrink-0 fill-none stroke-accent stroke-2"
                  >
                    <path d="M4 10.5l4 4 8-9" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </li>
            ))}
            {!shown.length && (
              <li role="presentation" className="px-3 py-2 text-sm text-muted">
                {t("dropdown.empty")}
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
