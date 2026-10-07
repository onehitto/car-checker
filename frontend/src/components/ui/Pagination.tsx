import { useTranslation } from "react-i18next";

import { Button } from "./Button";

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, totalPages, total, onPageChange }: PaginationProps) {
  const { t } = useTranslation();
  if (totalPages <= 1) return null;
  return (
    <nav className="mt-4 flex items-center justify-between gap-3 text-sm text-steel">
      <span>
        {t("common.pageOf", { page, total: totalPages })}, {t("common.results", { count: total })}
      </span>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          {t("common.previous")}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          {t("common.next")}
        </Button>
      </div>
    </nav>
  );
}
