import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type Schemas, unwrap } from "../../api/client";
import { CodeInput } from "../../pages/ForgotPasswordPage";
import { Button, ErrorText } from "../ui";

/** For a signed-in account whose address nobody has confirmed yet (a Microsoft sign-in can
 * arrive that way): organizations, invites and digests wait for it. */
export function VerifyBanner({ me }: { me: Schemas["User"] }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [code, setCode] = useState("");
  const send = useMutation({
    mutationFn: () =>
      unwrap(api.POST("/api/v1/auth/verify/resend/", { body: { email: me.email } })),
  });
  const verify = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/verify/", { body: { email: me.email, code } })),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["me"] });
      await client.invalidateQueries({ queryKey: ["csrf"] });
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    verify.mutate();
  }

  return (
    <section
      aria-labelledby="verify-title"
      className="flex flex-col gap-4 rounded-[var(--radius-card)] border border-halfday/40 bg-halfday-soft p-5"
    >
      <div>
        <h2 id="verify-title" className="font-display text-lg font-semibold text-ink">
          {t("verify.title")}
        </h2>
        <p className="text-sm text-muted">
          {t("verify.lead")}{" "}
          <strong className="text-ink" dir="ltr">
            {me.email}
          </strong>
        </p>
      </div>
      {send.isSuccess ? (
        <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-3">
          <CodeInput value={code} onChange={setCode} />
          <Button type="submit" disabled={verify.isPending || code.length !== 6}>
            {t("auth.verify")}
          </Button>
        </form>
      ) : (
        <div>
          <Button onClick={() => send.mutate()} disabled={send.isPending}>
            {t("auth.sendCode")}
          </Button>
        </div>
      )}
      <ErrorText error={verify.error ?? send.error} />
    </section>
  );
}
