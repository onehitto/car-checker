import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { ApiError } from "@/api/errors";
import { Field, FormDialog, Input } from "@/components/ui";
import { renderWithProviders } from "@/test/render";

import { useFormSubmit, useZodForm } from "./forms";
import { field } from "./validation";

const schema = z.object({ mileage: field.int(0, 2_000_000), notes: field.optionalText(100) });

function MileageForm({ save }: { save: (values: z.output<typeof schema>) => Promise<unknown> }) {
  const form = useZodForm(schema, { mileage: "", notes: "" });
  const { onSubmit, formError, pending } = useFormSubmit(form, save, {
    successMessage: "Mileage updated",
  });
  return (
    <FormDialog
      title="Update the mileage"
      submitLabel="Save"
      onSubmit={onSubmit}
      onClose={() => {}}
      error={formError}
      pending={pending}
    >
      <Field label="Mileage" error={form.formState.errors.mileage?.message}>
        {(props) => <Input {...props} {...form.register("mileage")} />}
      </Field>
    </FormDialog>
  );
}

describe("useFormSubmit", () => {
  it("submits parsed values and confirms with a toast", async () => {
    const save = vi.fn().mockResolvedValue({});
    renderWithProviders(<MileageForm save={save} />);
    await userEvent.type(screen.getByLabelText("Mileage"), "98400");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(save).toHaveBeenCalledWith({ mileage: 98400, notes: null }, expect.anything());
    expect(await screen.findByText("Mileage updated")).toBeInTheDocument();
  });

  it("validates before sending", async () => {
    const save = vi.fn();
    renderWithProviders(<MileageForm save={save} />);
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Required")).toBeInTheDocument();
    expect(save).not.toHaveBeenCalled();
  });

  it("puts API field errors next to their input and other errors above the form", async () => {
    const save = vi
      .fn()
      .mockRejectedValueOnce(
        new ApiError(422, {
          code: "VALIDATION_ERROR",
          message: "Invalid",
          fields: { mileage: "Lower than a previous reading." },
        }),
      )
      .mockRejectedValueOnce(
        new ApiError(409, { code: "MILEAGE_DECREASE", message: "Mileage decreased" }),
      )
      .mockRejectedValueOnce(
        new ApiError(422, {
          code: "MILEAGE_DECREASE",
          message: "Mileage decreased",
          fields: { mileage: "Must be greater than or equal to 98910." },
        }),
      );
    renderWithProviders(<MileageForm save={save} />);
    await userEvent.type(screen.getByLabelText("Mileage"), "100");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Lower than a previous reading.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/lower than a previous one/);

    // Business rules attached to a field use the translated rule message.
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/lower than a previous one/)).toBeInTheDocument();
    expect(screen.queryByText(/greater than or equal/)).not.toBeInTheDocument();
  });
});
