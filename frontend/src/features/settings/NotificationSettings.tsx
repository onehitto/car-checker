import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, unwrap } from "@/api/client";
import { ALERT_PRIORITIES } from "@/api/enums";
import type { NotificationPreference } from "@/api/types";
import {
  Button,
  Checkbox,
  errorMessage,
  ErrorState,
  LoadingState,
  Panel,
  Select,
  useToast,
} from "@/components/ui";

type Channel = "in_app" | "email";
type Priority = NotificationPreference["min_priority"];
type Rules = Record<Channel, { enabled: boolean; min_priority: Priority }>;

/** Channels that can deliver today (push and SMS have no provider yet). */
const CHANNELS: Channel[] = ["in_app", "email"];

export function NotificationSettings() {
  const preferences = useQuery({
    queryKey: ["me", "notification-preferences"],
    queryFn: () => unwrap(api.GET("/api/v1/users/me/notification-preferences")),
  });
  if (preferences.isPending) return <LoadingState />;
  if (preferences.isError)
    return <ErrorState error={preferences.error} onRetry={() => void preferences.refetch()} />;
  return <NotificationForm preferences={preferences.data} />;
}

function NotificationForm({ preferences }: { preferences: NotificationPreference[] }) {
  const { t } = useTranslation();
  const toast = useToast();
  const [rules, setRules] = useState<Rules>(() => {
    const rule = (channel: Channel) => {
      const found = preferences.find(
        (item) => item.channel === channel && item.alert_type === "all",
      );
      return { enabled: found?.enabled ?? true, min_priority: found?.min_priority ?? "low" };
    };
    return { in_app: rule("in_app"), email: rule("email") };
  });
  const save = useMutation({
    mutationFn: () =>
      unwrap(
        api.PUT("/api/v1/users/me/notification-preferences", {
          body: {
            preferences: CHANNELS.map((channel) => ({
              channel,
              alert_type: "all",
              ...rules[channel],
            })),
          },
        }),
      ),
    onSuccess: () => toast.success(t("settings.notifications.saved")),
    onError: (error) => toast.error(errorMessage(error, t)),
  });

  return (
    <Panel title={t("settings.notifications.title")} className="max-w-3xl">
      <p className="mb-4 text-sm text-steel">{t("settings.notifications.body")}</p>
      <ul className="divide-y divide-rule">
        {CHANNELS.map((channel) => (
          <li key={channel} className="flex flex-wrap items-center gap-x-6 gap-y-2 py-3">
            <div className="min-w-0 flex-1 basis-56">
              <Checkbox
                label={
                  <span className="text-[15px] font-medium">
                    {t(`settings.notifications.channels.${channel}`)}
                  </span>
                }
                checked={rules[channel].enabled}
                onChange={(event) =>
                  setRules((current) => ({
                    ...current,
                    [channel]: { ...current[channel], enabled: event.target.checked },
                  }))
                }
              />
              <p className="ms-6 text-sm text-steel">
                {t(`settings.notifications.channelHints.${channel}`)}
              </p>
            </div>
            <label className="flex items-center gap-2 text-sm">
              {t("settings.notifications.from")}
              <Select
                className="w-auto"
                value={rules[channel].min_priority}
                disabled={!rules[channel].enabled}
                onChange={(event) =>
                  setRules((current) => ({
                    ...current,
                    [channel]: {
                      ...current[channel],
                      min_priority: event.target.value as Priority,
                    },
                  }))
                }
              >
                {[...ALERT_PRIORITIES].reverse().map((priority) => (
                  <option key={priority} value={priority}>
                    {t(`status.${priority}`)}
                  </option>
                ))}
              </Select>
            </label>
          </li>
        ))}
      </ul>
      <div className="mt-4">
        <Button loading={save.isPending} onClick={() => save.mutate()}>
          {t("common.saveChanges")}
        </Button>
      </div>
    </Panel>
  );
}
