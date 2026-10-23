// Google reCAPTCHA, loaded only on the forms that use it. The page CSP trusts this script through
// 'strict-dynamic': it is added by the app's own nonced code (backend/config/spa.py).

export type Grecaptcha = {
  ready(callback: () => void): void;
  execute(siteKey: string, options: { action: string }): Promise<string>;
  render(
    element: HTMLElement,
    options: {
      sitekey: string;
      theme: "light" | "dark";
      size: "normal" | "compact";
      callback: (token: string) => void;
      "expired-callback": () => void;
      "error-callback": () => void;
    },
  ): number;
  reset(widget?: number): void;
};

declare global {
  interface Window {
    grecaptcha?: Grecaptcha;
  }
}

let loading: Promise<Grecaptcha> | null = null;

export function loadRecaptcha(v3Key: string | null, language: string): Promise<Grecaptcha> {
  loading ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    const params = new URLSearchParams({ render: v3Key ?? "explicit", hl: language });
    script.src = `https://www.google.com/recaptcha/api.js?${params}`;
    script.async = true;
    script.onload = () => {
      const g = window.grecaptcha;
      if (g) g.ready(() => resolve(g));
      else reject(new Error("reCAPTCHA did not load"));
    };
    script.onerror = () => {
      loading = null;
      reject(new Error("reCAPTCHA did not load"));
    };
    document.head.append(script);
  });
  return loading;
}

/** The checkbox is 304 px wide; narrower than that it has to use Google's compact layout. */
export function checkboxSize(width: number): "normal" | "compact" {
  return width < 304 ? "compact" : "normal";
}

export function pageTheme(root: HTMLElement = document.documentElement): "light" | "dark" {
  const chosen = root.dataset.theme;
  if (chosen === "light" || chosen === "dark") return chosen;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
