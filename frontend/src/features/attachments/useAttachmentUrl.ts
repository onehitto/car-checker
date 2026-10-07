import { useQuery } from "@tanstack/react-query";

import { fetchBlob } from "@/api/files";

/** Object URL of a stored file (images are protected, so <img src> needs a blob URL). */
export function useAttachmentUrl(vehicleId: string, attachmentId: string | null | undefined) {
  return useQuery({
    queryKey: ["attachment-url", attachmentId],
    queryFn: async () =>
      URL.createObjectURL(
        await fetchBlob(`/api/v1/vehicles/${vehicleId}/attachments/${attachmentId}/download`),
      ),
    enabled: Boolean(attachmentId),
    staleTime: Infinity,
    meta: { objectUrl: true },
  });
}
