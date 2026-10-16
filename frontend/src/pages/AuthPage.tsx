import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router";
import { api, unwrap } from "../api/client";
import { Button, Card, ErrorText, Field, Input } from "../components/ui";

export function AuthPage({ mode }: { mode: "login" | "signup" }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const client = useQueryClient();
  const navigate = useNavigate();

  const submit = useMutation({
    mutationFn: () =>
      mode === "login"
        ? unwrap(api.POST("/api/v1/auth/login/", { body: { email, password } }))
        : unwrap(api.POST("/api/v1/auth/signup/", { body: { email, password, name } })),
    onSuccess: async (user) => {
      client.setQueryData(["me"], user);
      // Django rotates the CSRF token on login, so fetch the fresh one.
      await client.invalidateQueries({ queryKey: ["csrf"] });
      navigate("/app");
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    submit.mutate();
  }

  return (
    <div className="mx-auto max-w-md">
      <Card title={mode === "login" ? "Log in" : "Create your account"}>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          {mode === "signup" && (
            <Field label="Name">
              <Input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
            </Field>
          )}
          <Field label="Email">
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </Field>
          <Field label="Password">
            <Input
              type="password"
              required
              minLength={mode === "signup" ? 10 : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </Field>
          <ErrorText error={submit.error} />
          <Button type="submit" disabled={submit.isPending}>
            {mode === "login" ? "Log in" : "Sign up"}
          </Button>
          <p className="text-center text-sm text-slate-600">
            {mode === "login" ? (
              <>
                New here?{" "}
                <Link className="text-teal-700 underline" to="/signup">
                  Create an account
                </Link>
              </>
            ) : (
              <>
                Have an account?{" "}
                <Link className="text-teal-700 underline" to="/login">
                  Log in
                </Link>
              </>
            )}
          </p>
        </form>
      </Card>
    </div>
  );
}
