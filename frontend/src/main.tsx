import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { Layout } from "./components/Layout";
import { i18nReady } from "./i18n";
import "./index.css";
import { applyTheme, readTheme } from "./lib/theme";

// One chunk per page: the playground doesn't download the org settings screens.
const AuthPage = lazy(() => import("./pages/AuthPage").then((m) => ({ default: m.AuthPage })));
const CalendarPage = lazy(() =>
  import("./pages/CalendarPage").then((m) => ({ default: m.CalendarPage })),
);
const CalendarSettingsPage = lazy(() =>
  import("./pages/CalendarSettingsPage").then((m) => ({ default: m.CalendarSettingsPage })),
);
const InvitePage = lazy(() =>
  import("./pages/InvitePage").then((m) => ({ default: m.InvitePage })),
);
const NotFoundPage = lazy(() =>
  import("./pages/NotFoundPage").then((m) => ({ default: m.NotFoundPage })),
);
const OrgPage = lazy(() => import("./pages/OrgPage").then((m) => ({ default: m.OrgPage })));
const OrgSettingsPage = lazy(() =>
  import("./pages/OrgSettingsPage").then((m) => ({ default: m.OrgSettingsPage })),
);
const OrgsPage = lazy(() => import("./pages/OrgsPage").then((m) => ({ default: m.OrgsPage })));
const PlaygroundPage = lazy(() =>
  import("./pages/PlaygroundPage").then((m) => ({ default: m.PlaygroundPage })),
);
const UnsubscribePage = lazy(() =>
  import("./pages/UnsubscribePage").then((m) => ({ default: m.UnsubscribePage })),
);

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

applyTheme(readTheme());

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element");

await i18nReady;

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/playground" replace />} />
            <Route path="playground" element={<PlaygroundPage />} />
            <Route path="login" element={<AuthPage mode="login" />} />
            <Route path="signup" element={<AuthPage mode="signup" />} />
            <Route path="unsubscribe" element={<UnsubscribePage />} />
            <Route path="invite" element={<InvitePage />} />
            <Route path="app" element={<OrgsPage />} />
            <Route path="app/:org" element={<OrgPage />} />
            <Route path="app/:org/settings" element={<OrgSettingsPage />} />
            <Route path="app/:org/calendars/:id" element={<CalendarPage />} />
            <Route path="app/:org/calendars/:id/settings" element={<CalendarSettingsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
