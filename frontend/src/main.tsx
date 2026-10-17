import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import { Layout } from "./components/Layout";
import "./i18n";
import "./index.css";
import { AuthPage } from "./pages/AuthPage";
import { CalendarPage } from "./pages/CalendarPage";
import { CalendarSettingsPage } from "./pages/CalendarSettingsPage";
import { InvitePage } from "./pages/InvitePage";
import { OrgPage } from "./pages/OrgPage";
import { OrgSettingsPage } from "./pages/OrgSettingsPage";
import { OrgsPage } from "./pages/OrgsPage";
import { PlaygroundPage } from "./pages/PlaygroundPage";
import { UnsubscribePage } from "./pages/UnsubscribePage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element");

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<PlaygroundPage />} />
            <Route path="login" element={<AuthPage mode="login" />} />
            <Route path="signup" element={<AuthPage mode="signup" />} />
            <Route path="unsubscribe" element={<UnsubscribePage />} />
            <Route path="invite" element={<InvitePage />} />
            <Route path="app" element={<OrgsPage />} />
            <Route path="app/:org" element={<OrgPage />} />
            <Route path="app/:org/settings" element={<OrgSettingsPage />} />
            <Route path="app/:org/calendars/:id" element={<CalendarPage />} />
            <Route path="app/:org/calendars/:id/settings" element={<CalendarSettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
